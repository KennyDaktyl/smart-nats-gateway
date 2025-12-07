# app/ws/subscriptions.py
raspberry_subs: dict[str, set] = {}
inverter_subs: dict[str, set] = {}

clients = set()


def add_raspberry_subscription(uuid: str, ws):
    raspberry_subs.setdefault(uuid, set()).add(ws)


def remove_raspberry_subscription(uuid: str, ws):
    subs = raspberry_subs.get(uuid)
    if subs is None:
        return

    subs.discard(ws)
    if not subs:
        raspberry_subs.pop(uuid, None)


def add_inverter_subscription(serial: str, ws):
    inverter_subs.setdefault(serial, set()).add(ws)


def remove_inverter_subscription(serial: str, ws):
    subs = inverter_subs.get(serial)
    if subs is None:
        return

    subs.discard(ws)
    if not subs:
        inverter_subs.pop(serial, None)


def remove_ws(ws):
    removed_raspberry = 0
    removed_inverter = 0

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
    return removed_raspberry, removed_inverter


def get_raspberry_subscribers(uuid: str):
    return raspberry_subs.get(uuid, set())


def get_inverter_subscribers(serial: str):
    return inverter_subs.get(serial, set())


def get_raspberry_subscriptions_for_ws(ws):
    """
    Return a set of UUIDs this websocket is subscribed to.
    """
    return {uuid for uuid, subs in raspberry_subs.items() if ws in subs}
