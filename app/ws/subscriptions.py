# app/ws/subscriptions.py
from app.core.logging import logger

subscribers: dict[str, set] = {}

clients = set()
ws_sets: dict = {}


def ws_label(ws) -> str:
    """
    Helper used only for logging to identify a websocket connection.
    """
    peer = getattr(ws, "remote_address", None)
    if isinstance(peer, tuple) and len(peer) >= 2:
        peer_repr = f"{peer[0]}:{peer[1]}"
    else:
        peer_repr = str(peer) if peer else "unknown"
    return f"ws#{id(ws)}@{peer_repr}"


def add_subscription(subject: str, ws):
    subs = subscribers.setdefault(subject, set())
    already = ws in subs
    was_empty = len(subs) == 0
    subs.add(ws)
    logger.info(
        f"[subs] Subject {subject} <- {ws_label(ws)} "
        f"({'already' if already else 'new'}) | total for uuid={len(subs)}"
    )
    return was_empty and not already


def remove_subscription(subject: str, ws):
    subs = subscribers.get(subject)
    if subs is None:
        return False

    had_ws = ws in subs
    subs.discard(ws)
    logger.info(
        f"[subs] Subject {subject} removed {ws_label(ws)} "
        f"| remaining for subject={len(subs)}"
    )
    if not subs and had_ws:
        subscribers.pop(subject, None)
        logger.info(f"[subs] Subject {subject} has no remaining WS subscribers")
        return True

    return False


def remove_ws(ws):
    removed_subscriber = 0
    emptied_subscriber: set[str] = set()

    ws_sets.pop(ws, None)

    for subject, subs in list(subscribers.items()):
        if ws in subs:
            removed_subscriber += 1
            subs.discard(ws)
            if not subs:
                subscribers.pop(subject, None)
                emptied_subscriber.add(subject)

    clients.discard(ws)
    logger.info(f"[subs] {ws_label(ws)} removed from {removed_subscriber} subscribers ")
    return removed_subscriber, emptied_subscriber


def get_cached_subcribers_set(ws):
    return ws_sets.get(ws, set())


def cache_subcribers_set(ws, subjects: set[str]):
    ws_sets[ws] = set(subjects)


def get_subscribers(subject: str):
    return subscribers.get(subject, set())


def get_subscribers_for_ws(ws):
    """
    Return a set of SUBJECTs this websocket is subscribed to.
    """
    return {subject for subject, subs in subscribers.items() if ws in subs}
