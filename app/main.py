import asyncio
import json
import signal
import websockets
import nats

from app.core.config import settings
from app.core.logging import logger

from app.nats.publisher import set_nats_client
from app.ws.websocket_handler import websocket_handler
from app.ws.send import send_to_subscribers
from app.nats.subscription_manager import NatsSubscriptionManager


async def start_gateway():
    logger.info("🚀 Starting NATS → WebSocket Gateway")

    # -------------------------------------------------
    # NATS connection
    # -------------------------------------------------
    nc = await nats.connect(
        settings.NATS_URL,
        name="smart-gateway",
    )
    logger.info("✅ Connected to NATS Core")
    set_nats_client(nc)

    # -------------------------------------------------
    # NATS message handler (fan-out only)
    # -------------------------------------------------
    async def on_nats_msg(msg):
        try:
            subject = msg.subject
            data = json.loads(msg.data.decode())
            await send_to_subscribers(
                subject,
                {"subject": subject, "data": data},
            )
        except Exception as e:
            logger.exception(f"NATS message handling failed: {e}")

    # -------------------------------------------------
    # Subscription manager (CONTROL PLANE)
    # -------------------------------------------------
    nats_manager = NatsSubscriptionManager(nc, on_nats_msg)

    # -------------------------------------------------
    # WebSocket server
    # -------------------------------------------------
    ws_server = await websockets.serve(
        lambda ws: websocket_handler(ws, nats_manager),
        host="0.0.0.0",
        port=8765,
        ping_interval=30,
        ping_timeout=10,
        max_queue=32,
    )

    logger.info("🌐 WebSocket ready at ws://0.0.0.0:8765")

    # -------------------------------------------------
    # Graceful shutdown
    # -------------------------------------------------
    stop_event = asyncio.Event()

    def _shutdown():
        logger.warning("🛑 Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _shutdown)

    await stop_event.wait()

    # -------------------------------------------------
    # Cleanup
    # -------------------------------------------------
    logger.info("🔻 Shutting down gateway...")
    ws_server.close()
    await ws_server.wait_closed()
    await nc.close()
    logger.info("👋 Gateway stopped")


if __name__ == "__main__":
    asyncio.run(start_gateway())
