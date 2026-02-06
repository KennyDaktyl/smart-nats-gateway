import json
from app.core.logging import logger

from app.ws.subscriptions import (
    add_subscription,
    remove_subscription,
    subscribers,
    get_subscribers_for_ws,
    get_cached_subcribers_set,
    cache_subcribers_set,
    remove_ws,
    clients,
    ws_label,
)
from app.nats.publisher import publish_event


async def websocket_handler(ws):
    clients.add(ws)
    logger.info(f"Client connected {ws_label(ws)} ({len(clients)} total)")

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
                action = data.get("action")

                # -------------------------------------------------------
                # Event subscriptions
                # -------------------------------------------------------
                if action == "subscribe":
                    subject = data["subject"]
                    is_first = add_subscription(subject, ws)
                    if is_first:
                        await publish_event(subject, "start")
                    logger.info(f"WS subscribed to Subject {subject}")

                elif action == "subscribe_many":
                    subjects = set(data["subjects"])

                    cached = get_cached_subcribers_set(ws)
                    current = get_subscribers_for_ws(ws)
                    if cached == subjects and current == subjects:
                        logger.info(
                            f"WS subscribe_many received identical set, skipping update: {list(subjects)}"
                        )
                        continue

                    for subject in current - subjects:
                        emptied = remove_subscription(subject, ws)
                        if emptied:
                            await publish_event(subject, "stop")

                    cache_subcribers_set(ws, subjects)
                    logger.info(f"WS subscribed to MANY: {list(subjects)}")

                elif action == "unsubscribe_many":
                    subjects = set(data.get("subjects", []))
                    removed_any = False
                    for subject in subjects:
                        before = len(subscribers.get(subject, ()))
                        emptied = remove_subscription(subject, ws)
                        after = len(subscribers.get(subject, ()))
                        if before != after:
                            removed_any = True
                        if emptied:
                            await publish_event(subject, "stop")
                    cache_subcribers_set(ws, get_subscribers_for_ws(ws))
                    if removed_any:
                        logger.info(f"WS unsubscribed from MANY: {list(subjects)}")

            except Exception as e:
                logger.warning(f"Bad WS message: {e}")

    finally:
        removed_subscriber, emptied_subscriber = remove_ws(ws)
        for subject in emptied_subscriber:
            await publish_event(subject, "stop")
        logger.info(
            f"Client disconnected {ws_label(ws)} ({len(clients)} total), "
            f"removed from {removed_subscriber} subscribers"
        )
