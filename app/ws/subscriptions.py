# app/ws/subscriptions.py
from app.core.logging import logger

raspberry_subs: dict[str, set] = {}
inverter_subs: dict[str, set] = {}

clients = set()
raspberry_ws_sets: dict = {}


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


def add_raspberry_subscription(uuid: str, ws):
    subs = raspberry_subs.setdefault(uuid, set())
    already = ws in subs
    subs.add(ws)
    logger.info(
        f"[subs] Raspberry {uuid} <- {ws_label(ws)} "
        f"({'already' if already else 'new'}) | total for uuid={len(subs)}"
    )


def remove_raspberry_subscription(uuid: str, ws):
    subs = raspberry_subs.get(uuid)
    if subs is None:
        return

    subs.discard(ws)
    logger.info(
        f"[subs] Raspberry {uuid} removed {ws_label(ws)} "
        f"| remaining for uuid={len(subs)}"
    )
    if not subs:
        raspberry_subs.pop(uuid, None)
        logger.info(f"[subs] Raspberry {uuid} has no remaining WS subscribers")


def add_inverter_subscription(serial: str, ws):
    subs = inverter_subs.setdefault(serial, set())
    already = ws in subs
    subs.add(ws)
    logger.info(
        f"[subs] Inverter {serial} <- {ws_label(ws)} "
        f"({'already' if already else 'new'}) | total for serial={len(subs)}"
    )


def remove_inverter_subscription(serial: str, ws):
    subs = inverter_subs.get(serial)
    if subs is None:
        return

    subs.discard(ws)
    logger.info(
        f"[subs] Inverter {serial} removed {ws_label(ws)} "
        f"| remaining for serial={len(subs)}"
    )
    if not subs:
        inverter_subs.pop(serial, None)
        logger.info(f"[subs] Inverter {serial} has no remaining WS subscribers")


def remove_ws(ws):
    removed_raspberry = 0
    removed_inverter = 0

    raspberry_ws_sets.pop(ws, None)

    for uuid, subs in list(raspberry_subs.items()):
        if ws in subs:
            removed_raspberry += 1
            subs.discard(ws)
            if not subs:
                raspberry_subs.pop(uuid, None)

    for serial, subs in list(inverter_subs.items()):
        if ws in subs:
            removed_inverter += 1
            subs.discard(ws)
            if not subs:
                inverter_subs.pop(serial, None)

    clients.discard(ws)
    logger.info(
        f"[subs] {ws_label(ws)} removed from {removed_raspberry} raspberry "
        f"and {removed_inverter} inverter subscription(s)"
    )
    return removed_raspberry, removed_inverter


def get_cached_raspberry_set(ws):
    return raspberry_ws_sets.get(ws, set())


def cache_raspberry_set(ws, uuids: set[str]):
    raspberry_ws_sets[ws] = set(uuids)


def get_raspberry_subscribers(uuid: str):
    return raspberry_subs.get(uuid, set())


def get_inverter_subscribers(serial: str):
    return inverter_subs.get(serial, set())


def get_raspberry_subscriptions_for_ws(ws):
    """
    Return a set of UUIDs this websocket is subscribed to.
    """
    return {uuid for uuid, subs in raspberry_subs.items() if ws in subs}
