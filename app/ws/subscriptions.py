import asyncio

from app.core.logging import logger

# subject -> set(ws)
subscribers: dict[str, set] = {}

# ws -> set(subject)
ws_sets: dict = {}

_subs_lock = asyncio.Lock()


def ws_label(ws) -> str:
    peer = getattr(ws, "remote_address", None)
    if isinstance(peer, tuple) and len(peer) >= 2:
        peer_repr = f"{peer[0]}:{peer[1]}"
    else:
        peer_repr = str(peer) if peer else "unknown"
    return f"ws#{id(ws)}@{peer_repr}"


async def add_subscription(subject: str, ws) -> bool:
    """
    Add ws to subject.

    Returns:
        added -> whether ws was newly added to subject
    """
    async with _subs_lock:
        subs = subscribers.setdefault(subject, set())
        already = ws in subs
        subs.add(ws)
        ws_sets.setdefault(ws, set()).add(subject)

        logger.info(
            "[subs] %s <- %s (%s) | total=%s",
            subject,
            ws_label(ws),
            "already" if already else "new",
            len(subs),
        )

        return not already


async def remove_subscription(subject: str, ws) -> tuple[bool, bool]:
    """
    Remove ws from subject.

    Returns:
        removed  -> whether ws was removed from subject
        is_empty -> whether subject transitioned to 0 subscribers
    """
    async with _subs_lock:
        subs = subscribers.get(subject)
        if not subs or ws not in subs:
            return False, False

        subs.remove(ws)
        ws_subjects = ws_sets.get(ws)
        if ws_subjects is not None:
            ws_subjects.discard(subject)
            if not ws_subjects:
                ws_sets.pop(ws, None)

        logger.info(
            "[subs] %s -/-> %s | remaining=%s",
            subject,
            ws_label(ws),
            len(subs),
        )

        if not subs:
            subscribers.pop(subject, None)
            logger.info("[subs] subject %s has no remaining WS subscribers", subject)
            return True, True

        return True, False


async def remove_ws(ws) -> tuple[set[str], set[str]]:
    """
    Remove websocket from all subjects.

    Returns:
        removed_subjects: all subjects where ws was removed
        emptied_subjects: subjects that transitioned to 0 subscribers
    """
    async with _subs_lock:
        removed_subjects = ws_sets.pop(ws, set())
        emptied_subjects: set[str] = set()

        for subject in removed_subjects:
            subs = subscribers.get(subject)
            if not subs:
                continue

            subs.discard(ws)
            if not subs:
                subscribers.pop(subject, None)
                emptied_subjects.add(subject)

        logger.info(
            "[subs] %s removed from %s subjects",
            ws_label(ws),
            len(removed_subjects),
        )

        return set(removed_subjects), emptied_subjects


async def get_subscribers(subject: str) -> set:
    """
    Returns a snapshot of WS subscribers for subject.
    """
    async with _subs_lock:
        return set(subscribers.get(subject, set()))


async def register_client(ws):
    """
    Register new WS connection.
    """
    async with _subs_lock:
        ws_sets.setdefault(ws, set())
