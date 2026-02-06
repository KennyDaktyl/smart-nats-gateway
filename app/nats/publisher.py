# app/nats/publisher.py
import json

from app.core.logging import logger

jetstream_client = None


def set_jetstream_client(js):
    """
    Store the JetStream client so that WS handlers can publish control events.
    """
    global jetstream_client
    jetstream_client = js
    logger.info("JetStream client attached to publisher")


async def publish_event(subject: str, action: str, data: dict = {}):
    if not jetstream_client:
        logger.error(
            f"Cannot publish event '{action}' for {subject}: "
            f"JetStream client is not set"
        )
        return

    payload = json.dumps(data).encode()

    logger.info(f"Publishing event '{action}' for Subject {subject} ")
    await jetstream_client.publish(subject, payload)
