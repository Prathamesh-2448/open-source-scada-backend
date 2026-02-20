from flask import Blueprint, request, jsonify
from database import db, bcrypt, jwt
from auth.models import User, Role
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(username=data['username'], password=hashed_pw)
    
    role = Role.query.filter_by(name=data.get('role', 'operator')).first()
    if role: user.roles.append(role)
    
    db.session.add(user)
    db.session.commit()
    return jsonify(message="User created"), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and bcrypt.check_password_hash(user.password, data['password']):
        token = create_access_token(
            identity=user.username, 
            additional_claims={"roles": [r.name for r in user.roles]}
        )
        return jsonify(access_token=token)
    return jsonify(message="Invalid"), 401