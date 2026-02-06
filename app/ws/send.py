# app/ws/send.py
import json
from app.ws.subscriptions import (
    get_subscribers,
    ws_label,
)
from app.core.logging import logger


async def send_to_subscribers(subject: str, data: dict):
    subs = get_subscribers(subject)
    if not subs:
        logger.info(f"No WS subscribers for Subject {subject}, skipping send")
        return

    msg = json.dumps(data)
    dead = []

    subscribers_labels = [ws_label(ws) for ws in subs]
    logger.info(
        f"Sending event for subject {subject} to {len(subs)} WS client(s): "
        f"{subscribers_labels}"
    )

    for ws in list(subs):
        try:
            await ws.send(msg)
        except Exception as e:
            dead.append(ws)
            logger.warning(f"Send failed to {ws_label(ws)} for Subject {subject}: {e}")

    if dead:
        logger.info(f"Pruned {len(dead)} dead WS connections for Subject {subject}")

    delivered = len(subs) - len(dead)
    logger.info(f"Sent event to {delivered} WS subscriber(s) for Subject {subject}")

    for ws in dead:
        subs.discard(ws)
