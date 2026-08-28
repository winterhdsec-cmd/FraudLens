"""
通用审批引擎（ADR-18/19，R-1/R-2）。

支持多级串行审批 / 会签 / 驳回 / 委派，可被止付冻结/结案/协查通报等复用。
审批流状态机：pending(待审) → approved(通过)/rejected(驳回)/cancelled(撤销)

设计：
  - create_flow(business_type, business_id, applicant, chain, payload) 创建审批流
  - approve(flow_id, approver, comment) 当前层级审批通过，自动推进到下一层
  - reject(flow_id, approver, comment) 驳回（整个流程终止）
  - get_pending_for_user(user) 获取待该用户审批的流程列表
  - 审批通过后触发回调（业务侧注册 on_approved/on_rejected）
"""
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from database import db
from database.workflow_models import ApprovalFlow, ApprovalNode
from tools.response import logger


# ── 审批流状态 ──
FLOW_PENDING = "pending"
FLOW_APPROVED = "approved"
FLOW_REJECTED = "rejected"
FLOW_CANCELLED = "cancelled"

NODE_APPROVED = "approved"
NODE_REJECTED = "rejected"
NODE_DELEGATED = "delegated"


# ── 审批通过/驳回的回调注册（业务侧注册，如止付冻结执行） ──
_approval_callbacks: Dict[str, Dict[str, Callable]] = {}


def register_approval_callback(business_type: str,
                                on_approved: Callable = None,
                                on_rejected: Callable = None):
    """注册审批结果回调。

    business_type: freeze_order / case_close / cooperation 等
    on_approved(flow: ApprovalFlow): 审批通过回调
    on_rejected(flow: ApprovalFlow): 审批驳回回调
    """
    _approval_callbacks[business_type] = {
        "on_approved": on_approved,
        "on_rejected": on_rejected,
    }


def _gen_flow_id() -> str:
    return f"APV_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


def create_flow(business_type: str, business_id: str,
                applicant_id: int, applicant_name: str, department: str,
                approval_chain: List[Dict[str, Any]],
                summary: str = "", payload: Dict[str, Any] = None) -> ApprovalFlow:
    """创建审批流。

    approval_chain: [{level:1, role:'主办单位负责人', user_id:5, user_name:'张三'},
                     {level:2, role:'反诈中心负责人', user_id:8, user_name:'李四'}]
    """
    flow = ApprovalFlow(
        flow_id=_gen_flow_id(),
        business_type=business_type,
        business_id=business_id,
        applicant_id=applicant_id,
        applicant_name=applicant_name,
        department=department,
        approval_chain=approval_chain,
        current_level=1,
        status=FLOW_PENDING,
        summary=summary,
        payload=payload or {},
    )
    db.session.add(flow)
    db.session.commit()
    logger.info(f"审批流创建: {flow.flow_id} ({business_type}/{business_id}), 共 {len(approval_chain)} 级")
    return flow


def _get_current_node_config(flow: ApprovalFlow) -> Optional[Dict[str, Any]]:
    """获取当前层级的审批节点配置"""
    for node in (flow.approval_chain or []):
        if node.get("level") == flow.current_level:
            return node
    return None


def approve(flow_id: str, approver_id: int, approver_name: str,
            approver_role: str = "", comment: str = "") -> Dict[str, Any]:
    """当前层级审批通过，自动推进到下一层；若已是最后一层，流程完成。

    Returns: {flow, completed, message}
    """
    flow = db.session.query(ApprovalFlow).filter_by(flow_id=flow_id).first()
    if not flow:
        raise ValueError(f"审批流不存在: {flow_id}")
    if flow.status != FLOW_PENDING:
        raise ValueError(f"审批流状态非 pending（当前 {flow.status}），无法审批")

    node_config = _get_current_node_config(flow)
    expected_user = (node_config or {}).get("user_id")
    # 校验审批人身份（若配置了 user_id 则需匹配；admin 可代审）
    if expected_user and approver_id != expected_user:
        # 检查是否 admin（admin 可代审任意层级）
        from database.models import User
        approver = db.session.get(User, approver_id)
        if not approver or approver.role != 'admin':
            raise ValueError(f"当前层级审批人应为 {node_config.get('user_name', expected_user)}，"
                             f"您（{approver_name}）无权审批此层级")

    # 自审自批防护：申请人不得审批自己发起的流程（admin 作为信任代理除外）
    if flow.applicant_id and approver_id == flow.applicant_id:
        from database.models import User
        _approver = db.session.get(User, approver_id)
        if not _approver or _approver.role != 'admin':
            raise ValueError("申请人不能审批自己发起的流程，请交由他人审批")

    # 记录审批节点
    node = ApprovalNode(
        flow_id=flow_id,
        level=flow.current_level,
        approver_id=approver_id,
        approver_name=approver_name,
        approver_role=approver_role or (node_config or {}).get("role", ""),
        decision=NODE_APPROVED,
        comment=comment,
    )
    db.session.add(node)

    # 推进到下一层
    max_level = max((n.get("level", 0) for n in (flow.approval_chain or [])), default=1)
    if flow.current_level >= max_level:
        # 最后一层通过，流程完成
        flow.status = FLOW_APPROVED
        flow.completed_at = datetime.utcnow()
        db.session.commit()
        # 触发通过回调
        _trigger_callback(flow.business_type, "on_approved", flow)
        return {"flow": flow.to_dict(), "completed": True,
                "message": "审批通过，流程已完成"}
    else:
        flow.current_level = flow.current_level + 1
        db.session.commit()
        return {"flow": flow.to_dict(), "completed": False,
                "message": f"第 {flow.current_level - 1} 级审批通过，"
                           f"待第 {flow.current_level} 级审批"}


def reject(flow_id: str, approver_id: int, approver_name: str,
           approver_role: str = "", comment: str = "") -> Dict[str, Any]:
    """驳回审批（整个流程终止）"""
    flow = db.session.query(ApprovalFlow).filter_by(flow_id=flow_id).first()
    if not flow:
        raise ValueError(f"审批流不存在: {flow_id}")
    if flow.status != FLOW_PENDING:
        raise ValueError(f"审批流状态非 pending（当前 {flow.status}），无法驳回")

    node_config = _get_current_node_config(flow)
    node = ApprovalNode(
        flow_id=flow_id,
        level=flow.current_level,
        approver_id=approver_id,
        approver_name=approver_name,
        approver_role=approver_role or (node_config or {}).get("role", ""),
        decision=NODE_REJECTED,
        comment=comment,
    )
    db.session.add(node)
    flow.status = FLOW_REJECTED
    flow.completed_at = datetime.utcnow()
    db.session.commit()
    # 触发驳回回调
    _trigger_callback(flow.business_type, "on_rejected", flow)
    return {"flow": flow.to_dict(), "completed": True, "message": "审批已驳回"}


def cancel(flow_id: str, operator_id: int, reason: str = "") -> Dict[str, Any]:
    """撤销审批流（仅申请人或 admin 可撤销）"""
    flow = db.session.query(ApprovalFlow).filter_by(flow_id=flow_id).first()
    if not flow:
        raise ValueError(f"审批流不存在: {flow_id}")
    if flow.status != FLOW_PENDING:
        raise ValueError(f"审批流状态非 pending（当前 {flow.status}），无法撤销")
    if flow.applicant_id != operator_id:
        from database.models import User
        op = db.session.get(User, operator_id)
        if not op or op.role != 'admin':
            raise ValueError("仅申请人或管理员可撤销审批流")
    flow.status = FLOW_CANCELLED
    flow.completed_at = datetime.utcnow()
    db.session.commit()
    return {"flow": flow.to_dict(), "completed": True, "message": "审批流已撤销"}


def get_pending_for_user(user: Dict[str, Any]) -> List[ApprovalFlow]:
    """获取待该用户审批的流程列表（按当前层级匹配 user_id，admin 可见全部待审）"""
    q = db.session.query(ApprovalFlow).filter_by(status=FLOW_PENDING)
    if user.get("role") == "admin":
        flows = q.all()
    else:
        # 匹配当前层级的 user_id
        flows = q.all()
        flows = [
            f for f in flows
            if _get_current_node_config(f) and
               _get_current_node_config(f).get("user_id") == user.get("id")
        ]
    return flows


def _trigger_callback(business_type: str, event: str, flow: ApprovalFlow):
    """触发业务侧注册的回调"""
    cb = _approval_callbacks.get(business_type, {})
    handler = cb.get(event)
    if handler:
        try:
            handler(flow)
        except Exception as e:
            logger.error(f"审批回调异常 ({business_type}.{event}): {e}")
