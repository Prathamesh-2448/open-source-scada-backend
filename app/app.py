from flask import Flask
from database import db, migrate, bcrypt, jwt, sock
from auth.routes import auth_bp
from sensors.routes import sensor_bp
from flask_cors import CORS
import os

def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True) # Allow CORS for all domains on all routes
    
    # Use environment variables if they exist (for Docker), otherwise default to local vars
    mysql_user = os.environ.get('MYSQL_USER', 'root')
    mysql_password = os.environ.get('MYSQL_PASSWORD', 'root')
    mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
    mysql_db = os.environ.get('MYSQL_DB', 'auth_db')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}:3306/{mysql_db}'
    app.config['JWT_SECRET_KEY'] = 'secret-key'

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    sock.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(sensor_bp) # WebSockets usually handle their own prefixes
    from dashboards.routes import dashboards_bp
    app.register_blueprint(dashboards_bp, url_prefix='/dashboards')
    
    from plc.routes import plc_bp
    app.register_blueprint(plc_bp) # Includes /devices REST endpoints and /ws/plc

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0')


















###############################################################################################################################



# from flask import Flask, jsonify
# from flask_sock import Sock
# from influxdb_client_3 import InfluxDBClient3, Point
# import datetime
# import json
# import time

# app = Flask(__name__)
# sock = Sock(app)

# # --- InfluxDB 3.0 Configuration ---
# token = "apiv3_CgOaF6faKN0zISCCoGE6oxg2bBAxfvg9HSEnZ1F-AXn3hlV7hlVeFEVlu30_GKcKtkAm8r0ClZGwHAuULVAsuA"
# org = "YOUR_ORG"
# host = "http://localhost:8181" # Change to your region
# database = "sensor_data_db"

# client = InfluxDBClient3(host=host, token=token, org=org, database=database)

# @app.route('/ping', methods=['GET'])
# def ping():
#     return jsonify({"status": "online", "message": "Flask is communicating with InfluxDB 3.0"}), 200

# @sock.route('/ws/sensor')
# def handle_sensor_stream(ws):
#     """
#     Handles persistent WebSocket connection.
#     Expects JSON: {"sensor_id": "Engine_01", "temp": 98.2, "rpm": 3000}
#     """
#     print("New sensor client connected.")
#     while True:
#         message = ws.receive()
#         try:
#             data = json.loads(message)
            
#             if 'sensor_id' not in data:
#                 ws.send(json.dumps({"error": "Missing sensor_id"}))
#                 continue

#             # Use sensor_id as the Table Name (Measurement)
#             table_name = data.pop('sensor_id')
            
#             # Prepare InfluxDB Point
#             point = Point(table_name).time(datetime.datetime.utcnow())

#             # Add numeric values as fields
#             for key, value in data.items():
#                 if isinstance(value, (int, float)):
#                     point.field(key, value)
#                 else:
#                     # Treat non-numeric data as tags (e.g., status, location)
#                     point.tag(key, str(value))

#             # Write to InfluxDB
#             client.write(record=point)
            
#             # Optional: Acknowledge receipt to the sensor
#             ws.send(json.dumps({"status": "success", "table": table_name}))

#         except json.JSONDecodeError:
#             ws.send(json.dumps({"error": "Invalid JSON format"}))
#         except Exception as e:
#             print(f"Error: {e}")
#             break # Close connection on critical error

# @sock.route('/ws/stream/<sensor_id>')
# def stream_sensor_data(ws, sensor_id):
#     """
#     Continuously queries InfluxDB for the latest data of a specific sensor
#     and streams it to the frontend/client.
#     """
#     print(f"Client subscribed to live feed for: {sensor_id}")
    
#     # Track the last timestamp we sent to avoid duplicates
#     last_timestamp = None

#     while True:
#         try:
#             # Query InfluxDB 3.0 using SQL
#             # We fetch the most recent record for this sensor's table
#             query = f"SELECT * FROM '{sensor_id}' ORDER BY time DESC LIMIT 1"
            
#             # Execute query
#             table = client.query(query=query, language="sql")
            
#             # Convert the result (PyArrow Table) to a list of dictionaries
#             results = table.to_pylist()

#             if results:
#                 latest_record = results[0]
#                 current_timestamp = latest_record.get('time')

#                 # Only send if the data is new
#                 if current_timestamp != last_timestamp:
#                     ws.send(json.dumps(latest_record, default=str))
#                     last_timestamp = current_timestamp

#             # Wait before the next poll (adjust based on your sensor frequency)
#             time.sleep(2) 

#         except Exception as e:
#             print(f"Streaming error: {e}")
#             break # Close connection if client disconnects

# if __name__ == '__main__':
#     app.run(debug=True, port=5000)
