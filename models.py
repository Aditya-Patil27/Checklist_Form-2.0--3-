from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    machine_id = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='Operator')
    assigned_checklists = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'employee_id': self.employee_id,
            'machine_id': self.machine_id,
            'role': self.role,
            'assigned_checklists': self.assigned_checklists
        }


class Submission(db.Model):
    __tablename__ = 'submissions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slug = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    operator_name = db.Column(db.String(100), nullable=False)
    operator_id = db.Column(db.String(50), nullable=False)
    machine_id = db.Column(db.String(50), nullable=False)
    batch_no = db.Column(db.String(20), nullable=False)
    checklist_no = db.Column(db.Integer, nullable=False)
    shift = db.Column(db.String(20), default='no_shift')
    payload = db.Column(db.Text, nullable=False)
    verify_status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'slug': self.slug,
            'category': self.category,
            'operator_name': self.operator_name,
            'operator_id': self.operator_id,
            'machine_id': self.machine_id,
            'batch_no': self.batch_no,
            'checklist_no': self.checklist_no,
            'shift': self.shift,
            'verify_status': self.verify_status,
            'created_at': self.created_at.isoformat()
        }