from database import db

# Association Table: Links Users to Roles
# This table doesn't need a class because it's managed by the relationship helper
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id', ondelete='CASCADE'))
)

class Role(db.Model):
    """Table to store available roles: 'admin', 'operator', 'viewer'"""
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f"<Role {self.name}>"

class User(db.Model):
    """Main User table with relationship to the Roles table"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Store hashed passwords
    
    # Many-to-Many Relationship
    # This allows you to access roles via user.roles
    roles = db.relationship('Role', 
                            secondary=roles_users, 
                            backref=db.backref('users', lazy='dynamic'))

    def __repr__(self):
        return f"<User {self.username}>"