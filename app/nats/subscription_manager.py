import asyncio

from app.core.logging import logger


class NatsSubscriptionManager:
    def __init__(self, nc, on_message_cb):
        self._nc = nc
        self._on_message_cb = on_message_cb
        self._subs: dict[str, object] = {}
        self._ref_counts: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def start(self, subject: str):
        """
        Increment local interest for subject and ensure NATS subscription exists.
        """
        async with self._lock:
            current = self._ref_counts.get(subject, 0)
            next_count = current + 1
            self._ref_counts[subject] = next_count

            if current > 0:
                logger.debug(
                    "[nats] subscribe ref++ subject=%s refs=%s",
                    subject,
                    next_count,
                )
                return

            logger.info("[nats] subscribe %s", subject)
            try:
                sub = await self._nc.subscribe(subject, cb=self._on_message_cb)
            except Exception:
                self._ref_counts.pop(subject, None)
                logger.exception("[nats] subscribe failed subject=%s", subject)
                raise

            self._subs[subject] = sub
            logger.info(
                "[nats] subject active=%s refs=%s total_subjects=%s",
                subject,
                next_count,
                len(self._subs),
            )

    async def stop(self, subject: str):
        """
        Decrement local interest for subject and remove NATS subscription at 0 refs.
        """
        async with self._lock:
            current = self._ref_counts.get(subject, 0)
            if current == 0:
                logger.debug("[nats] unsubscribe skipped, no refs for subject=%s", subject)
                return

            next_count = current - 1
            if next_count > 0:
                self._ref_counts[subject] = next_count
                logger.debug(
                    "[nats] subscribe ref-- subject=%s refs=%s",
                    subject,
                    next_count,
                )
                return

            self._ref_counts.pop(subject, None)
            sub = self._subs.pop(subject, None)

        if sub is None:
            logger.warning("[nats] missing subscription object for subject=%s", subject)
            return

        logger.info("[nats] unsubscribe %s", subject)
        await sub.unsubscribe()
        logger.info("[nats] total_subjects=%s", len(self._subs))

    async def stop_all(self):
        async with self._lock:
            to_stop = list(self._subs.items())
            self._subs.clear()
            self._ref_counts.clear()

        if not to_stop:
            return

        logger.info("[nats] stopping %s active subscriptions", len(to_stop))
        for subject, sub in to_stop:
            try:
                await sub.unsubscribe()
                logger.info("[nats] unsubscribed %s during shutdown", subject)
            except Exception:
                logger.exception("[nats] failed to unsubscribe %s during shutdown", subject)
