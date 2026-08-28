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

    cases = db.relationship('Case', backref='session', lazy='selectin')
    gangs = db.relationship('Gang', backref='session', lazy='selectin')


class GraphNode(db.Model):
    """图节点表 - 持久化存储异构图节点"""
    __tablename__ = 'graph_nodes'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    node_type = db.Column(db.String(20), nullable=False, index=True)  # case, victim, phone, scam_type, city
    features = db.Column(JSON, default=dict)  # 节点特征
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GraphEdge(db.Model):
    """图边表 - 持久化存储异构图边"""
    __tablename__ = 'graph_edges'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source_id = db.Column(db.String(64), db.ForeignKey('graph_nodes.node_id'), nullable=False, index=True)
    target_id = db.Column(db.String(64), db.ForeignKey('graph_nodes.node_id'), nullable=False, index=True)
    relation = db.Column(db.String(30), nullable=False)  # has_victim, has_phone, is_type, in_city, similar
    weight = db.Column(db.Float, default=1.0)
    properties = db.Column(JSON, default=dict)  # 边的额外属性
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_edge_relation', 'relation'),
        db.UniqueConstraint('source_id', 'target_id', 'relation', name='uq_edge'),
    )


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
    # ADR-18 办案生命周期状态（与 status 分析态正交）：待立案/已立案/侦查中/待研判/研判中/研判完成/待结案/已归档
    lifecycle_status = db.Column(db.String(32), default='待立案', index=True)
    source = db.Column(db.String(20), default='文本')
    ai_report = db.Column(Text, default='')
    keywords = db.Column(JSON, default=list)
    steps = db.Column(JSON, default=list)
    roles = db.Column(JSON, default=list)
    extracted_entities = db.Column(JSON, default=dict)
    radar_data = db.Column(JSON, default=dict)
    message_count = db.Column(db.Integer, default=0)
    time_range = db.Column(db.String(50), default='')
    warning = db.Column(db.Text, nullable=True)
    is_error = db.Column(db.Boolean, default=False)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)
    department = db.Column(db.String(100), default='', index=True)  # G3 资源级 RBAC：录入/研判归属部门
    embedding = db.Column(LargeBinary, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    persons = db.relationship('Person', backref='case', lazy='selectin')
    evidence_items = db.relationship('EvidenceItem', backref='case', lazy='selectin')


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
    department = db.Column(db.String(100), default='', index=True)  # G3 资源级 RBAC

    case_relations = db.relationship('GangCaseRelation', backref='gang', lazy='selectin')


class GangCaseRelation(db.Model):
    """案件-团伙关联表（带可解释性）。

    改进点（vs 旧版只有 similarity）：
    - relation_type: 关联来源（share_account / share_perpetrator / similar_text / gnn_cluster / manual）
    - reason: 人类可读的关联理由（如"共享收款账户 6222****1234"）
    - matched_entities: 命中的实体列表（账户号、电话号等），供前端高亮展示
    """
    __tablename__ = 'gang_case_relations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gang_id = db.Column(db.String(32), db.ForeignKey('gangs.gang_id'), nullable=False)
    case_id = db.Column(db.String(32), db.ForeignKey('cases.case_id'), nullable=False)
    similarity = db.Column(db.Float, default=0.0)
    relation_type = db.Column(db.String(30), default='gnn_cluster')   # 关联来源
    reason = db.Column(db.String(500), default='')                    # 人类可读理由
    matched_entities = db.Column(JSON, default=list)                  # 命中的实体
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('gang_id', 'case_id', name='uq_gang_case'),)

    def to_dict(self):
        return {
            'gang_id': self.gang_id,
            'case_id': self.case_id,
            'similarity': self.similarity,
            'relation_type': self.relation_type,
            'reason': self.reason,
            'matched_entities': self.matched_entities or [],
            'added_at': self.added_at.isoformat() if self.added_at else None,
        }


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

    accounts = db.relationship('Account', backref='person', lazy='selectin')
    phones = db.relationship('Phone', backref='person', lazy='selectin')


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


class FreezeDecision(db.Model):
    """冻卡决策事实表（A4.2，ADR-7 合规落地）。

    与 OperationLog（记'谁操作'）互补：本表记'决策事实'——
    团伙研判产出的冻卡建议（涉案账户 / 客观置信度 / 门控结论 / 复核人 / 时间），
    落 MySQL 可审计追溯。GangDetector 本身不碰 db，本表写入在路由层研判产出后。
    """

    __tablename__ = 'freeze_decisions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gang_id = db.Column(db.String(32), nullable=False, index=True)        # 对应 gangs.gang_id，如 GANG_001
    session_id = db.Column(db.String(64), nullable=True, index=True)      # 研判会话（来自 /agent-analyze）
    related_accounts = db.Column(JSON, default=list)                      # 冻结候选收款账户（freeze_candidates）
    related_perpetrators = db.Column(JSON, default=list)                  # 关联违法者
    confidence = db.Column(db.Float, default=0.0)                         # 客观置信度（非 LLM 自评）
    gate_decision = db.Column(db.String(20), default='待人工复核')        # 建议冻结 / 待人工复核（客观门控结论）
    risk_level = db.Column(db.String(10), default='LOW')                 # 团伙风险等级 HIGH/MEDIUM/LOW
    is_reflux = db.Column(db.Boolean, default=False)                      # 是否检测到资金回流闭环
    case_ids = db.Column(JSON, default=list)                             # 关联案件列表
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 复核人（人工复核后回填）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'gang_id': self.gang_id,
            'session_id': self.session_id,
            'related_accounts': self.related_accounts,
            'related_perpetrators': self.related_perpetrators,
            'confidence': self.confidence,
            'gate_decision': self.gate_decision,
            'risk_level': self.risk_level,
            'is_reflux': self.is_reflux,
            'case_ids': self.case_ids,
            'reviewer_id': self.reviewer_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ImportedFundFlow(db.Model):
    """导入的资���流水原始记录（合规留痕，可审计溯源）。

    与 CapitalFlow（按案件归属的派生态）区分：本表记录'用户上传的批量流水'，
    在绑定到具体研判会话/案件前即可留存，供 /agent-analyze 的 accounts_tx 消费与回溯。
    """

    __tablename__ = 'imported_fund_flows'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    operator = db.Column(db.String(64), default='')
    session_id = db.Column(db.String(64), nullable=True, index=True)
    source_file = db.Column(db.String(200), default='')
    from_account = db.Column(db.String(50), index=True)
    to_account = db.Column(db.String(50), index=True)
    amount = db.Column(db.Float, default=0.0)
    tx_timestamp = db.Column(db.String(50), default='')
    raw = db.Column(JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'operator': self.operator,
            'session_id': self.session_id,
            'source_file': self.source_file,
            'from_account': self.from_account,
            'to_account': self.to_account,
            'amount': self.amount,
            'tx_timestamp': self.tx_timestamp,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }