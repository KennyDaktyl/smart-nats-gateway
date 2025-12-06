import json
from app.ws.send import send_to_inverter_subscribers
from app.core.logging import logger


async def inverter_consumer(sub):
    while True:
        try:
            msgs = await sub.fetch(10, timeout=1)
        except:
            continue

        for msg in msgs:
            try:
                data = json.loads(msg.data.decode())
                payload = data.get("payload", {}) if isinstance(data, dict) else {}

                serial = payload.get("serial_number") or payload.get("serial")

                if not serial:
                    logger.error(
                        f"Inverter consumer error: missing serial_number "
                        f"(subject={msg.subject}, payload={data})"
                    )
                    await msg.ack()
                    continue

                logger.info(f"[Inverter] Event: {data}")

                await send_to_inverter_subscribers(serial, payload)

                await msg.ack()
            except Exception as e:
                logger.error(f"Inverter consumer error: {e}")
