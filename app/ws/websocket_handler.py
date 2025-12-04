import json
from app.core.logging import logger

from app.ws.subscriptions import (
    add_raspberry_subscription,
    add_inverter_subscription,
    remove_inverter_subscription,
    remove_ws,
    clients,
)


async def websocket_handler(ws):
    clients.add(ws)
    logger.info(f"Client connected ({len(clients)} total)")

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
                action = data.get("action")

                # -------------------------------------------------------
                # Raspberry subscriptions
                # -------------------------------------------------------
                if action == "subscribe":
                    uuid = data["uuid"]
                    add_raspberry_subscription(uuid, ws)
                    logger.info(f"WS subscribed to Raspberry {uuid}")

                elif action == "subscribe_many":
                    uuids = data["uuids"]
                    for uuid in uuids:
                        add_raspberry_subscription(uuid, ws)
                    logger.info(f"WS subscribed to MANY: {uuids}")

                # -------------------------------------------------------
                # Inverter subscriptions
                # -------------------------------------------------------
                elif action == "subscribe_inverter":
                    serial = data["serial"]
                    add_inverter_subscription(serial, ws)
                    logger.info(f"WS subscribed to Inverter {serial}")

                elif action == "unsubscribe_inverter":
                    serial = data["serial"]
                    remove_inverter_subscription(serial, ws)
                    logger.info(f"WS unsubscribed from Inverter {serial}")

                else:
                    logger.warning(f"Unknown WS action: {action}")

            except Exception as e:
                logger.warning(f"Bad WS message: {e}")

    finally:
        remove_ws(ws)
        logger.info(f"Client disconnected ({len(clients)} total))")
