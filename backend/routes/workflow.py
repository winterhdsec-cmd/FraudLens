"""
办案工作流路由（Phase R1，docs/15 ADR-18/19/21）。

统一暴露"真实办案系统"的五大业务域 API：
  - 案件生命周期：立案/侦查/研判/结案/归档 状态机流转与时间线
  - 研判任务：绑定案件调用 OrchestratorAgent，落库可复现快照
  - 止付冻结工单：申请 → 审批 → 执行 → 回执 闭环
  - HITL 复核任务：低置信结论进复核，意见回写，触发再分析
  - 通用审批流：多级审批/会签/驳回，可被止付/结案等复用

设计原则：
  - 研判引擎是"可被调用的能力"，案件生命周期为系统主轴
  - 所有影响法律后果的动作（止付冻结/结案）必须人工审批
  - 所有写操作 append-only 审计留痕（OperationLog + 状态流转记录）
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from urllib.parse import quote as _urlquote

from database import db
from database.models import Case
from database.workflow_models import (
    CaseStatusTransition, CASE_LIFECYCLE_STATUS, CASE_TRANSITIONS,
    InvestigationTask, FreezeOrder, FreezeApproval, FreezeReceipt,
    ReviewTask, ReviewOpinion,
    ApprovalFlow, ApprovalNode,
)
from database.crud import _case_to_dict
from core import approval_engine
from core.approval_engine import (
    create_flow as create_approval_flow,
    approve as approve_flow,
    reject as reject_flow,
    cancel as cancel_flow,
    get_pending_for_user,
    FLOW_PENDING, FLOW_APPROVED, FLOW_REJECTED,
)
from tools.freeze_executor import get_freeze_executor
from tools.doc_generator import generate_freeze_order_doc, generate_investigation_report
from tools.response import logger
from .deps import get_current_user, log_operation, db_retry


router = APIRouter(prefix='/api/workflow', tags=['办案工作流'])


# ──────────────────────────────────────────────────────────────────────
# 模块加载时注册 freeze_order 审批回调：审批通过即执行止付冻结
# ──────────────────────────────────────────────────────────────────────
def _on_freeze_order_approved(flow: ApprovalFlow):
    """止付冻结审批通过回调：执行冻结并落库回执。"""
    order_id = flow.business_id
    order = db.session.query(FreezeOrder).filter_by(order_id=order_id).first()
    if not order:
        logger.error(f"止付冻结审批通过回调失败：工单 {order_id} 不存在")
        return
    try:
        order.status = 'approved'
        order.approved_at = datetime.utcnow()
        # 调用 FreezeExecutor 执行
        executor = get_freeze_executor()
        receipts_dto = executor.execute(order)
        # 落库回执
        for dto in receipts_dto:
            rec = FreezeReceipt(
                order_id=order_id,
                target_account=dto.target_account,
                bank_name=dto.bank_name,
                execution_status=dto.execution_status,
                execution_message=dto.execution_message,
                executed_by=dto.executed_by,
                external_ref=dto.external_ref,
                freeze_until=dto.freeze_until,
            )
            db.session.add(rec)
        # 统计执行结果
        success_count = sum(1 for d in receipts_dto if d.execution_status == 'success')
        if receipts_dto and success_count == len(receipts_dto):
            order.status = 'executed'
        elif success_count > 0:
            order.status = 'partial'
        else:
            order.status = 'failed'
        order.executed_at = datetime.utcnow()
        db.session.commit()
        logger.info(f"止付冻结工单 {order_id} 执行完成：{success_count}/{len(receipts_dto)} 成功")
    except Exception as e:
        db.session.rollback()
        logger.error(f"止付冻结执行异常（工单 {order_id}）: {e}")
        try:
            order = db.session.query(FreezeOrder).filter_by(order_id=order_id).first()
            if order:
                order.status = 'failed'
                db.session.commit()
        except Exception:
            pass


def _on_freeze_order_rejected(flow: ApprovalFlow):
    """止付冻结审批驳回回调。"""
    order_id = flow.business_id
    try:
        order = db.session.query(FreezeOrder).filter_by(order_id=order_id).first()
        if order:
            order.status = 'rejected'
            db.session.commit()
            logger.info(f"止付冻结工单 {order_id} 已驳回")
    except Exception as e:
        db.session.rollback()
        logger.error(f"止付冻结驳回回调异常（工单 {order_id}）: {e}")


approval_engine.register_approval_callback(
    business_type='freeze_order',
    on_approved=_on_freeze_order_approved,
    on_rejected=_on_freeze_order_rejected,
)


# ──────────────────────────────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────────────────────────────
def _gen_id(prefix: str) -> str:
    return f"{prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _ensure_workflow_tables():
    """幂等建表：确保办案工作流表存在（兼容历史库未迁移场景）。

    与 crud.py 中 FreezeDecision.__table__.create(checkfirst=True) 同模式：
    create_all 在启动时执行，但若历史库未迁移或建表失败，此处兜底。
    """
    try:
        for model_cls in (
            CaseStatusTransition, InvestigationTask, FreezeOrder,
            FreezeApproval, FreezeReceipt, ReviewTask, ReviewOpinion,
            ApprovalFlow, ApprovalNode,
        ):
            model_cls.__table__.create(bind=db.engine, checkfirst=True)
    except Exception as e:
        logger.warning(f"workflow 表幂等建表跳过: {e}")


# 模块加载时尝试建表（DB 未就绪则静默跳过，首次查询时各端点亦有 db_retry 兜底）
_ensure_workflow_tables()


def _record_transition(case_id: str, from_status: str, to_status: str,
                       operator: Dict[str, Any], reason: str = ''):
    """记录案件状态流转（append-only）。"""
    try:
        t = CaseStatusTransition(
            case_id=case_id,
            from_status=from_status or '',
            to_status=to_status,
            operator_id=operator.get('id'),
            operator_name=operator.get('username', '') or operator.get('display_name', ''),
            reason=reason or '',
        )
        db.session.add(t)
    except Exception as e:
        logger.warning(f"状态流转记录失败: {e}")


def _check_rbac(current_user: Dict[str, Any], item_department: str) -> bool:
    """资源级 RBAC 校验：admin 全量可见；非 admin 仅本部门或空部门可见。"""
    if current_user.get('role') == 'admin':
        return True
    user_dept = current_user.get('department', '') or ''
    return (item_department or '') in ('', user_dept)


def _content_disposition(filename: str) -> str:
    """构造支持中文文件名的 Content-Disposition（RFC 5987）。

    latin-1 header 无法直接承载中文，故提供 ASCII fallback + UTF-8 percent-encoded filename*。
    """
    ascii_fallback = filename.encode('ascii', 'ignore').decode('ascii') or 'document'
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{_urlquote(filename)}"


# ════════════════════════════════════════════════════════════════════
# 一、案件生命周期（状态机）
# ════════════════════════════════════════════════════════════════════

@router.get('/cases/{case_id}/lifecycle')
@db_retry()
async def api_get_case_lifecycle(case_id: str, current_user: dict = Depends(get_current_user)):
    """获取案件生命周期状态、可流转状态、时间线。"""
    try:
        case = db.session.query(Case).filter_by(case_id=case_id).first()
        if not case:
            return JSONResponse(status_code=404, content={"success": False, "error": "案件不存在"})
        if not _check_rbac(current_user, case.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权访问该案件"})

        current = case.lifecycle_status or '待立案'
        transitions = db.session.query(CaseStatusTransition).filter_by(
            case_id=case_id
        ).order_by(CaseStatusTransition.created_at.asc()).all()

        return {
            "success": True,
            "case_id": case_id,
            "current_status": current,
            "current_status_code": CASE_LIFECYCLE_STATUS.get(current, ''),
            "available_transitions": CASE_TRANSITIONS.get(current, []),
            "all_statuses": list(CASE_LIFECYCLE_STATUS.keys()),
            "timeline": [t.to_dict() for t in transitions],
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/cases/{case_id}/transition')
@db_retry()
async def api_transition_case(case_id: str, request: Request,
                              current_user: dict = Depends(get_current_user)):
    """案件状态流转（立案/侦查/研判/结案/归档）。

    Body: {to_status, reason}
    """
    try:
        body = await request.json()
        to_status = body.get('to_status', '').strip()
        reason = body.get('reason', '').strip()
        if not to_status:
            raise HTTPException(status_code=400, detail="缺少 to_status 参数")

        case = db.session.query(Case).filter_by(case_id=case_id).first()
        if not case:
            return JSONResponse(status_code=404, content={"success": False, "error": "案件不存在"})
        if not _check_rbac(current_user, case.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权操作该案件"})

        from_status = case.lifecycle_status or '待立案'
        if to_status not in CASE_LIFECYCLE_STATUS:
            raise HTTPException(status_code=400, detail=f"非法状态: {to_status}")
        allowed = CASE_TRANSITIONS.get(from_status, [])
        if to_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"非法流转：{from_status} → {to_status}（允许: {allowed}）"
            )

        case.lifecycle_status = to_status
        _record_transition(case_id, from_status, to_status, current_user, reason)
        db.session.commit()

        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'case_transition', 'case', case_id,
                      {'from': from_status, 'to': to_status, 'reason': reason}, ip_address=ip)

        return {
            "success": True,
            "case_id": case_id,
            "from_status": from_status,
            "to_status": to_status,
            "available_transitions": CASE_TRANSITIONS.get(to_status, []),
        }
    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/cases/{case_id}/timeline')
@db_retry()
async def api_get_case_timeline(case_id: str, current_user: dict = Depends(get_current_user)):
    """获取案件状态流转时间线（含研判/止付/复核关键事件）。"""
    try:
        case = db.session.query(Case).filter_by(case_id=case_id).first()
        if not case:
            return JSONResponse(status_code=404, content={"success": False, "error": "案件不存在"})
        if not _check_rbac(current_user, case.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权访问该案件"})

        events: List[Dict[str, Any]] = []
        # 状态流转
        transitions = db.session.query(CaseStatusTransition).filter_by(
            case_id=case_id
        ).order_by(CaseStatusTransition.created_at.asc()).all()
        for t in transitions:
            events.append({
                'time': t.created_at.isoformat() if t.created_at else None,
                'type': 'status_transition',
                'title': f"{t.from_status} → {t.to_status}",
                'operator': t.operator_name,
                'reason': t.reason,
            })
        # 研判任务
        tasks = db.session.query(InvestigationTask).filter_by(
            case_id=case_id
        ).order_by(InvestigationTask.created_at.asc()).all()
        for tk in tasks:
            events.append({
                'time': tk.created_at.isoformat() if tk.created_at else None,
                'type': 'investigation',
                'title': f"研判任务 {tk.task_id}",
                'operator': tk.operator_name,
                'status': tk.status,
                'confidence': tk.confidence,
                'gate_decision': tk.gate_decision,
            })
        # 止付冻结工单
        orders = db.session.query(FreezeOrder).filter_by(
            case_id=case_id
        ).order_by(FreezeOrder.created_at.asc()).all()
        for o in orders:
            events.append({
                'time': o.created_at.isoformat() if o.created_at else None,
                'type': 'freeze_order',
                'title': f"{o.action_type}工单 {o.order_id}",
                'operator': o.applicant_name,
                'status': o.status,
                'amount': o.freeze_amount,
            })
        # 复核任务
        reviews = db.session.query(ReviewTask).filter_by(
            case_id=case_id
        ).order_by(ReviewTask.created_at.asc()).all()
        for r in reviews:
            events.append({
                'time': r.created_at.isoformat() if r.created_at else None,
                'type': 'review',
                'title': f"复核任务 {r.review_id}",
                'operator': r.assigned_to_name,
                'status': r.status,
                'result': r.review_result,
            })
        events.sort(key=lambda x: x.get('time') or '')
        return {"success": True, "case_id": case_id, "timeline": events, "total": len(events)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ════════════════════════════════════════════════════════════════════
# 二、研判任务（InvestigationTask）
# ════════════════════════════════════════════════════════════════════

@router.get('/investigations')
@db_retry()
async def api_list_investigations(case_id: str = '', limit: int = 50,
                                  current_user: dict = Depends(get_current_user)):
    """研判任务列表（可按案件过滤）。"""
    try:
        q = db.session.query(InvestigationTask)
        if case_id:
            q = q.filter_by(case_id=case_id)
        if current_user.get('role') != 'admin':
            dept = current_user.get('department', '') or ''
            q = q.filter(db.or_(
                InvestigationTask.department == dept,
                InvestigationTask.department == '',
            ))
        tasks = q.order_by(InvestigationTask.created_at.desc()).limit(min(limit, 200)).all()
        return {"success": True, "tasks": [t.to_dict() for t in tasks], "total": len(tasks)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/investigations/{task_id}')
@db_retry()
async def api_get_investigation(task_id: str, current_user: dict = Depends(get_current_user)):
    """研判任务详情（含输入快照/输出结果，可复现）。"""
    try:
        task = db.session.query(InvestigationTask).filter_by(task_id=task_id).first()
        if not task:
            return JSONResponse(status_code=404, content={"success": False, "error": "研判任务不存在"})
        if not _check_rbac(current_user, task.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权访问"})
        return {"success": True, "task": task.to_dict()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/cases/{case_id}/investigations')
@db_retry()
async def api_create_investigation(case_id: str, request: Request,
                                   current_user: dict = Depends(get_current_user)):
    """对指定案件发起研判（调用 OrchestratorAgent，落库可复现快照）。

    Body: {accounts_tx?: [], use_gnn?: bool, extra_cases?: []}
    """
    import time
    t0 = time.time()
    try:
        case = db.session.query(Case).filter_by(case_id=case_id).first()
        if not case:
            return JSONResponse(status_code=404, content={"success": False, "error": "案件不存在"})
        if not _check_rbac(current_user, case.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权操作该案件"})

        body = await request.json() if request.headers.get('content-type', '').startswith('application/json') else {}
        accounts_tx = body.get('accounts_tx', [])
        use_gnn = body.get('use_gnn', True)
        extra_cases = body.get('extra_cases', [])

        # 案件状态校验：需处于"待研判/研判中/侦查中"
        if case.lifecycle_status not in ('待研判', '研判中', '侦查中', '研判完成', '待立案', '已立案'):
            # 自动流转到"研判中"
            from_status = case.lifecycle_status or '待立案'
            if '研判中' in CASE_TRANSITIONS.get(from_status, []):
                case.lifecycle_status = '研判中'
                _record_transition(case_id, from_status, '研判中', current_user, '发起研判')
            elif from_status not in ('研判中',):
                logger.info(f"案件 {case_id} 当前状态 {from_status}，仍允许发起研判")

        # 构造研判输入快照
        input_snapshot = {
            'case': _case_to_dict(case) or {},
            'accounts_tx': accounts_tx,
            'use_gnn': use_gnn,
            'extra_cases': extra_cases,
            'operator': {
                'id': current_user.get('id'),
                'username': current_user.get('username', ''),
                'department': current_user.get('department', ''),
            },
        }

        task_id = _gen_id('INV')
        investigation = InvestigationTask(
            task_id=task_id,
            case_id=case_id,
            operator_id=current_user.get('id'),
            operator_name=current_user.get('username', '') or current_user.get('display_name', ''),
            department=current_user.get('department', '') or case.department or '',
            input_snapshot=input_snapshot,
            status='running',
            use_gnn=use_gnn,
            use_llm=True,
        )
        db.session.add(investigation)
        case.lifecycle_status = '研判中'
        db.session.commit()

        # 调用 OrchestratorAgent
        try:
            from agents.orchestrator import OrchestratorAgent
            from core.llm_client import get_llm_client

            cases_input = [_case_to_dict(case)] if case else []
            cases_input.extend(extra_cases)

            orchestrator = OrchestratorAgent(llm_client=get_llm_client())
            result = orchestrator.process(cases_input, context={"accounts_tx": accounts_tx})

            # 关键：orchestrator 内部可能产生 DB 副作用（如团伙落库冲突）污染 session，
            # 此处 remove() 释放当前 scoped_session 并重建，保证后续查询的 session 干净可用。
            # 仅 rollback 不足以清理 scoped_session 的脏状态，必须 remove()。
            try:
                db.session.remove()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
            investigation = db.session.query(InvestigationTask).filter_by(task_id=task_id).first()
            case = db.session.query(Case).filter_by(case_id=case_id).first()
            if investigation is None:
                return JSONResponse(status_code=500, content={
                    "success": False, "error": "研判任务落库后查询失败", "task_id": task_id
                })

            investigation.output_result = result
            investigation.status = 'completed'
            investigation.processing_time = time.time() - t0
            investigation.completed_at = datetime.utcnow()
            statistics = result.get('statistics', {}) if isinstance(result, dict) else {}
            investigation.quality_score = float(statistics.get('quality_score', 0.0))
            gangs = result.get('gangs', []) if isinstance(result, dict) else []
            if gangs:
                investigation.gang_id = gangs[0].get('gang_id', '') if isinstance(gangs[0], dict) else ''
            # 置信度门控
            try:
                from database.crud import get_freeze_decisions
                fds = get_freeze_decisions(limit=10)
                if fds:
                    fd = fds[0]
                    investigation.confidence = float(fd.get('confidence', 0.0))
                    investigation.gate_decision = fd.get('gate_decision', '待人工复核')
                else:
                    investigation.confidence = float(statistics.get('quality_score', 0.0))
                    investigation.gate_decision = '建议冻结' if investigation.confidence >= 0.75 else '待人工复核'
            except Exception:
                investigation.confidence = float(statistics.get('quality_score', 0.0))
                investigation.gate_decision = '建议冻结' if investigation.confidence >= 0.75 else '待人工复核'

            # 研判完成流转
            if case and case.lifecycle_status == '研判中':
                _record_transition(case_id, '研判中', '研判完成', current_user, '研判任务完成')
                case.lifecycle_status = '研判完成'

            db.session.commit()

            # 低置信自动创建复核任务
            if investigation.gate_decision == '待人工复核' and investigation.confidence < 0.6:
                _auto_create_review_task(case_id, investigation, current_user)

            ip = request.client.host if request.client else ''
            log_operation(current_user['id'], current_user.get('username', ''),
                          'investigation_complete', 'case', case_id,
                          {'task_id': task_id, 'confidence': investigation.confidence,
                           'gate_decision': investigation.gate_decision}, ip_address=ip)
            return {
                "success": True,
                "task_id": task_id,
                "case_id": case_id,
                "result": result,
                "confidence": investigation.confidence,
                "gate_decision": investigation.gate_decision,
                "processing_time": investigation.processing_time,
            }
        except Exception as e:
            investigation.status = 'failed'
            investigation.error_message = str(e)
            investigation.processing_time = time.time() - t0
            db.session.commit()
            logger.error(f"研判执行失败（任务 {task_id}）: {e}")
            return JSONResponse(status_code=500, content={
                "success": False, "error": f"研判执行失败: {e}", "task_id": task_id
            })
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


def _auto_create_review_task(case_id: str, investigation: InvestigationTask,
                             current_user: Dict[str, Any]):
    """低置信研判结论自动创建 HITL 复核任务。"""
    try:
        review = ReviewTask(
            review_id=_gen_id('REV'),
            case_id=case_id,
            gang_id=investigation.gang_id,
            investigation_task_id=investigation.task_id,
            review_snapshot=investigation.output_result or {},
            confidence=investigation.confidence,
            original_gate_decision=investigation.gate_decision or '待人工复核',
            assigned_department=current_user.get('department', '') or '',
            status='pending',
        )
        db.session.add(review)
        db.session.commit()
        logger.info(f"低置信研判自动创建复核任务：case={case_id}, task={investigation.task_id}")
    except Exception as e:
        db.session.rollback()
        logger.warning(f"自动创建复核任务失败: {e}")


# ════════════════════════════════════════════════════════════════════
# 三、止付冻结工单（FreezeOrder）
# ════════════════════════════════════════════════════════════════════

@router.get('/freeze-orders')
@db_retry()
async def api_list_freeze_orders(case_id: str = '', status: str = '',
                                 limit: int = 50,
                                 current_user: dict = Depends(get_current_user)):
    """止付冻结工单列表。"""
    try:
        q = db.session.query(FreezeOrder)
        if case_id:
            q = q.filter_by(case_id=case_id)
        if status:
            q = q.filter_by(status=status)
        if current_user.get('role') != 'admin':
            dept = current_user.get('department', '') or ''
            q = q.filter(db.or_(
                FreezeOrder.department == dept,
                FreezeOrder.department == '',
            ))
        orders = q.order_by(FreezeOrder.created_at.desc()).limit(min(limit, 200)).all()
        return {"success": True, "orders": [o.to_dict() for o in orders], "total": len(orders)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/freeze-orders')
@db_retry()
async def api_create_freeze_order(request: Request,
                                  current_user: dict = Depends(get_current_user)):
    """创建止付冻结工单（draft 状态）。

    Body: {case_id, gang_id?, action_type, target_accounts, legal_basis, reason, freeze_amount, freeze_decision_id?}
    """
    try:
        body = await request.json()
        case_id = body.get('case_id', '').strip()
        if not case_id:
            raise HTTPException(status_code=400, detail="缺少 case_id")
        case = db.session.query(Case).filter_by(case_id=case_id).first()
        if not case:
            return JSONResponse(status_code=404, content={"success": False, "error": "案件不存在"})
        if not _check_rbac(current_user, case.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权操作该案件"})

        target_accounts = body.get('target_accounts', [])
        if not target_accounts:
            raise HTTPException(status_code=400, detail="缺少 target_accounts")

        order = FreezeOrder(
            order_id=_gen_id('FRZ'),
            case_id=case_id,
            gang_id=body.get('gang_id', ''),
            freeze_decision_id=body.get('freeze_decision_id'),
            applicant_id=current_user['id'],
            applicant_name=current_user.get('username', '') or current_user.get('display_name', ''),
            department=current_user.get('department', '') or case.department or '',
            action_type=body.get('action_type', '冻结'),
            target_accounts=target_accounts,
            legal_basis=body.get('legal_basis', ''),
            reason=body.get('reason', ''),
            status='draft',
            freeze_amount=float(body.get('freeze_amount', 0.0) or 0.0),
        )
        db.session.add(order)
        db.session.commit()

        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'create_freeze_order', 'freeze_order', order.order_id,
                      {'case_id': case_id, 'action_type': order.action_type,
                       'target_count': len(target_accounts)}, ip_address=ip)
        return {"success": True, "order": order.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/freeze-orders/{order_id}')
@db_retry()
async def api_get_freeze_order(order_id: str, current_user: dict = Depends(get_current_user)):
    """止付冻结工单详情（含审批记录/回执）。"""
    try:
        order = db.session.query(FreezeOrder).filter_by(order_id=order_id).first()
        if not order:
            return JSONResponse(status_code=404, content={"success": False, "error": "工单不存在"})
        if not _check_rbac(current_user, order.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权访问"})

        approvals = db.session.query(FreezeApproval).filter_by(
            order_id=order_id
        ).order_by(FreezeApproval.approval_level.asc()).all()
        receipts = db.session.query(FreezeReceipt).filter_by(
            order_id=order_id
        ).order_by(FreezeReceipt.created_at.asc()).all()
        # 关联审批流
        flows = db.session.query(ApprovalFlow).filter_by(
            business_type='freeze_order', business_id=order_id
        ).all()
        return {
            "success": True,
            "order": order.to_dict(),
            "approvals": [a.to_dict() for a in approvals],
            "receipts": [r.to_dict() for r in receipts],
            "approval_flows": [f.to_dict() for f in flows],
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/freeze-orders/{order_id}/submit')
@db_retry()
async def api_submit_freeze_order(order_id: str, request: Request,
                                  current_user: dict = Depends(get_current_user)):
    """提交止付冻结工单审批（创建审批流）。

    Body: {approval_chain: [{level, role, user_id, user_name}]}
    缺省审批链按金额分级：<10万 单级；10万-100万 两级；>100万 三级
    """
    try:
        order = db.session.query(FreezeOrder).filter_by(order_id=order_id).first()
        if not order:
            return JSONResponse(status_code=404, content={"success": False, "error": "工单不存在"})
        if not _check_rbac(current_user, order.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权操作"})
        if order.status not in ('draft', 'rejected'):
            raise HTTPException(status_code=400, detail=f"工单状态 {order.status} 不可提交审批")

        body = await request.json() if request.headers.get('content-type', '').startswith('application/json') else {}
        approval_chain = body.get('approval_chain')
        if not approval_chain:
            # 缺省审批链：按金额分级
            approval_chain = _default_approval_chain(order.freeze_amount, current_user)

        order.status = 'pending_approval'
        db.session.commit()

        flow = create_approval_flow(
            business_type='freeze_order',
            business_id=order_id,
            applicant_id=current_user['id'],
            applicant_name=current_user.get('username', '') or current_user.get('display_name', ''),
            department=current_user.get('department', '') or order.department or '',
            approval_chain=approval_chain,
            summary=f"{order.action_type}工单 {order_id}（案件 {order.case_id}，"
                    f"金额 {order.freeze_amount}，账户 {len(order.target_accounts or [])} 个）",
            payload=order.to_dict(),
        )

        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'submit_freeze_order', 'freeze_order', order_id,
                      {'flow_id': flow.flow_id, 'levels': len(approval_chain)}, ip_address=ip)
        return {
            "success": True,
            "order_id": order_id,
            "flow_id": flow.flow_id,
            "status": order.status,
            "approval_chain": approval_chain,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


def _default_approval_chain(amount: float, current_user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """按金额生成缺省审批链（<10万 单级；10-100万 两级；>100万 三级）。

    注：缺省链使用当前用户作为占位审批人（演示用）。真实部署应从组织架构查询实际审批人。
    """
    uid = current_user.get('id')
    uname = current_user.get('username', '') or current_user.get('display_name', '')
    if amount < 100000:
        return [{"level": 1, "role": "主办单位负责人", "user_id": uid, "user_name": uname}]
    elif amount < 1000000:
        return [
            {"level": 1, "role": "主办单位负责人", "user_id": uid, "user_name": uname},
            {"level": 2, "role": "反诈中心负责人", "user_id": uid, "user_name": uname},
        ]
    else:
        return [
            {"level": 1, "role": "主办单位负责人", "user_id": uid, "user_name": uname},
            {"level": 2, "role": "反诈中心负责人", "user_id": uid, "user_name": uname},
            {"level": 3, "role": "分管局领导", "user_id": uid, "user_name": uname},
        ]


@router.post('/freeze-orders/{order_id}/execute')
@db_retry()
async def api_execute_freeze_order(order_id: str, request: Request,
                                   current_user: dict = Depends(get_current_user)):
    """手动执行止付冻结（仅 admin，或审批通过后自动执行失败时手动重试）。"""
    try:
        order = db.session.query(FreezeOrder).filter_by(order_id=order_id).first()
        if not order:
            return JSONResponse(status_code=404, content={"success": False, "error": "工单不存在"})
        if not _check_rbac(current_user, order.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权操作"})
        if current_user.get('role') != 'admin' and order.status not in ('approved', 'failed', 'partial'):
            raise HTTPException(status_code=400,
                                detail=f"工单状态 {order.status} 不可执行（需 approved/failed/partial）")

        executor = get_freeze_executor()
        receipts_dto = executor.execute(order)
        for dto in receipts_dto:
            rec = FreezeReceipt(
                order_id=order_id,
                target_account=dto.target_account,
                bank_name=dto.bank_name,
                execution_status=dto.execution_status,
                execution_message=dto.execution_message,
                executed_by=dto.executed_by,
                external_ref=dto.external_ref,
                freeze_until=dto.freeze_until,
            )
            db.session.add(rec)
        success_count = sum(1 for d in receipts_dto if d.execution_status == 'success')
        if receipts_dto and success_count == len(receipts_dto):
            order.status = 'executed'
        elif success_count > 0:
            order.status = 'partial'
        else:
            order.status = 'failed'
        order.executed_at = datetime.utcnow()
        db.session.commit()

        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'execute_freeze_order', 'freeze_order', order_id,
                      {'success': success_count, 'total': len(receipts_dto)}, ip_address=ip)
        return {
            "success": True,
            "order_id": order_id,
            "status": order.status,
            "receipts": [r.to_dict() for r in db.session.query(FreezeReceipt).filter_by(order_id=order_id).all()],
        }
    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/freeze-orders/{order_id}/receipts')
@db_retry()
async def api_get_freeze_receipts(order_id: str, current_user: dict = Depends(get_current_user)):
    """止付冻结执行回执列表。"""
    try:
        order = db.session.query(FreezeOrder).filter_by(order_id=order_id).first()
        if not order:
            return JSONResponse(status_code=404, content={"success": False, "error": "工单不存在"})
        if not _check_rbac(current_user, order.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权访问"})
        receipts = db.session.query(FreezeReceipt).filter_by(
            order_id=order_id
        ).order_by(FreezeReceipt.created_at.asc()).all()
        return {"success": True, "receipts": [r.to_dict() for r in receipts], "total": len(receipts)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/freeze-orders/{order_id}/document')
@db_retry()
async def api_download_freeze_doc(order_id: str, request: Request,
                                  current_user: dict = Depends(get_current_user)):
    """下载止付/冻结文书（PDF 或 HTML）。"""
    from fastapi.responses import Response
    try:
        order = db.session.query(FreezeOrder).filter_by(order_id=order_id).first()
        if not order:
            return JSONResponse(status_code=404, content={"success": False, "error": "工单不存在"})
        if not _check_rbac(current_user, order.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权访问"})

        case = db.session.query(Case).filter_by(case_id=order.case_id).first()
        fmt = request.query_params.get('format', 'pdf')
        result = generate_freeze_order_doc(order, case=case,
                                           applicant=current_user, fmt=fmt)
        headers = {
            'Content-Disposition': _content_disposition(result["filename"])
        }
        return Response(content=result['content'],
                        media_type=result['content_type'],
                        headers=headers)
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/investigations/{task_id}/report')
@db_retry()
async def api_download_investigation_report(task_id: str, request: Request,
                                            current_user: dict = Depends(get_current_user)):
    """下载研判报告（PDF 或 HTML）。"""
    from fastapi.responses import Response
    try:
        task = db.session.query(InvestigationTask).filter_by(task_id=task_id).first()
        if not task:
            return JSONResponse(status_code=404, content={"success": False, "error": "研判任务不存在"})
        if not _check_rbac(current_user, task.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权访问"})

        case = db.session.query(Case).filter_by(case_id=task.case_id).first()
        fmt = request.query_params.get('format', 'pdf')
        result = generate_investigation_report(task, case=case, fmt=fmt)
        headers = {
            'Content-Disposition': _content_disposition(result["filename"])
        }
        return Response(content=result['content'],
                        media_type=result['content_type'],
                        headers=headers)
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/freeze-orders/{order_id}/cancel')
@db_retry()
async def api_cancel_freeze_order(order_id: str, request: Request,
                                  current_user: dict = Depends(get_current_user)):
    """撤销止付冻结工单（仅 draft/pending_approval 状态，申请人或 admin）。"""
    try:
        order = db.session.query(FreezeOrder).filter_by(order_id=order_id).first()
        if not order:
            return JSONResponse(status_code=404, content={"success": False, "error": "工单不存在"})
        if order.status not in ('draft', 'pending_approval', 'rejected'):
            raise HTTPException(status_code=400, detail=f"工单状态 {order.status} 不可撤销")
        if order.applicant_id != current_user['id'] and current_user.get('role') != 'admin':
            return JSONResponse(status_code=403, content={"success": False, "error": "仅申请人或管理员可撤销"})

        body = await request.json() if request.headers.get('content-type', '').startswith('application/json') else {}
        reason = body.get('reason', '')
        # 撤销关联审批流
        flows = db.session.query(ApprovalFlow).filter_by(
            business_type='freeze_order', business_id=order_id, status=FLOW_PENDING
        ).all()
        for f in flows:
            try:
                cancel_flow(f.flow_id, current_user['id'], reason)
            except Exception as e:
                logger.warning(f"撤销审批流 {f.flow_id} 失败: {e}")
        order.status = 'cancelled'
        order.closed_at = datetime.utcnow()
        db.session.commit()

        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'cancel_freeze_order', 'freeze_order', order_id,
                      {'reason': reason}, ip_address=ip)
        return {"success": True, "order_id": order_id, "status": order.status}
    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ════════════════════════════════════════════════════════════════════
# 四、HITL 复核任务（ReviewTask）
# ════════════════════════════════════════════════════════════════════

@router.get('/reviews')
@db_retry()
async def api_list_review_tasks(case_id: str = '', status: str = '',
                                limit: int = 50,
                                current_user: dict = Depends(get_current_user)):
    """复核任务列表。"""
    try:
        q = db.session.query(ReviewTask)
        if case_id:
            q = q.filter_by(case_id=case_id)
        if status:
            q = q.filter_by(status=status)
        if current_user.get('role') != 'admin':
            dept = current_user.get('department', '') or ''
            q = q.filter(db.or_(
                ReviewTask.assigned_department == dept,
                ReviewTask.assigned_department == '',
            ))
        tasks = q.order_by(ReviewTask.created_at.desc()).limit(min(limit, 200)).all()
        return {"success": True, "reviews": [t.to_dict() for t in tasks], "total": len(tasks)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/reviews/{review_id}')
@db_retry()
async def api_get_review_task(review_id: str, current_user: dict = Depends(get_current_user)):
    """复核任务详情（含意见历史）。"""
    try:
        task = db.session.query(ReviewTask).filter_by(review_id=review_id).first()
        if not task:
            return JSONResponse(status_code=404, content={"success": False, "error": "复核任务不存在"})
        if not _check_rbac(current_user, task.assigned_department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权访问"})
        return {"success": True, "review": task.to_dict()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/reviews/{review_id}/assign')
@db_retry()
async def api_assign_review(review_id: str, request: Request,
                            current_user: dict = Depends(get_current_user)):
    """分派复核任务。

    Body: {assigned_to_id?, assigned_to_name?, assigned_department?}
    """
    try:
        task = db.session.query(ReviewTask).filter_by(review_id=review_id).first()
        if not task:
            return JSONResponse(status_code=404, content={"success": False, "error": "复核任务不存在"})
        body = await request.json()
        task.assigned_to_id = body.get('assigned_to_id')
        task.assigned_to_name = body.get('assigned_to_name', '')
        task.assigned_department = body.get('assigned_department', current_user.get('department', ''))
        task.status = 'assigned'
        task.assigned_at = datetime.utcnow()
        db.session.commit()

        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'assign_review', 'review', review_id,
                      {'assigned_to': task.assigned_to_name}, ip_address=ip)
        return {"success": True, "review": task.to_dict()}
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/reviews/{review_id}/opinions')
@db_retry()
async def api_add_review_opinion(review_id: str, request: Request,
                                 current_user: dict = Depends(get_current_user)):
    """添加复核意见（append-only）。

    Body: {opinion_type, correction_data?, comment}
    opinion_type: confirm/split/correct_type/supplement_entity/mark_false_positive/comment
    """
    try:
        task = db.session.query(ReviewTask).filter_by(review_id=review_id).first()
        if not task:
            return JSONResponse(status_code=404, content={"success": False, "error": "复核任务不存在"})
        body = await request.json()
        opinion = ReviewOpinion(
            review_id=review_id,
            reviewer_id=current_user['id'],
            reviewer_name=current_user.get('username', '') or current_user.get('display_name', ''),
            opinion_type=body.get('opinion_type', 'comment'),
            correction_data=body.get('correction_data', {}),
            comment=body.get('comment', ''),
        )
        db.session.add(opinion)
        if task.status == 'pending':
            task.status = 'in_review'
        db.session.commit()

        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'add_review_opinion', 'review', review_id,
                      {'opinion_type': opinion.opinion_type}, ip_address=ip)
        return {"success": True, "opinion": opinion.to_dict()}
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/reviews/{review_id}/resolve')
@db_retry()
async def api_resolve_review(review_id: str, request: Request,
                             current_user: dict = Depends(get_current_user)):
    """完成复核（含结论，可触发再分析）。

    Body: {review_result, comment, trigger_reanalysis?: bool}
    review_result: confirmed_merge/split_gang/corrected_type/supplemented_entity/false_positive
    """
    try:
        task = db.session.query(ReviewTask).filter_by(review_id=review_id).first()
        if not task:
            return JSONResponse(status_code=404, content={"success": False, "error": "复核任务不存在"})
        body = await request.json()
        review_result = body.get('review_result', '')
        if not review_result:
            raise HTTPException(status_code=400, detail="缺少 review_result")

        task.review_result = review_result
        task.status = 'resolved'
        task.resolved_at = datetime.utcnow()
        trigger = bool(body.get('trigger_reanalysis', False))
        task.triggered_reanalysis = trigger

        # 记录最终意见
        opinion = ReviewOpinion(
            review_id=review_id,
            reviewer_id=current_user['id'],
            reviewer_name=current_user.get('username', '') or current_user.get('display_name', ''),
            opinion_type=review_result,
            correction_data=body.get('correction_data', {}),
            comment=body.get('comment', ''),
        )
        db.session.add(opinion)

        # 触发再分析：回写案件状态为"侦查中"（待补充侦查后重新研判）
        if trigger:
            case = db.session.query(Case).filter_by(case_id=task.case_id).first()
            if case and case.lifecycle_status == '研判完成':
                from_status = case.lifecycle_status
                case.lifecycle_status = '侦查中'
                _record_transition(task.case_id, from_status, '侦查中', current_user,
                                   f"复核触发再分析：{review_result}")

        db.session.commit()
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'resolve_review', 'review', review_id,
                      {'review_result': review_result, 'trigger_reanalysis': trigger}, ip_address=ip)
        return {"success": True, "review": task.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ════════════════════════════════════════════════════════════════════
# 五、通用审批流（ApprovalFlow）
# ════════════════════════════════════════════════════════════════════

@router.get('/approvals/pending')
@db_retry()
async def api_pending_approvals(current_user: dict = Depends(get_current_user)):
    """待我审批的流程列表。"""
    try:
        flows = get_pending_for_user(current_user)
        result = []
        for f in flows:
            d = f.to_dict()
            # 补充当前层级配置
            node_config = None
            for n in (f.approval_chain or []):
                if n.get("level") == f.current_level:
                    node_config = n
                    break
            d['current_node'] = node_config
            # 补充已审批节点
            nodes = db.session.query(ApprovalNode).filter_by(
                flow_id=f.flow_id
            ).order_by(ApprovalNode.level.asc()).all()
            d['history_nodes'] = [n.to_dict() for n in nodes]
            result.append(d)
        return {"success": True, "flows": result, "total": len(result)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/approvals/{flow_id}')
@db_retry()
async def api_get_approval_flow(flow_id: str, current_user: dict = Depends(get_current_user)):
    """审批流详情（含所有节点历史）。"""
    try:
        flow = db.session.query(ApprovalFlow).filter_by(flow_id=flow_id).first()
        if not flow:
            return JSONResponse(status_code=404, content={"success": False, "error": "审批流不存在"})
        if not _check_rbac(current_user, flow.department or ''):
            return JSONResponse(status_code=403, content={"success": False, "error": "无权访问"})
        nodes = db.session.query(ApprovalNode).filter_by(
            flow_id=flow_id
        ).order_by(ApprovalNode.level.asc()).all()
        d = flow.to_dict()
        d['nodes'] = [n.to_dict() for n in nodes]
        return {"success": True, "flow": d}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/approvals/{flow_id}/approve')
@db_retry()
async def api_approve_flow(flow_id: str, request: Request,
                           current_user: dict = Depends(get_current_user)):
    """审批通过（当前层级）。"""
    try:
        body = await request.json() if request.headers.get('content-type', '').startswith('application/json') else {}
        comment = body.get('comment', '')
        result = approve_flow(
            flow_id=flow_id,
            approver_id=current_user['id'],
            approver_name=current_user.get('username', '') or current_user.get('display_name', ''),
            approver_role=current_user.get('role', ''),
            comment=comment,
        )
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'approve_flow', 'approval', flow_id,
                      {'comment': comment, 'completed': result.get('completed', False)}, ip_address=ip)
        return {"success": True, **result}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/approvals/{flow_id}/reject')
@db_retry()
async def api_reject_flow(flow_id: str, request: Request,
                          current_user: dict = Depends(get_current_user)):
    """驳回审批（整个流程终止）。"""
    try:
        body = await request.json() if request.headers.get('content-type', '').startswith('application/json') else {}
        comment = body.get('comment', '')
        result = reject_flow(
            flow_id=flow_id,
            approver_id=current_user['id'],
            approver_name=current_user.get('username', '') or current_user.get('display_name', ''),
            approver_role=current_user.get('role', ''),
            comment=comment,
        )
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'reject_flow', 'approval', flow_id,
                      {'comment': comment}, ip_address=ip)
        return {"success": True, **result}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/approvals/{flow_id}/cancel')
@db_retry()
async def api_cancel_flow(flow_id: str, request: Request,
                          current_user: dict = Depends(get_current_user)):
    """撤销审批流（仅申请人或 admin）。"""
    try:
        body = await request.json() if request.headers.get('content-type', '').startswith('application/json') else {}
        reason = body.get('reason', '')
        result = cancel_flow(flow_id=flow_id, operator_id=current_user['id'], reason=reason)
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'cancel_flow', 'approval', flow_id,
                      {'reason': reason}, ip_address=ip)
        return {"success": True, **result}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/approvals')
@db_retry()
async def api_list_approvals(business_type: str = '', status: str = '',
                             limit: int = 50,
                             current_user: dict = Depends(get_current_user)):
    """审批流列表（可按业务类型/状态过滤）。"""
    try:
        q = db.session.query(ApprovalFlow)
        if business_type:
            q = q.filter_by(business_type=business_type)
        if status:
            q = q.filter_by(status=status)
        if current_user.get('role') != 'admin':
            dept = current_user.get('department', '') or ''
            q = q.filter(db.or_(
                ApprovalFlow.department == dept,
                ApprovalFlow.department == '',
            ))
        flows = q.order_by(ApprovalFlow.created_at.desc()).limit(min(limit, 200)).all()
        return {"success": True, "flows": [f.to_dict() for f in flows], "total": len(flows)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
