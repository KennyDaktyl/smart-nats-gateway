# app/nats/subjects.py
INVERTER_UPDATE = "device_communication.inverter.*.production.update"
RASPBERRY_HEARTBEAT = "device_communication.raspberry.*.heartbeat"
RASPBERRY_EVENTS = "device_communication.raspberry.{uuid}.events"
