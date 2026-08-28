"""
办案工作流数据模型（Phase R1，docs/15 ADR-18/19）。

本模块承载"真实办案系统"的核心实体，与现有 models.py（研判分析域）解耦：
  - 案件生命周期状态机（立案→侦查→研判→止付→结案→归档）
  - 研判任务（InvestigationTask）——绑定案件、记录每次研判输入输出与操作人
  - 止付冻结工单（FreezeOrder）——申请/审批/执行/回执/解冻完整闭环
  - HITL 复核任务（ReviewTask）——低置信结论进复核、意见回写、触发再分析
  - 通用审批流（ApprovalFlow）——多级审批/会签/驳回，可被止付/结案等复用

设计原则（ADR-18/19）：
  - 研判引擎是"可被调用的能力"，案件生命周期为系统主轴
  - 所有影响法律后果的动作必须人工审批，系统只提供建议与依据
  - 审计留痕 append-only，与 OperationLog 互补
"""
from . import db
from sqlalchemy import JSON, Text, Float
from datetime import datetime


# ── 案件生命周期状态枚举（ADR-18） ──
# 与现有 Case.status（'待分析' 等分析态）正交：lifecycle_status 描述办案流程阶段
CASE_LIFECYCLE_STATUS = {
    "待立案": "pending_filing",     # 接警/报案录入后，等待立案审批
    "已立案": "filed",              # 立案审批通过
    "侦查中": "investigating",      # 分派主办人、启动侦查
    "待研判": "pending_analysis",   # 侦查收集材料完毕，准备研判
    "研判中": "analyzing",          # 研判进行中
    "研判完成": "analysis_done",    # 研判结束（含置信度门控结果）
    "待结案": "pending_close",      # 等待结案审批
    "已归档": "archived",           # 结案归档
}

# 合法状态流转（状态机边）
CASE_TRANSITIONS = {
    "待立案": ["已立案", "已归档"],          # 已立案=批准立案；已归档=不予立案
    "已立案": ["侦查中"],
    "侦查中": ["待研判", "待结案"],           # 待研判=材料齐备；待结案=直接结案
    "待研判": ["研判中"],
    "研判中": ["研判完成"],
    "研判完成": ["待结案", "侦查中"],         # 待结案=研判后结案；侦查中=需补充侦查
    "待结案": ["已归档", "侦查中"],           # 已归档=结案；侦查中=驳回补充侦查
    "已归档": [],                            # 终态
}


class CaseStatusTransition(db.Model):
    """案件状态流转记录（append-only，可审计追溯）。

    每次案件 lifecycle_status 变更落一条，记录操作人/前后状态/原因/时间，
    形成完整办案流程时间线，满足 §3.4 证据合规的可复现要求。
    """
    __tablename__ = 'case_status_transitions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.String(32), db.ForeignKey('cases.case_id'), nullable=False, index=True)
    from_status = db.Column(db.String(32), default='')
    to_status = db.Column(db.String(32), nullable=False)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    operator_name = db.Column(db.String(64), default='')
    reason = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'from_status': self.from_status,
            'to_status': self.to_status,
            'operator_id': self.operator_id,
            'operator_name': self.operator_name,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class InvestigationTask(db.Model):
    """研判任务实体（ADR-18）。

    绑定案件、记录每次研判的输入快照/输出结果/使用模型版本/随机种子/操作人。
    满足 §3.4 证据合规"分析过程可复现"：任意时刻可按 task 重放复现研判。
    """
    __tablename__ = 'investigation_tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.String(64), unique=True, nullable=False, index=True)  # INV_YYYYMMDDHHMMSS_xxxx
    case_id = db.Column(db.String(32), db.ForeignKey('cases.case_id'), nullable=False, index=True)
    gang_id = db.Column(db.String(32), nullable=True, index=True)  # 若研判产出团伙
    session_id = db.Column(db.String(64), nullable=True)  # 关联 AnalysisSession
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    operator_name = db.Column(db.String(64), default='')
    department = db.Column(db.String(100), default='', index=True)  # RBAC

    # 输入快照（含 cases 原始数据、accounts_tx、参数），JSON 存储
    input_snapshot = db.Column(JSON, default=dict)
    # 研判输出（gangs/statistics/reflection/quality_score）
    output_result = db.Column(JSON, default=dict)
    # 置信度门控结果
    gate_decision = db.Column(db.String(20), default='')  # 建议冻结 / 待人工复核
    confidence = db.Column(db.Float, default=0.0)
    quality_score = db.Column(db.Float, default=0.0)

    # 可复现性：模型版本/参数/种子
    model_version = db.Column(db.String(64), default='')
    use_gnn = db.Column(db.Boolean, default=False)
    use_llm = db.Column(db.Boolean, default=False)
    random_seed = db.Column(db.Integer, nullable=True)

    status = db.Column(db.String(20), default='completed')  # running/completed/failed
    error_message = db.Column(db.Text, default='')
    processing_time = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'case_id': self.case_id,
            'gang_id': self.gang_id,
            'session_id': self.session_id,
            'operator_id': self.operator_id,
            'operator_name': self.operator_name,
            'department': self.department,
            'input_snapshot': self.input_snapshot,
            'output_result': self.output_result,
            'gate_decision': self.gate_decision,
            'confidence': self.confidence,
            'quality_score': self.quality_score,
            'model_version': self.model_version,
            'use_gnn': self.use_gnn,
            'use_llm': self.use_llm,
            'random_seed': self.random_seed,
            'status': self.status,
            'error_message': self.error_message,
            'processing_time': self.processing_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class FreezeOrder(db.Model):
    """止付冻结工单（ADR-19，R-2）。

    完整闭环：申请 → 审批（多级）→ 执行（FreezeExecutor）→ 回执 → 解冻。
    与 FreezeDecision（研判产出的"建议"）关联：建议经人工审批后转为工单执行。
    所有步骤 append-only，文书可导出 PDF 作为诉讼证据。
    """
    __tablename__ = 'freeze_orders'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.String(64), unique=True, nullable=False, index=True)  # FRZ_YYYYMMDDHHMMSS_xxxx
    case_id = db.Column(db.String(32), db.ForeignKey('cases.case_id'), nullable=False, index=True)
    gang_id = db.Column(db.String(32), nullable=True, index=True)
    freeze_decision_id = db.Column(db.Integer, db.ForeignKey('freeze_decisions.id'), nullable=True)

    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    applicant_name = db.Column(db.String(64), default='')
    department = db.Column(db.String(100), default='', index=True)

    # 止付类型：止付(紧急)/冻结(正式)/续冻/解冻
    action_type = db.Column(db.String(20), default='冻结')  # 止付/冻结/续冻/解冻
    # 目标账户清单
    target_accounts = db.Column(JSON, default=list)  # [{account, bank, holder}]
    # 法律依据
    legal_basis = db.Column(db.String(500), default='')
    # 申请理由
    reason = db.Column(db.Text, default='')

    # 状态：draft/pending_approval/approved/rejected/executing/executed/partial/refunded/closed
    status = db.Column(db.String(20), default='draft', index=True)

    # 金额（用于分级审批）
    freeze_amount = db.Column(db.Float, default=0.0)

    # 文书（PDF 生成后存 MinIO 的对象 key）
    document_key = db.Column(db.String(200), default='')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
    executed_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'case_id': self.case_id,
            'gang_id': self.gang_id,
            'freeze_decision_id': self.freeze_decision_id,
            'applicant_id': self.applicant_id,
            'applicant_name': self.applicant_name,
            'department': self.department,
            'action_type': self.action_type,
            'target_accounts': self.target_accounts,
            'legal_basis': self.legal_basis,
            'reason': self.reason,
            'status': self.status,
            'freeze_amount': self.freeze_amount,
            'document_key': self.document_key,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
        }


class FreezeApproval(db.Model):
    """止付冻结审批记录（多级审批链）。

    一个 FreezeOrder 可有多条审批记录（主办单位负责人 → 反诈中心负责人）。
    """
    __tablename__ = 'freeze_approvals'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.String(64), db.ForeignKey('freeze_orders.order_id'), nullable=False, index=True)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approver_name = db.Column(db.String(64), default='')
    approver_role = db.Column(db.String(50), default='')  # 主办单位负责人/反诈中心负责人
    approval_level = db.Column(db.Integer, default=1)  # 审批层级 1,2,3...
    decision = db.Column(db.String(20), default='')  # approved/rejected
    comment = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'approver_id': self.approver_id,
            'approver_name': self.approver_name,
            'approver_role': self.approver_role,
            'approval_level': self.approval_level,
            'decision': self.decision,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class FreezeReceipt(db.Model):
    """止付冻结执行回执（FreezeExecutor 执行结果）。

    每个目标账户一条回执，记录执行成功/失败/部分成功。
    真实对接反诈平台/银行时由 FreezeExecutor 写入；Mock 实现模拟写入。
    """
    __tablename__ = 'freeze_receipts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.String(64), db.ForeignKey('freeze_orders.order_id'), nullable=False, index=True)
    target_account = db.Column(db.String(50), nullable=False)
    bank_name = db.Column(db.String(100), default='')
    execution_status = db.Column(db.String(20), default='')  # success/failed/partial
    execution_message = db.Column(db.String(500), default='')
    executed_by = db.Column(db.String(64), default='')  # 执行通道标识（mock/反诈平台/某银行）
    external_ref = db.Column(db.String(100), default='')  # 外部回执编号
    freeze_until = db.Column(db.DateTime, nullable=True)  # 冻结到期时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'target_account': self.target_account,
            'bank_name': self.bank_name,
            'execution_status': self.execution_status,
            'execution_message': self.execution_message,
            'executed_by': self.executed_by,
            'external_ref': self.external_ref,
            'freeze_until': self.freeze_until.isoformat() if self.freeze_until else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ReviewTask(db.Model):
    """HITL 人工复核任务（ADR-21，R-6）。

    当研判 gate_decision == "待人工复核" 时自动创建。
    复核人操作：确认并案/拆分团伙/修正诈骗类型/补充实体/标注误报。
    复核意见回写后，若修正了实体或并案 → 触发再分析（重跑 cluster）。
    复核数据沉淀为标注集，可用于未来模型迭代。
    """
    __tablename__ = 'review_tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    review_id = db.Column(db.String(64), unique=True, nullable=False, index=True)  # REV_YYYYMMDDHHMMSS_xxxx
    case_id = db.Column(db.String(32), db.ForeignKey('cases.case_id'), nullable=False, index=True)
    gang_id = db.Column(db.String(32), nullable=True, index=True)
    investigation_task_id = db.Column(db.String(64), db.ForeignKey('investigation_tasks.task_id'), nullable=True)

    # 待复核内容快照（研判产出的 gangs/置信度/门控结论）
    review_snapshot = db.Column(JSON, default=dict)
    confidence = db.Column(db.Float, default=0.0)
    original_gate_decision = db.Column(db.String(20), default='待人工复核')

    # 复核分派
    assigned_department = db.Column(db.String(100), default='', index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_to_name = db.Column(db.String(64), default='')

    # 状态：pending/assigned/in_review/resolved/rejected
    status = db.Column(db.String(20), default='pending', index=True)
    # 复核结论：confirmed_merge / split_gang / corrected_type / supplemented_entity / false_positive
    review_result = db.Column(db.String(32), default='')
    # 是否触发再分析
    triggered_reanalysis = db.Column(db.Boolean, default=False)
    reanalysis_task_id = db.Column(db.String(64), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    opinions = db.relationship('ReviewOpinion', backref='review_task', lazy='selectin')

    def to_dict(self):
        return {
            'id': self.id,
            'review_id': self.review_id,
            'case_id': self.case_id,
            'gang_id': self.gang_id,
            'investigation_task_id': self.investigation_task_id,
            'review_snapshot': self.review_snapshot,
            'confidence': self.confidence,
            'original_gate_decision': self.original_gate_decision,
            'assigned_department': self.assigned_department,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_to_name,
            'status': self.status,
            'review_result': self.review_result,
            'triggered_reanalysis': self.triggered_reanalysis,
            'reanalysis_task_id': self.reanalysis_task_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'opinions': [o.to_dict() for o in self.opinions] if self.opinions else [],
        }


class ReviewOpinion(db.Model):
    """复核意见（一条复核任务可有多条意见，记录复核人操作历史）"""
    __tablename__ = 'review_opinions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    review_id = db.Column(db.String(64), db.ForeignKey('review_tasks.review_id'), nullable=False, index=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reviewer_name = db.Column(db.String(64), default='')
    # 意见类型：confirm/split/correct_type/supplement_entity/mark_false_positive/comment
    opinion_type = db.Column(db.String(32), default='comment')
    # 修正内容（如拆分后的团伙划分、修正的诈骗类型、补充的实体）
    correction_data = db.Column(JSON, default=dict)
    comment = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'review_id': self.review_id,
            'reviewer_id': self.reviewer_id,
            'reviewer_name': self.reviewer_name,
            'opinion_type': self.opinion_type,
            'correction_data': self.correction_data,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ApprovalFlow(db.Model):
    """通用审批流（可复用于止付冻结/结案/协查通报等）。

    一个审批流绑定一个业务对象（如 FreezeOrder），含多级审批节点。
    支持：多级串行审批 / 会签（多人同级）/ 驳回 / 委派。
    """
    __tablename__ = 'approval_flows'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    flow_id = db.Column(db.String(64), unique=True, nullable=False, index=True)  # APV_YYYYMMDDHHMMSS_xxxx
    # 业务对象类型与 ID（freeze_order / case_close / cooperation 等）
    business_type = db.Column(db.String(32), nullable=False)
    business_id = db.Column(db.String(64), nullable=False, index=True)
    # 申请人
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    applicant_name = db.Column(db.String(64), default='')
    department = db.Column(db.String(100), default='', index=True)
    # 审批流配置（JSON：[{level, role, name, user_id}]）
    approval_chain = db.Column(JSON, default=list)
    # 当前审批层级
    current_level = db.Column(db.Integer, default=1)
    # 状态：pending/approved/rejected/cancelled
    status = db.Column(db.String(20), default='pending', index=True)
    # 申请摘要
    summary = db.Column(db.String(500), default='')
    # 申请详情（JSON，业务对象快照）
    payload = db.Column(JSON, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'flow_id': self.flow_id,
            'business_type': self.business_type,
            'business_id': self.business_id,
            'applicant_id': self.applicant_id,
            'applicant_name': self.applicant_name,
            'department': self.department,
            'approval_chain': self.approval_chain,
            'current_level': self.current_level,
            'status': self.status,
            'summary': self.summary,
            'payload': self.payload,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class ApprovalNode(db.Model):
    """审批节点记录（每个层级的审批结果）"""
    __tablename__ = 'approval_nodes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    flow_id = db.Column(db.String(64), db.ForeignKey('approval_flows.flow_id'), nullable=False, index=True)
    level = db.Column(db.Integer, nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approver_name = db.Column(db.String(64), default='')
    approver_role = db.Column(db.String(50), default='')
    decision = db.Column(db.String(20), default='')  # approved/rejected/delegated
    comment = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'flow_id': self.flow_id,
            'level': self.level,
            'approver_id': self.approver_id,
            'approver_name': self.approver_name,
            'approver_role': self.approver_role,
            'decision': self.decision,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
