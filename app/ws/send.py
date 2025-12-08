#app/ws/send.py
import json
from app.ws.subscriptions import (
    get_raspberry_subscribers,
    get_inverter_subscribers,
    ws_label,
)
from app.core.logging import logger


async def send_to_subscribers(uuid: str, payload: dict):
    subs = get_raspberry_subscribers(uuid)
    if not subs:
        logger.info(f"No WS subscribers for Raspberry {uuid}, skipping send")
        return

    msg = json.dumps(payload)
    dead = []

    subscribers_labels = [ws_label(ws) for ws in subs]
    logger.info(
        f"Sending heartbeat for Raspberry {uuid} to {len(subs)} WS client(s): "
        f"{subscribers_labels}"
    )

    for ws in list(subs):
        try:
            await ws.send(msg)
        except Exception as e:
            dead.append(ws)
            logger.warning(f"Send failed to {ws_label(ws)} for Raspberry {uuid}: {e}")

    if dead:
        logger.info(
            f"Pruned {len(dead)} dead WS connections for Raspberry {uuid}"
        )

    delivered = len(subs) - len(dead)
    logger.info(f"Sent heartbeat to {delivered} WS subscriber(s) for Raspberry {uuid}")

    for ws in dead:
        subs.discard(ws)


async def send_to_inverter_subscribers(serial: str, payload: dict):
    subs = get_inverter_subscribers(serial)
    if not subs:
        logger.info(f"No WS subscribers for Inverter {serial}, skipping send")
        return

    msg = json.dumps(payload)
    dead = []

    subscribers_labels = [ws_label(ws) for ws in subs]
    logger.info(
        f"Sending inverter update for {serial} to {len(subs)} WS client(s): "
        f"{subscribers_labels}"
    )

    for ws in list(subs):
        try:
            await ws.send(msg)
        except Exception as e:
            dead.append(ws)
            logger.warning(f"Send failed to {ws_label(ws)} for Inverter {serial}: {e}")

    if dead:
        logger.info(
            f"Pruned {len(dead)} dead WS connections for Inverter {serial}"
        )

    delivered = len(subs) - len(dead)
    logger.info(f"Sent inverter update to {delivered} WS subscriber(s) for Inverter {serial}")

    for ws in dead:
        subs.discard(ws)
