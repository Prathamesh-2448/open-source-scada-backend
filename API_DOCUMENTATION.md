# SCADA Backend API Documentation

The API is base-routed at `http://localhost:5000` (or whatever origin your server runs on) and grouped under three main segments: **Auth**, **Dashboards**, and **Sensors**.

---

## 1. Authentication Endpoints

These endpoints handle user registration and generating JSON Web Tokens (JWT) required to interact with the protected dashboard & sensor routes.

### `POST /auth/register`
Creates a new user account.
- **Headers:** `Content-Type: application/json`
- **Request Body Example:**
  ```json
  {
    "username": "admin_user",
    "password": "securepassword123",
    "role": "admin"  // Optional. Defaults to "operator"
  }
  ```
- **Success Response (201 Created):**
  ```json
  {
    "message": "User created"
  }
  ```

### `POST /auth/login`
Authenticates a user and returns a JWT access token.
- **Headers:** `Content-Type: application/json`
- **Request Body Example:**
  ```json
  {
    "username": "admin_user",
    "password": "securepassword123"
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpX..."
  }
  ```
- **Error Response (401 Unauthorized):** `{"message": "Invalid"}`

*Note: For all the endpoints below that require an Authorization header or Token Query, use the `access_token` returned from this endpoint.*

---

## 2. Dashboard Interface Endpoints

These endpoints handle CRUD operations for saving and loading React Flow visual dashboard configurations.

**Global Requirement for Dashboard routes:**
- **Headers:** `Authorization: Bearer <your_jwt_access_token>`
- **Headers:** `Content-Type: application/json` (Optional but recommended for POST/PUT)

### `POST /dashboards/`
Creates and saves a new React Flow visual mapping configuration.
- **Request Body Example:**
  ```json
  {
    "name": "Main Manufacturing Plant",
    "description": "Overview of Engine 1 and Engine 2",
    "layout_data": {
      "nodes": [
        {
          "id": "block-1",
          "type": "machineBlock",
          "position": { "x": 100, "y": 200 },
          "data": { 
             "label": "Engine 1", 
             "selectedSensorMetricWS": "ws://localhost:5000/ws/stream/Engine_01" 
          }
        }
      ],
      "edges": []
    }
  }
  ```
- **Success Response (201 Created):**
  ```json
  {
    "id": 1,
    "message": "Dashboard created successfully"
  }
  ```

### `GET /dashboards/`
Retrieves a lightweight list of all dashboards owned by the logged-in user. *(Excludes the heavy `layout_data` JSON).*
- **Success Response (200 OK):**
  ```json
  [
    {
      "created_at": "Fri, 20 Feb 2026 17:35:00 GMT",
      "description": "Overview of Engine 1 and Engine 2",
      "id": 1,
      "name": "Main Manufacturing Plant",
      "updated_at": "Fri, 20 Feb 2026 17:35:00 GMT"
    }
  ]
  ```

### `GET /dashboards/<dashboard_id>`
Fetches the full React Flow configuration map for rendering a specific dashboard based on its integer ID.
- **Success Response (200 OK):**
  ```json
  {
    "created_at": "Fri, 20 Feb 2026 17:35:00 GMT",
    "description": "Overview of Engine 1 and Engine 2",
    "id": 1,
    "layout_data": {
      "edges": [],
      "nodes": [
        {
          "data": {
            "label": "Engine 1",
            "selectedSensorMetricWS": "ws://localhost:5000/ws/stream/Engine_01"
          }
        }
      ]
    },
    "name": "Main Manufacturing Plant",
    "updated_at": "Fri, 20 Feb 2026 17:35:00 GMT"
  }
  ```
- **Error Response (404 Not Found):** `{"message": "Dashboard not found"}`

### `PUT /dashboards/<dashboard_id>`
Updates an existing dashboard map. Use this when the user moves React Flow blocks, adds new nodes, or changes the selected dropdown metrics, and hits "Save Layout".
- **Request Body Example:**
  ```json
  {
    "name": "Updated Plant View",
    "layout_data": {
       // Complete, updated React Flow mapping nodes/edges here
    }
  }
  ```
- **Success Response (200 OK):** `{"message": "Dashboard updated successfully"}`

### `DELETE /dashboards/<dashboard_id>`
Deletes a specific dashboard layout map from the database.
- **Success Response (200 OK):** `{"message": "Dashboard deleted successfully"}`

---

## 3. Real-Time Sensor Endpoints (WebSockets)

These are WebSocket (`ws://`) endpoints powered by `flask_sock` built to interface sequentially with InfluxDB logic. 

**Global Requirement for WebSocket routes:**
Standard HTTP Headers (like `Authorization`) usually don't survive handshake processes easily in some strict WebSocket clients/browsers. Therefore, these authenticate via a URL query parameter: **`?token=<your_jwt_access_token>`**.

### `WS /ws/sensor`
**Ingestion Endpoint:** For physical machines/sensors to continuously stream their telemetry data into the system database (InfluxDB).
- **Exact Connection URL:** 
  `ws://localhost:5000/ws/sensor?token=eyJhbGciOiJIUzI...`
- **Expected Stream Frame (JSON Payload from Sensor):**
  ```json
  {
    "sensor_id": "Engine_01",
    "oil_pressure": 45.2,
    "rpm": 3200,
    "status": "running"
  }
  ```
- **Description:** The system will strip out `sensor_id` to use as the database table/measurement name. Numeric values (`oil_pressure`, `rpm`) are stored as db "fields", while Strings (`status`) are stored as indexable db "tags".
- **Success Frame (Returned from Server):** `{"status": "success", "table": "Engine_01"}`

### `WS /ws/stream/<sensor_id>`
**Egress Endpoint:** For the Frontend UI (React Flow Dashboard Blocks) to subscribe to a specific machine metric stream. It natively polls InfluxDB.
- **Exact Connection URL:** 
  `ws://localhost:5000/ws/stream/Engine_01?token=eyJhbGciOiJIUzI...`
- **Provided Stream Frame (JSON Output continuously pumped to Frontend):**
  ```json
  {
    "time": "2026-02-20T17:55:01.123Z",
    "oil_pressure": 45.2,
    "rpm": 3200,
    "status": "running"
  }
  ```
- **Description:** Sends a JSON frame containing the most recent database record corresponding to the `<sensor_id>` parameter down the pipe as soon as a new metric row arrives. You can use standard JavaScript `new WebSocket(endpoint)` inside each React flow block to hook up directly to this data feed.

---

## 4. PLC Networking & Control Endpoints

These endpoints manage bidirectional, real-time control logic with external hardware like Raspberry Pi PLCs. 

### `WS /ws/plc`
**PLC Persistent Connection:** An always-on WebSocket endpoint for PLC devices to maintain connection with the server and receive commands.
- **Exact Connection URL:** 
  `ws://localhost:5000/ws/plc?token=eyJhbGciOiJIUzI...`
- **Initial Registration Message (Sent by PLC upon connection):**
  ```json
  {
    "device_id": "RaspberryPi_01"
  }
  ```
- **Expected Responses from PLC (During Operation):**
  PLCs should send acknowledgement messages back up the connection when they finish processing commands.
  ```json
  {
    "type": "ack",
    "command_id": "uuid-string-of-command",
    "result": "Motor started."
  }
  ```

### `POST /devices/<device_id>/command`
**Send PLC Command:** Allows a web dashboard to send a real-time instruction straight down the localized socket to a specific connected PLC device.
- **Headers:** `Authorization: Bearer <your_jwt_access_token>`
  `Content-Type: application/json`
- **Request Body Example:**
  ```json
  {
    "command": "START_MOTOR",
    "params": {
      "speed": 100
    }
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "message": "Command 'START_MOTOR' sent successfully to 'RaspberryPi_01'.",
    "command_id": "4512bd34-92ca-49d7-8321-72f5bcaba321"
  }
  ```
- **Error Response (404 Not Found - Sensor Offline):** `{"error": "Device 'RaspberryPi_01' is not connected."}`
