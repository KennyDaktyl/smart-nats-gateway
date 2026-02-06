# app/main.py
import asyncio
import websockets
import nats

from app.core.config import settings
from app.core.logging import logger

from app.nats.consumer import consumer
from app.nats.publisher import set_jetstream_client
from app.ws.websocket_handler import websocket_handler


async def start_gateway():
    logger.info("Starting NATS JetStream Gateway...")

    nc = await nats.connect(settings.NATS_URL)
    subject = settings.SUBJECT
    js = nc.jetstream()
    set_jetstream_client(js)

    logger.info("Connected to NATS JetStream")

    nats_subscription = await js.pull_subscribe(subject, durable="nats_gateway")

    tasks = [
        asyncio.create_task(consumer(nats_subscription)),
    ]

    await websockets.serve(websocket_handler, "0.0.0.0", 8765)
    logger.info("🌐 WebSocket ready at ws://0.0.0.0:8765")

    try:
        await asyncio.Event().wait()
    finally:
        for t in tasks:
            t.cancel()
            logger.warning("Task cancelled:", t)


if __name__ == "__main__":
    asyncio.run(start_gateway())
