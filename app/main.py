# app/main.py
import asyncio
import websockets
import nats

from app.core.config import settings
from app.core.logging import logger

from app.nats.subjects import INVERTER_UPDATE, RASPBERRY_HEARTBEAT
from app.nats.consumer_inverter import inverter_consumer
from app.nats.consumer_heartbeat import heartbeat_consumer, last_seen, raspberry_status
from app.watchdog.offline_checker import watchdog
from app.nats.publisher import set_jetstream_client
from app.ws.websocket_handler import websocket_handler


async def start_gateway():
    logger.info("Starting NATS JetStream Gateway...")

    nc = await nats.connect(settings.NATS_URL)
    js = nc.jetstream()
    set_jetstream_client(js)

    logger.info("Connected to NATS JetStream")

    sub_inverter = await js.pull_subscribe(
        INVERTER_UPDATE, durable="inverter_gateway"
    )

    sub_heartbeat = await js.pull_subscribe(
        RASPBERRY_HEARTBEAT, durable="heartbeat_gateway"
    )

    tasks = [
        asyncio.create_task(inverter_consumer(sub_inverter)),
        asyncio.create_task(heartbeat_consumer(sub_heartbeat)),
        asyncio.create_task(watchdog(last_seen, raspberry_status)),
    ]

    server = await websockets.serve(websocket_handler, "0.0.0.0", 8765)
    logger.info("🌐 WebSocket ready at ws://0.0.0.0:8765")

    try:
        await asyncio.Event().wait()
    finally:
        for t in tasks:
            t.cancel()
            logger.warning("Task cancelled:", t)



if __name__ == "__main__":
    asyncio.run(start_gateway())
