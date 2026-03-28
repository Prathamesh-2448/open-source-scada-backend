from flask import Blueprint, request, jsonify
from database import sock
from flask_jwt_extended import decode_token, jwt_required
import json
import uuid

plc_bp = Blueprint('plc', __name__)

# In-memory registry for tracking connected PLCs
# Structure: { "device_id": websocket_object }
connected_plcs = {}

@sock.route('/ws/plc')
def handle_plc_connection(ws):
    """
    Persistent WebSocket connection for PLC devices.
    URL: ws://localhost:5000/ws/plc?token=JWT_TOKEN
    """
    # 1. JWT Authentication via query parameter
    token = request.args.get('token')
    if not token:
        ws.send(json.dumps({"error": "Missing authentication token"}))
        return

    try:
        decode_token(token)
    except Exception as e:
        ws.send(json.dumps({"error": f"Invalid or expired token: {str(e)}"}))
        return

    print("New PLC connection attempt...")
    device_id = None

    while True:
        try:
            message = ws.receive()
            if message is None:
                break
                
            data = json.loads(message)

            # Registration Phase
            if not device_id:
                if 'device_id' in data:
                    device_id = data['device_id']
                    connected_plcs[device_id] = ws
                    print(f"PLC '{device_id}' registered successfully.")
                    ws.send(json.dumps({"status": "registered", "device_id": device_id}))
                else:
                    ws.send(json.dumps({"error": "Registration required. Send device_id"}))
                    continue
            else:
                # Handle incoming messages from registered PLC (e.g., acks)
                if data.get('type') == 'ack':
                    print(f"Received ACK from {device_id} for command {data.get('command_id')}: {data.get('result')}")
                elif data.get('type') == 'error':
                    print(f"Received ERROR from {device_id} for command {data.get('command_id')}: {data.get('error')}")
                else:
                    print(f"Received unknown message from {device_id}: {data}")

        except json.JSONDecodeError:
            ws.send(json.dumps({"error": "Invalid JSON format"}))
        except Exception as e:
            print(f"PLC Connection Error for {device_id}: {e}")
            break

    # Cleanup upon disconnect
    if device_id and device_id in connected_plcs:
        # Prevent removing a re-connected socket under the same ID
        if connected_plcs[device_id] == ws:
            del connected_plcs[device_id]
            print(f"PLC '{device_id}' disconnected and removed from registry.")


@plc_bp.route('/devices/<device_id>/command', methods=['POST'])
@jwt_required()
def send_plc_command(device_id):
    """
    Sends a structured command locally to a registered PLC over its WebSocket.
    Example payload: {"command": "START_MOTOR", "params": {"speed": 100}}
    """
    if device_id not in connected_plcs:
        return jsonify({"error": f"Device '{device_id}' is not connected."}), 404

    data = request.get_json(force=True, silent=True) or {}
    command = data.get('command')
    
    if not command:
        return jsonify({"error": "Missing 'command' field in payload."}), 400

    ws = connected_plcs[device_id]
    command_id = str(uuid.uuid4())

    try:
        # Construct the instruction envelope matching what PLCs expect
        payload = {
            "type": "command",
            "command_id": command_id,
            "command": command,
            "params": data.get("params", {})
        }
        
        ws.send(json.dumps(payload))
        
        return jsonify({
            "message": f"Command '{command}' sent successfully to '{device_id}'.",
            "command_id": command_id
        }), 200

    except Exception as e:
        print(f"Error sending command to {device_id}: {e}")
        # Automatically clean up if sending failed (socket likely closed)
        if device_id in connected_plcs and connected_plcs[device_id] == ws:
            del connected_plcs[device_id]
        return jsonify({"error": f"Failed to deliver command: {str(e)}"}), 500
