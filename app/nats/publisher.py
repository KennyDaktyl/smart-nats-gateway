# app/nats/publisher.py
import json
from app.core.logging import logger

_nats_client = None


def set_nats_client(nc):
    """
    Attach NATS Core client for publishing control events.
    """
    global _nats_client
    _nats_client = nc
    logger.info("NATS client attached to publisher")


async def publish_agent_control(
    micro_uuid: str,
    action: str,
    data: dict | None = None,
):
    if not micro_uuid or not action:
        logger.warning(
            "[NATS -> AGENT] skipped publish, missing micro_uuid/action: uuid=%s action=%s",
            micro_uuid,
            action,
        )
        return

    if not _nats_client:
        logger.error("[NATS -> AGENT] skipped publish, NATS client not set")
        return

    subject = f"device_communication.{micro_uuid}.command.heartbeat"

    payload = {
        "event_type": "HEARTBEAT_CONTROL",
        "action": action,
        "data": data or {},
    }

    logger.info(
        "[NATS -> AGENT] subject=%s payload=%s",
        subject,
        payload,
    )

    await _nats_client.publish(
        subject,
        json.dumps(payload).encode(),
    )
