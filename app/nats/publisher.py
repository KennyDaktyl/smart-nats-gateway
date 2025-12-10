# app/nats/publisher.py
import json
from typing import Optional

from app.core.config import settings
from app.core.logging import logger
from app.nats.subjects import RASPBERRY_EVENTS

jetstream_client = None


def set_jetstream_client(js):
    """
    Store the JetStream client so that WS handlers can publish control events.
    """
    global jetstream_client
    jetstream_client = js
    logger.info("JetStream client attached to publisher")


def heartbeat_control_subject(uuid: str) -> str:
    template = settings.RASPBERRY_EVENTS_SUBJECT_TEMPLATE or RASPBERRY_EVENTS
    return template.format(uuid=uuid)


async def publish_heartbeat_control(uuid: str, action: str):
    """
    Publish start/stop heartbeat commands for a given Raspberry UUID.
    """
    if not jetstream_client:
        logger.error(
            f"Cannot publish heartbeat control '{action}' for {uuid}: "
            f"JetStream client is not set"
        )
        return

    subject = heartbeat_control_subject(uuid)
    payload = json.dumps({
        "event_type": "HEARTBEAT",
        "payload": {
            "uuid": uuid,
            "action": action,
        },
    }).encode()

    logger.info(
        f"Publishing heartbeat control '{action}' for Raspberry {uuid} "
        f"on subject {subject}"
    )
    await jetstream_client.publish(subject, payload)
