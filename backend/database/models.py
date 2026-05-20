from . import db
from sqlalchemy import Text, JSON, LargeBinary
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(64), default='')
    role = db.Column(db.String(20), default='police')
    department = db.Column(db.String(100), default='')
    phone = db.Column(db.String(20), default='')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'role': self.role,
            'department': self.department,
            'phone': self.phone,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class OperationLog(db.Model):
    __tablename__ = 'operation_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(64), default='')
    action = db.Column(db.String(64), nullable=False)
    target_type = db.Column(db.String(32), default='')
    target_id = db.Column(db.String(64), default='')
    detail = db.Column(JSON, default=dict)
    ip_address = db.Column(db.String(45), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MergeSuggestion(db.Model):
    __tablename__ = 'merge_suggestions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id_a = db.Column(db.String(32), db.ForeignKey('cases.case_id'), nullable=False)
    case_id_b = db.Column(db.String(32), db.ForeignKey('cases.case_id'), nullable=False)
    similarity = db.Column(db.Float, default=0.0)
    reason = db.Column(db.String(200), default='')
    status = db.Column(db.String(20), default='pending')
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)


class AnalysisSession(db.Model):
    __tablename__ = 'analysis_sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default='pending')
    total_cases = db.Column(db.Integer, default=0)
    total_gangs = db.Column(db.Integer, default=0)
    raw_input = db.Column(JSON)
    processing_info = db.Column(JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    cases = db.relationship('Case', backref='session', lazy='dynamic')
    gangs = db.relationship('Gang', backref='session', lazy='dynamic')


class Case(db.Model):
    __tablename__ = 'cases'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    number = db.Column(db.Integer, default=0)
    session_id = db.Column(db.String(64), db.ForeignKey('analysis_sessions.session_id'), nullable=True)
    title = db.Column(db.String(200), default='')
    scam_type = db.Column(db.String(100), default='')
    scam_subtype = db.Column(db.String(100), default='')
    risk_level = db.Column(db.String(10), default='LOW')
    risk_label = db.Column(db.String(20), default='低风险')
    risk_type = db.Column(db.String(20), default='info')
    risk_score = db.Column(db.Integer, default=0)
    victim_name = db.Column(db.String(50), default='')
    victim_gender = db.Column(db.String(10), default='')
    victim_age = db.Column(db.String(10), default='')
    victim_phone = db.Column(db.String(30), default='')
    victim_job = db.Column(db.String(50), default='')
    victim_address = db.Column(db.String(200), default='')
    amount = db.Column(db.String(50), default='')
    amount_value = db.Column(db.Float, default=0.0)
    description = db.Column(Text, default='')
    status = db.Column(db.String(20), default='待分析')
    source = db.Column(db.String(20), default='文本')
    ai_report = db.Column(Text, default='')
    keywords = db.Column(JSON, default=list)
    steps = db.Column(JSON, default=list)
    roles = db.Column(JSON, default=list)
    extracted_entities = db.Column(JSON, default=dict)
    message_count = db.Column(db.Integer, default=0)
    time_range = db.Column(db.String(50), default='')
    warning = db.Column(db.Text, nullable=True)
    is_error = db.Column(db.Boolean, default=False)
    embedding = db.Column(LargeBinary, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    persons = db.relationship('Person', backref='case', lazy='dynamic')
    evidence_items = db.relationship('EvidenceItem', backref='case', lazy='dynamic')


class Gang(db.Model):
    __tablename__ = 'gangs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gang_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    number = db.Column(db.Integer, default=0)
    session_id = db.Column(db.String(64), db.ForeignKey('analysis_sessions.session_id'), nullable=True)
    gang_name = db.Column(db.String(100), default='未命名团伙')
    risk_level = db.Column(db.String(10), default='C')
    risk_label = db.Column(db.String(20), default='低风险')
    risk_type = db.Column(db.String(20), default='info')
    threat_level = db.Column(db.String(5), default='C')
    comprehensive_score = db.Column(db.Integer, default=0)
    confidence = db.Column(db.Integer, default=0)
    member_count_estimate = db.Column(db.String(50), default='')
    tech_level = db.Column(db.String(10), default='中')
    script_type = db.Column(db.String(100), default='')
    total_cases = db.Column(db.Integer, default=0)
    total_amount = db.Column(db.String(50), default='')
    total_amount_value = db.Column(db.Float, default=0.0)
    description = db.Column(Text, default='')
    fingerprint = db.Column(JSON, default=list)
    enhanced_fingerprint = db.Column(JSON, default=list)
    steps = db.Column(JSON, default=list)
    radar_data = db.Column(JSON, default=dict)
    deep_characteristics = db.Column(JSON, default=list)
    risk_assessment = db.Column(JSON, default=dict)
    modus_operandi = db.Column(Text, default='')
    prevention_advice = db.Column(Text, default='')
    network_nodes = db.Column(JSON, default=list)
    centroid = db.Column(LargeBinary, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case_relations = db.relationship('GangCaseRelation', backref='gang', lazy='dynamic')


class GangCaseRelation(db.Model):
    __tablename__ = 'gang_case_relations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gang_id = db.Column(db.String(32), db.ForeignKey('gangs.gang_id'), nullable=False)
    case_id = db.Column(db.String(32), db.ForeignKey('cases.case_id'), nullable=False)
    similarity = db.Column(db.Float, default=0.0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('gang_id', 'case_id', name='uq_gang_case'),)


class Person(db.Model):
    __tablename__ = 'persons'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.String(32), db.ForeignKey('cases.case_id'), nullable=False)
    name = db.Column(db.String(50), default='')
    role = db.Column(db.String(20), default='')  # victim / suspect
    gender = db.Column(db.String(10), default='')
    age = db.Column(db.String(10), default='')
    phone = db.Column(db.String(30), default='')
    job = db.Column(db.String(50), default='')
    address = db.Column(db.String(200), default='')

    accounts = db.relationship('Account', backref='person', lazy='dynamic')
    phones = db.relationship('Phone', backref='person', lazy='dynamic')


class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'), nullable=True)
    account_number = db.Column(db.String(50), default='')
    bank_name = db.Column(db.String(100), default='')
    risk_level = db.Column(db.String(10), default='unknown')


class Phone(db.Model):
    __tablename__ = 'phones'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'), nullable=True)
    phone_number = db.Column(db.String(30), default='')
    carrier = db.Column(db.String(50), default='')
    risk_level = db.Column(db.String(10), default='unknown')


class EvidenceItem(db.Model):
    __tablename__ = 'evidence_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.String(32), db.ForeignKey('cases.case_id'), nullable=False)
    type = db.Column(db.String(50), default='')
    content = db.Column(Text, default='')
    status = db.Column(db.String(20), default='待验证')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AlertRecord(db.Model):
    __tablename__ = 'alert_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alert_type = db.Column(db.String(32), nullable=False)
    case_id = db.Column(db.String(32), nullable=False)
    matched_case_id = db.Column(db.String(32), nullable=False)
    matched_entities = db.Column(JSON, default=list)
    confidence = db.Column(db.Float, default=0.0)
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'case_id': self.case_id,
            'matched_case_id': self.matched_case_id,
            'matched_entities': self.matched_entities,
            'confidence': self.confidence,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }