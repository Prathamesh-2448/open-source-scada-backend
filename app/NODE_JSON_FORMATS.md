# PLC Engine Node JSON Formats

This document describes the required JSON format for the `data` payload of each node type supported by the `PLCEngine` in `engine.py`. These JSON structures are used when deploying a React Flow logic graph to the PLC or loading a graph into the engine.

Every node must have an `id`, a `type`, and a `data` object.

## Interface Nodes (Hardware)

### 1. Digital Input
Initiates physical flows by reading from a GPIO pin.
```json
{
  "id": "node_1",
  "type": "digital_input",
  "data": {
    "pin": 4
  }
}
```

### 2. Digital Output
Terminates electrical flows by writing to a GPIO pin.
```json
{
  "id": "node_2",
  "type": "digital_output",
  "data": {
    "pin": 17
  }
}
```

## Logic Nodes (Gates & Comparators)

### 3. AND Gate
Outputs True only if all incoming connections are True.
```json
{
  "id": "node_3",
  "type": "and",
  "data": {}
}
```

### 4. OR Gate
Outputs True if any incoming connection is True.
```json
{
  "id": "node_4",
  "type": "or",
  "data": {}
}
```

### 5. Threshold Comparator
A numerical comparator. Supported operators: `>`, `<`, `>=`, `<=`, `==`, `!=`.
```json
{
  "id": "node_5",
  "type": "threshold",
  "data": {
    "operator": ">=",
    "value": 50
  }
}
```

## Timing & Signal Conditioning (Stateful)

### 6. Timer On (TON)
Delay On. Stays low until the input holds high continuously for the specified `delay` in seconds.
```json
{
  "id": "node_6",
  "type": "timer_on",
  "data": {
    "delay": 2.5
  }
}
```

### 7. Timer Off (TOF)
Delay Off. Output stays high for the specified `delay` in seconds *after* the input shuts off.
```json
{
  "id": "node_7",
  "type": "timer_off",
  "data": {
    "delay": 5.0
  }
}
```

### 8. Debounce
Clears noisy signals. Drops fluttering until the signal is completely stable for the specified `delay` in seconds.
```json
{
  "id": "node_8",
  "type": "debounce",
  "data": {
    "delay": 0.5
  }
}
```

## Modbus Communications RS-485 (Hardware UART)

### 9. Modbus Read
Reads registers from external hardware and injects them into the circuit flow.
```json
{
  "id": "node_9",
  "type": "modbus_read",
  "data": {
    "slave_id": 1,
    "register_address": 40001
  }
}
```

### 10. Modbus Write
Writes incoming logic wires directly to Modbus registers over RS485.
```json
{
  "id": "node_10",
  "type": "modbus_write",
  "data": {
    "slave_id": 1,
    "register_address": 40001
  }
}
```

## SCADA Network Telemetry (WebSockets)

### 11. WebSocket Ingress
Injects live remote telemetry data straight from a cloud/backend WebSocket feed into local PLC logic.
```json
{
  "id": "node_11",
  "type": "websocket_ingress",
  "data": {
    "url": "ws://localhost:5000/ws/stream/Engine_01",
    "sensor_id": "Engine_01"
  }
}
```

### 12. WebSocket Egress
Pumps local Pi pin logic or raw numbers over a WebSocket connection to the centralized cloud ingestion database.
```json
{
  "id": "node_12",
  "type": "websocket_egress",
  "data": {
    "url": "ws://localhost:5000/ws/sensor",
    "sensor_id": "Remote_Pi_Sensor"
  }
}
```
