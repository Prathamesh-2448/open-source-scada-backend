from flask import Blueprint, request
from database import sock, influx_client
from flask_jwt_extended import decode_token
import json, datetime, time
from influxdb_client_3 import Point

sensor_bp = Blueprint('sensors', __name__)

# @sock.route('/ws/sensor')
# def ingest_data(ws):
#     token = request.args.get('token')
#     try:
#         decoded = decode_token(token)
#         # Auth successful, start loop
#         while True:
#             message = ws.receive()
#             data = json.loads(message)
#             # InfluxDB Storage Logic here (same as previous step)
#             # ...
#     except Exception as e:
#         ws.send(json.dumps({"error": "Auth failed"}))

# --- Pub/Sub Memory Cache ---
_live_cache = {}

@sock.route('/ws/sensor')
def handle_sensor_ingest(ws):
    """
    URL: ws://localhost:5000/ws/sensor?token=JWT_TOKEN
    """
    # 1. JWT Authentication check via query parameter
    token = request.args.get('token')
    if not token:
        ws.send(json.dumps({"error": "Missing token"}))
        return

    try:
        decode_token(token)  # Validates expiration and signature
    except Exception:
        ws.send(json.dumps({"error": "Invalid or expired token"}))
        return

    print("New sensor client authorized and connected.")

    while True:
        message = ws.receive()
        try:
            data = json.loads(message)

            if 'sensor_id' not in data:
                ws.send(json.dumps({"error": "Missing sensor_id"}))
                continue

            # Extract table name
            table_name = data.pop('sensor_id')

            # Prepare InfluxDB Point
            point = Point(table_name).time(datetime.datetime.utcnow())

            # Sort data into fields (numbers) and tags (strings)
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    point.field(key, value)
                else:
                    point.tag(key, str(value))

            # Write to InfluxDB 3.0 for permanent storage
            influx_client.write(record=point)
            
            # Instantly update the live RAM cache for connected frontend dashboards
            # We append the current timestamp so the frontend graph gets exactly when it arrived
            data['time'] = datetime.datetime.utcnow().isoformat()
            _live_cache[table_name] = data
            
            ws.send(json.dumps({"status": "success", "table": table_name}))

        except json.JSONDecodeError:
            ws.send(json.dumps({"error": "Invalid JSON"}))
        except Exception as e:
            print(f"Ingest Error: {e}")
            break


# --- EGRESS ENDPOINT: Dashboard reads data from InfluxDB ---
@sock.route('/ws/stream/<sensor_id>')
def stream_sensor_data(ws, sensor_id):
    """
    URL: ws://localhost:5000/ws/stream/SensorName?token=JWT_TOKEN
    """
    token = request.args.get('token')
    try:
        decode_token(token)
    except Exception:
        ws.send(json.dumps({"error": "Unauthorized"}))
        return

    print(f"Client monitoring: {sensor_id}")
    last_timestamp = None

    while True:
        try:
            # Read instantly from our pub/sub memory cache instead of heavy SQL Polling
            latest_record = _live_cache.get(sensor_id)

            if latest_record:
                current_timestamp = latest_record.get('time')

                if current_timestamp != last_timestamp:
                    ws.send(json.dumps(latest_record))
                    last_timestamp = current_timestamp

            time.sleep(0.5)  # Poll the RAM cache safely at 2Hz

        except Exception as e:
            print(f"Streaming Error: {e}")
            break