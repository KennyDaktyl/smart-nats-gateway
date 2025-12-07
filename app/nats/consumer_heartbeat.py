# app/nats/consumer_heartbeat.py
import json
import time
from app.core.logging import logger
from app.ws.send import send_to_subscribers

last_seen = {}
raspberry_status = {}

async def heartbeat_consumer(sub):
    while True:
        try:
            msgs = await sub.fetch(10, timeout=1)
        except:
            continue

        for msg in msgs:
            try:
                data = json.loads(msg.data.decode())
                logger.info(f"Heartbeat message data: {data}")

                if not isinstance(data, dict):
                    logger.error(
                        f"Heartbeat consumer error: unexpected payload type "
                        f"(subject={msg.subject}, payload={data})"
                    )
                    await msg.ack()
                    continue

                payload = data.get("payload", {})
                if not isinstance(payload, dict):
                    logger.error(
                        f"Heartbeat consumer error: payload is not a dict "
                        f"(subject={msg.subject}, payload={data})"
                    )
                    await msg.ack()
                    continue

                uuid = payload.get("uuid")
                status = payload.get("status", "online")

                if not uuid:
                    logger.error(
                        f"Heartbeat consumer error: missing uuid "
                        f"(subject={msg.subject}, payload={data})"
                    )
                    await msg.ack()
                    continue

                logger.info(f"Received heartbeat message: {data}")

                last_seen[uuid] = time.time()
                raspberry_status[uuid] = status

                logger.info(f"Heartbeat {uuid}, payload: {data}")

                await send_to_subscribers(uuid, {
                    "type": "raspberry_heartbeat",
                    "data": {**payload, "status": status}
                })

                await msg.ack()
            except Exception as e:
                logger.error(f"Heartbeat consumer error: {e} (subject={msg.subject})")
                await msg.ack()
