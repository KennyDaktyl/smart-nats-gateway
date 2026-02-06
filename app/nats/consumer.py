# app/nats/consumer_inverter.py
import json
from app.ws.send import send_to_subscribers
from app.core.logging import logger


async def consumer(sub):
    while True:
        try:
            msgs = await sub.fetch(10, timeout=1)
        except:
            continue

        for msg in msgs:
            try:
                data = json.loads(msg.data.decode())
                subject = data.get("subject")
                logger.info(f"[Inverter] payload: {data}, subject: {subject}")

                await send_to_subscribers(subject, data)

                await msg.ack()
            except Exception as e:
                logger.error(f"Inverter consumer error: {e}")
