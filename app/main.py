import asyncio
import base64
import json
import signal

import nats
import websockets

from app.core.config import settings
from app.core.logging import logger
from app.nats.publisher import set_nats_client
from app.nats.subscription_manager import NatsSubscriptionManager
from app.ws.send import send_to_subscribers
from app.ws.websocket_handler import websocket_handler


def _decode_nats_payload(raw_data: bytes) -> tuple[object, str]:
    try:
        text = raw_data.decode("utf-8")
    except UnicodeDecodeError:
        return (
            {
                "encoding": "base64",
                "value": base64.b64encode(raw_data).decode("ascii"),
            },
            "binary",
        )

    try:
        return json.loads(text), "json"
    except json.JSONDecodeError:
        return text, "text"


async def start_gateway():
    logger.info("Starting NATS -> WebSocket gateway")

    nc = await nats.connect(
        settings.NATS_URL,
        name=settings.NATS_CLIENT_NAME,
    )
    logger.info("Connected to NATS Core: %s", settings.NATS_URL)
    set_nats_client(nc)

    async def on_nats_msg(msg):
        subject = msg.subject
        try:
            payload, payload_format = _decode_nats_payload(msg.data)
            if payload_format != "json":
                logger.debug(
                    "Forwarding non-JSON NATS payload subject=%s payload_format=%s",
                    subject,
                    payload_format,
                )
            await send_to_subscribers(
                subject,
                {
                    "subject": subject,
                    "data": payload,
                    "payload_format": payload_format,
                },
            )
        except Exception:
            logger.exception("NATS message handling failed for subject=%s", subject)

    nats_manager = NatsSubscriptionManager(nc, on_nats_msg)

    ws_server = await websockets.serve(
        lambda ws: websocket_handler(ws, nats_manager),
        host=settings.WS_HOST,
        port=settings.WS_PORT,
        ping_interval=30,
        ping_timeout=10,
        max_queue=32,
    )

    logger.info("WebSocket ready at ws://%s:%s", settings.WS_HOST, settings.WS_PORT)

    stop_event = asyncio.Event()

    def _shutdown():
        logger.warning("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            logger.warning("Signal handlers are not supported in this runtime")
            break

    await stop_event.wait()

    logger.info("Shutting down gateway")
    ws_server.close()
    await ws_server.wait_closed()

    try:
        await nats_manager.stop_all()
    except Exception:
        logger.exception("Failed to stop NATS subscriptions during shutdown")

    try:
        await nc.drain()
    except Exception:
        logger.exception("Failed to drain NATS connection before close")
    finally:
        await nc.close()

    logger.info("Gateway stopped")


if __name__ == "__main__":
    asyncio.run(start_gateway())
