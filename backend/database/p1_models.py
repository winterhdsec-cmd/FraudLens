from . import db
from sqlalchemy import JSON, Text
from datetime import datetime


class CapitalFlow(db.Model):
    __tablename__ = 'capital_flows'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.String(32), db.ForeignKey('cases.case_id'), nullable=False)
    source_account = db.Column(db.String(100), default='')
    target_account = db.Column(db.String(100), default='')
    bank_name = db.Column(db.String(100), default='')
    amount = db.Column(db.Float, default=0.0)
    transaction_time = db.Column(db.DateTime, nullable=True)
    direction = db.Column(db.String(10), default='out')
    level = db.Column(db.Integer, default=1)
    annotation = db.Column(Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'source_account': self.source_account,
            'target_account': self.target_account,
            'bank_name': self.bank_name,
            'amount': self.amount,
            'transaction_time': self.transaction_time.isoformat() if self.transaction_time else None,
            'direction': self.direction,
            'level': self.level,
            'annotation': self.annotation,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DispatchOrder(db.Model):
    __tablename__ = 'dispatch_orders'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alert_id = db.Column(db.String(64), default='')
    case_id = db.Column(db.String(32), db.ForeignKey('cases.case_id'), nullable=False)
    assigned_dept = db.Column(db.String(100), default='')
    assigned_officer = db.Column(db.String(100), default='')
    status = db.Column(db.String(20), default='pending')
    dispatch_time = db.Column(db.DateTime, nullable=True)
    sign_time = db.Column(db.DateTime, nullable=True)
    feedback = db.Column(Text, nullable=True)
    deadline = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'case_id': self.case_id,
            'assigned_dept': self.assigned_dept,
            'assigned_officer': self.assigned_officer,
            'status': self.status,
            'dispatch_time': self.dispatch_time.isoformat() if self.dispatch_time else None,
            'sign_time': self.sign_time.isoformat() if self.sign_time else None,
            'feedback': self.feedback,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class KeyPerson(db.Model):
    __tablename__ = 'key_persons'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), default='')
    id_number = db.Column(db.String(18), unique=True, nullable=False)
    gender = db.Column(db.String(10), default='')
    age = db.Column(db.String(10), default='')
    phone = db.Column(db.String(30), default='')
    bank_account = db.Column(db.String(50), default='')
    address = db.Column(db.String(200), default='')
    risk_level = db.Column(db.String(10), default='B')
    risk_label = db.Column(db.String(20), default='中风险')
    person_type = db.Column(db.String(20), default='前科人员')
    tags = db.Column(JSON, default=list)
    case_ids = db.Column(JSON, default=list)
    source = db.Column(db.String(100), default='')
    notes = db.Column(Text, default='')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'id_number': self.id_number,
            'gender': self.gender,
            'age': self.age,
            'phone': self.phone,
            'bank_account': self.bank_account,
            'address': self.address,
            'risk_level': self.risk_level,
            'risk_label': self.risk_label,
            'person_type': self.person_type,
            'tags': self.tags if self.tags else [],
            'case_ids': self.case_ids if self.case_ids else [],
            'source': self.source,
            'notes': self.notes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }