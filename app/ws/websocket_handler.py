import json
from app.core.logging import logger

from app.ws.subscriptions import (
    add_subscription,
    remove_subscription,
    remove_ws,
    register_client,
    ws_label,
)

from app.nats.publisher import publish_agent_control


async def websocket_handler(ws, nats_manager):

    await register_client(ws)
    logger.info(f"Client connected {ws_label(ws)}")

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
                logger.info(f"Data event: {data}")
                action = data.get("action")

                # =================================================
                # SUBSCRIBE
                # =================================================
                if action == "subscribe":

                    subject = data.get("subject")
                    micro_uuid = data.get("uuid")
                    event_name = data.get("event")

                    if not subject or not micro_uuid or not event_name:
                        logger.warning(
                            f"{ws_label(ws)} subscribe missing subject/uuid/event"
                        )
                        continue

                    is_first = await add_subscription(subject, ws)

                    if is_first:
                        await nats_manager.start(subject)

                    # 🔥 TYLKO heartbeat steruje agentem
                    if event_name == "microcontroller_heartbeat":
                        await publish_agent_control(
                            micro_uuid,
                            action="START_HEARTBEAT",
                        )

                    logger.info(f"{ws_label(ws)} subscribed to {subject}")

                # =================================================
                # UNSUBSCRIBE MANY
                # =================================================
                elif action == "unsubscribe_many":

                    subjects = set(data.get("subjects", []))

                    for subject in subjects:

                        parts = subject.split(".")
                        if len(parts) >= 4:
                            micro_uuid = parts[1]
                            event_name = parts[3]

                            if event_name == "microcontroller_heartbeat":
                                await publish_agent_control(
                                    micro_uuid,
                                    action="STOP_HEARTBEAT",
                                )

                    logger.info(f"{ws_label(ws)} unsubscribe_many -> {list(subjects)}")

                else:
                    logger.warning(f"{ws_label(ws)} unknown action: {action}")

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from {ws_label(ws)}: {raw}")
            except Exception:
                logger.exception(f"Bad WS message from {ws_label(ws)}")

    finally:
        removed_count, emptied_subjects = await remove_ws(ws)

        for subject in emptied_subjects:
            await nats_manager.stop(subject)

            parts = subject.split(".")
            if len(parts) >= 4:
                micro_uuid = parts[1]
                event_name = parts[3]

                if event_name == "microcontroller_heartbeat":
                    await publish_agent_control(
                        micro_uuid,
                        action="STOP_HEARTBEAT",
                    )

        logger.info(
            f"Client disconnected {ws_label(ws)}, "
            f"removed from {removed_count} subjects"
        )
