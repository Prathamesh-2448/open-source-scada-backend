from database import db
from datetime import datetime
from sqlalchemy.dialects.mysql import JSON

class Dashboard(db.Model):
    __tablename__ = 'dashboards'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    
    # layout_data will store the React Flow JSON configuration
    # This JSON should include `{nodes: [...], edges: [...]}`
    # Each node can store something like:
    # {
    #   "id": "block-1",
    #   "type": "machineBlock",
    #   "position": { "x": 100, "y": 200 },
    #   "data": { "label": "Engine 1", "metricsEndpoint": "ws://.../stream/Engine_01" }
    # }
    layout_data = db.Column(JSON, nullable=False, default=dict)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Link back to the user who created it
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    def __repr__(self):
        return f"<Dashboard {self.name}>"
