import json
from app.core.logging import logger

from app.ws.subscriptions import (
    add_raspberry_subscription,
    remove_raspberry_subscription,
    raspberry_subs,
    get_raspberry_subscriptions_for_ws,
    get_cached_raspberry_set,
    cache_raspberry_set,
    add_inverter_subscription,
    remove_inverter_subscription,
    remove_ws,
    clients,
    ws_label,
)


async def websocket_handler(ws):
    clients.add(ws)
    logger.info(f"Client connected {ws_label(ws)} ({len(clients)} total)")

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
                    uuids = set(data["uuids"])

                    cached = get_cached_raspberry_set(ws)
                    current = get_raspberry_subscriptions_for_ws(ws)
                    if cached == uuids and current == uuids:
                        logger.info(
                            f"WS subscribe_many received identical set, skipping update: {list(uuids)}"
                        )
                        continue

                    # Align server state with the provided list to avoid stale subs
                    for uuid in current - uuids:
                        remove_raspberry_subscription(uuid, ws)

                    for uuid in uuids - current:
                        add_raspberry_subscription(uuid, ws)
                    cache_raspberry_set(ws, uuids)
                    logger.info(f"WS subscribed to MANY: {list(uuids)}")

                elif action == "unsubscribe_many":
                    uuids = set(data.get("uuids", []))
                    removed_any = False
                    for uuid in uuids:
                        before = len(raspberry_subs.get(uuid, ()))
                        remove_raspberry_subscription(uuid, ws)
                        after = len(raspberry_subs.get(uuid, ()))
                        if before != after:
                            removed_any = True
                    cache_raspberry_set(ws, get_raspberry_subscriptions_for_ws(ws))
                    if removed_any:
                        logger.info(f"WS unsubscribed from MANY: {list(uuids)}")

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
        r_removed, i_removed = remove_ws(ws)
        logger.info(
            f"Client disconnected {ws_label(ws)} ({len(clients)} total), "
            f"removed from {r_removed} raspberry and {i_removed} inverter subscriptions"
        )
