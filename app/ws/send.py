import json
import asyncio

from app.ws.subscriptions import (
    get_subscribers,
    ws_label,
)
from app.core.logging import logger


SEND_TIMEOUT = 1.0  # seconds


async def _send_one(ws, msg: str, subject: str) -> bool:
    """
    Send message to single WS client.

    Returns:
        True  -> delivered
        False -> failed / timeout
    """
    try:
        await asyncio.wait_for(ws.send(msg), timeout=SEND_TIMEOUT)
        return True
    except asyncio.TimeoutError:
        logger.warning(
            f"WS send timeout to {ws_label(ws)} for subject {subject}"
        )
    except Exception as e:
        logger.warning(
            f"WS send failed to {ws_label(ws)} "
            f"for subject {subject}: {e}"
        )
    return False


async def send_to_subscribers(subject: str, data: dict):
    # ---------------------------------------------------------
    # Snapshot subscribers (SAFE)
    # ---------------------------------------------------------
    subs = await get_subscribers(subject)
    if not subs:
        logger.debug("No WS subscribers for subject %s", subject)
        return

    try:
        msg = json.dumps(data)
    except (TypeError, ValueError):
        logger.exception("Failed to serialize outbound WS payload for subject %s", subject)
        return

    logger.info(
        "Sending event for subject %s to %s WS client(s): %s",
        subject,
        len(subs),
        [ws_label(ws) for ws in subs],
    )

    # ---------------------------------------------------------
    # Fan-out PARALLEL (isolated clients)
    # ---------------------------------------------------------
    tasks = [
        _send_one(ws, msg, subject)
        for ws in subs
    ]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=False,
    )

    delivered = sum(1 for r in results if r)

    if delivered != len(subs):
        logger.warning(
            "Sent event for subject %s to %s/%s WS subscriber(s)",
            subject,
            delivered,
            len(subs),
        )
        return

    logger.info(
        "Sent event for subject %s to %s/%s WS subscriber(s)",
        subject,
        delivered,
        len(subs),
    )
