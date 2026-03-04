"""
WebSocket control-plane contract:
- subscribe: {"action":"subscribe","subject":"...","event":"microcontroller_heartbeat","uuid":"..."}
- unsubscribe: {"action":"unsubscribe","subject":"..."}
- unsubscribe_many: {"action":"unsubscribe_many","subjects":["...", "..."]}

Gateway validates only shape (required fields) and never enforces any subject schema.
Heartbeat control is optional and activated only when subscribe payload explicitly carries
event == HEARTBEAT_EVENT_NAME and a valid uuid.
"""

import asyncio
import json
from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.nats.publisher import publish_agent_control
from app.ws.subscriptions import (
    add_subscription,
    register_client,
    remove_subscription,
    remove_ws,
    ws_label,
)


_heartbeat_subjects: dict[str, str] = {}
_heartbeat_lock = asyncio.Lock()


def _normalize_subject(subject: Any) -> str | None:
    if not isinstance(subject, str):
        return None

    normalized = subject.strip()
    return normalized or None


def _extract_heartbeat_uuid(data: dict[str, Any]) -> str | None:
    event_name = data.get("event")
    if event_name != settings.HEARTBEAT_EVENT_NAME:
        return None

    micro_uuid = data.get("uuid")
    if not isinstance(micro_uuid, str) or not micro_uuid.strip():
        logger.warning(
            "Heartbeat control skipped, invalid uuid in subscribe payload: %s",
            data,
        )
        return None

    return micro_uuid.strip()


async def _register_heartbeat_subject(subject: str, micro_uuid: str) -> bool:
    async with _heartbeat_lock:
        existing_uuid = _heartbeat_subjects.get(subject)
        if existing_uuid == micro_uuid:
            return True

        if existing_uuid and existing_uuid != micro_uuid:
            logger.warning(
                "Heartbeat subject %s already linked to uuid=%s, got uuid=%s (overwriting)",
                subject,
                existing_uuid,
                micro_uuid,
            )

        _heartbeat_subjects[subject] = micro_uuid
        return False


async def _pop_heartbeat_subject(subject: str) -> str | None:
    async with _heartbeat_lock:
        return _heartbeat_subjects.pop(subject, None)


async def _send_start_heartbeat_if_needed(subject: str, micro_uuid: str):
    already_running = await _register_heartbeat_subject(subject, micro_uuid)
    action = "RELOAD_HEARTBEAT" if already_running else "START_HEARTBEAT"

    await publish_agent_control(
        micro_uuid,
        action=action,
    )
    logger.info("Heartbeat %s requested for subject=%s uuid=%s", action, subject, micro_uuid)


async def _send_stop_heartbeat_if_needed(subject: str):
    micro_uuid = await _pop_heartbeat_subject(subject)
    if not micro_uuid:
        return

    await publish_agent_control(
        micro_uuid,
        action="STOP_HEARTBEAT",
    )
    logger.info("Heartbeat STOP requested for subject=%s uuid=%s", subject, micro_uuid)


async def _send_ws_error(ws, code: str, message: str):
    payload = {"type": "error", "code": code, "message": message}
    try:
        await ws.send(json.dumps(payload))
    except Exception:
        logger.exception("Failed to send ws error payload to %s", ws_label(ws))


async def _handle_subscribe(ws, data: dict[str, Any], nats_manager):
    subject = _normalize_subject(data.get("subject"))
    if not subject:
        logger.warning("%s subscribe ignored, invalid subject", ws_label(ws))
        await _send_ws_error(ws, "INVALID_SUBJECT", "subscribe requires non-empty subject")
        return

    added = await add_subscription(subject, ws)

    if added:
        try:
            await nats_manager.start(subject)
        except Exception:
            logger.exception("Failed to activate NATS subject=%s", subject)
            await remove_subscription(subject, ws)
            await _send_ws_error(
                ws,
                "NATS_SUBSCRIBE_FAILED",
                f"cannot subscribe NATS subject={subject}",
            )
            return

    heartbeat_uuid = _extract_heartbeat_uuid(data)
    if heartbeat_uuid and added:
        try:
            await _send_start_heartbeat_if_needed(subject, heartbeat_uuid)
        except Exception:
            logger.exception("Failed to publish heartbeat START for subject=%s", subject)

    if not added:
        logger.info("%s subscribe ignored, already subscribed to %s", ws_label(ws), subject)
    else:
        logger.info("%s subscribed to %s", ws_label(ws), subject)


async def _handle_unsubscribe(ws, data: dict[str, Any], nats_manager):
    subject = _normalize_subject(data.get("subject"))
    if not subject:
        logger.warning("%s unsubscribe ignored, invalid subject", ws_label(ws))
        await _send_ws_error(ws, "INVALID_SUBJECT", "unsubscribe requires non-empty subject")
        return

    removed, emptied = await remove_subscription(subject, ws)
    if not removed:
        logger.info("%s unsubscribe ignored, no active subscription for %s", ws_label(ws), subject)
        return

    try:
        await nats_manager.stop(subject)
    except Exception:
        logger.exception("Failed to stop NATS subject=%s", subject)

    if emptied:
        try:
            await _send_stop_heartbeat_if_needed(subject)
        except Exception:
            logger.exception("Failed to publish heartbeat STOP for subject=%s", subject)

    logger.info("%s unsubscribed from %s", ws_label(ws), subject)


async def _handle_unsubscribe_many(ws, data: dict[str, Any], nats_manager):
    subjects_raw = data.get("subjects")
    if not isinstance(subjects_raw, list):
        logger.warning("%s unsubscribe_many ignored, subjects is not a list", ws_label(ws))
        await _send_ws_error(ws, "INVALID_SUBJECTS", "unsubscribe_many requires subjects list")
        return

    subjects = {
        normalized
        for normalized in (_normalize_subject(item) for item in subjects_raw)
        if normalized
    }

    if not subjects:
        logger.info("%s unsubscribe_many ignored, no valid subjects provided", ws_label(ws))
        return

    for subject in subjects:
        removed, emptied = await remove_subscription(subject, ws)
        if not removed:
            continue

        try:
            await nats_manager.stop(subject)
        except Exception:
            logger.exception("Failed to stop NATS subject=%s", subject)

        if emptied:
            try:
                await _send_stop_heartbeat_if_needed(subject)
            except Exception:
                logger.exception("Failed to publish heartbeat STOP for subject=%s", subject)

    logger.info("%s unsubscribe_many handled for %s", ws_label(ws), sorted(subjects))


async def websocket_handler(ws, nats_manager):
    await register_client(ws)
    logger.info("Client connected %s", ws_label(ws))

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from %s: %s", ws_label(ws), raw)
                await _send_ws_error(ws, "INVALID_JSON", "message must be valid JSON")
                continue

            if not isinstance(data, dict):
                logger.warning("Ignored non-object payload from %s: %s", ws_label(ws), data)
                await _send_ws_error(ws, "INVALID_PAYLOAD", "message must be a JSON object")
                continue

            action = data.get("action")
            logger.info("Action received from %s: %s", ws_label(ws), action)

            try:
                if action == "subscribe":
                    await _handle_subscribe(ws, data, nats_manager)
                elif action == "unsubscribe":
                    await _handle_unsubscribe(ws, data, nats_manager)
                elif action == "unsubscribe_many":
                    await _handle_unsubscribe_many(ws, data, nats_manager)
                else:
                    logger.warning("%s unknown action: %s", ws_label(ws), action)
                    await _send_ws_error(
                        ws,
                        "UNKNOWN_ACTION",
                        "supported actions: subscribe, unsubscribe, unsubscribe_many",
                    )
            except Exception:
                logger.exception("Failed to process action=%s from %s", action, ws_label(ws))

    finally:
        removed_subjects, emptied_subjects = await remove_ws(ws)

        for subject in removed_subjects:
            try:
                await nats_manager.stop(subject)
            except Exception:
                logger.exception("Failed to stop NATS subject=%s on disconnect", subject)

            if subject in emptied_subjects:
                try:
                    await _send_stop_heartbeat_if_needed(subject)
                except Exception:
                    logger.exception(
                        "Failed to publish heartbeat STOP for subject=%s on disconnect",
                        subject,
                    )

        logger.info(
            "Client disconnected %s, removed from %s subjects",
            ws_label(ws),
            len(removed_subjects),
        )
