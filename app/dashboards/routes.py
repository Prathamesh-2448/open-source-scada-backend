from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db
from auth.models import User
from dashboards.models import Dashboard

dashboards_bp = Blueprint('dashboards', __name__)

@dashboards_bp.route('/', methods=['POST'])
@jwt_required()
def create_dashboard():
    """
    Creates a new Dashboard.
    Payload expected: {"name": "...", "description": "...", "layout_data": {"nodes": [...], "edges": [...]}}
    """
    data = request.get_json(force=True, silent=True) or {}
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    new_dashboard = Dashboard(
        name=data.get('name', 'Untitled Dashboard'),
        description=data.get('description', ''),
        layout_data=data.get('layout_data', {}),  # This stores the React Flow mapping and dropdown metric endpoint
        user_id=user.id
    )

    db.session.add(new_dashboard)
    db.session.commit()

    return jsonify({"message": "Dashboard created successfully", "id": new_dashboard.id}), 201

@dashboards_bp.route('/', methods=['GET'])
@jwt_required()
def list_dashboards():
    """
    Retrieves all dashboards for the logged-in user without returning large layout_data payloads.
    """
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    
    dashboards = Dashboard.query.filter_by(user_id=user.id).all()
    
    result = [{
        "id": d.id,
        "name": d.name,
        "description": d.description,
        "created_at": d.created_at,
        "updated_at": d.updated_at
    } for d in dashboards]
    
    return jsonify(result), 200

@dashboards_bp.route('/<int:dashboard_id>', methods=['GET'])
@jwt_required()
def get_dashboard(dashboard_id):
    """
    Fetches the full React Flow mapping data for the given dashboard ID.
    """
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    dashboard = Dashboard.query.filter_by(id=dashboard_id, user_id=user.id).first()

    if not dashboard:
        return jsonify({"message": "Dashboard not found"}), 404

    return jsonify({
        "id": dashboard.id,
        "name": dashboard.name,
        "description": dashboard.description,
        "layout_data": dashboard.layout_data,
        "created_at": dashboard.created_at,
        "updated_at": dashboard.updated_at
    }), 200

@dashboards_bp.route('/<int:dashboard_id>', methods=['PUT'])
@jwt_required()
def update_dashboard(dashboard_id):
    """
    Updates the entire dashboard. Used when 'Save Layout' or 'Update Metrics' is clicked.
    """
    data = request.get_json(force=True, silent=True) or {}
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    
    dashboard = Dashboard.query.filter_by(id=dashboard_id, user_id=user.id).first()
    if not dashboard:
        return jsonify({"message": "Dashboard not found"}), 404

    if 'name' in data: dashboard.name = data['name']
    if 'description' in data: dashboard.description = data['description']
    # layout_data holds the structure: { nodes: [{ data: { metricEndpoint: "...", ... } }], edges: [...] }
    if 'layout_data' in data: dashboard.layout_data = data['layout_data']

    db.session.commit()

    return jsonify({"message": "Dashboard updated successfully"}), 200

@dashboards_bp.route('/<int:dashboard_id>', methods=['DELETE'])
@jwt_required()
def delete_dashboard(dashboard_id):
    """
    Deletes the specific Dashboard map.
    """
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    dashboard = Dashboard.query.filter_by(id=dashboard_id, user_id=user.id).first()

    if not dashboard:
        return jsonify({"message": "Dashboard not found"}), 404

    db.session.delete(dashboard)
    db.session.commit()

    return jsonify({"message": "Dashboard deleted successfully"}), 200
