"""
Review routes: pending reviews, mark as reviewed.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from database import db
from database.models import Case, AnalysisSession
from database.crud import get_all_cases
from .deps import get_current_user, log_operation, db_retry

router = APIRouter(prefix='/api/reviews', tags=['复核'])


@router.get('/pending')
@db_retry()
async def api_pending_reviews(current_user: dict = Depends(get_current_user)):
    try:
        cases = get_all_cases()
        flagged_cases = []
        reviewed_ids = set()
        for c in cases:
            if not c:
                continue
            status = c.get('status', '')
            warning = c.get('warning', '') or ''
            is_error = c.get('is_error', False)
            has_radar = bool(c.get('radar_data'))

            if status == '已复核':
                reviewed_ids.add(c.get('case_id', ''))
                continue

            analyzed = status not in ('', '待分析', '已删除')

            if not analyzed:
                continue

            flagged_cases.append({
                'case_id': c.get('case_id', ''),
                'title': c.get('title', ''),
                'victim': c.get('victim', ''),
                'scam_type': c.get('scam_type', ''),
                'amount': c.get('amount', ''),
                'status': status,
                'warning': warning,
                'is_error': is_error,
                'has_radar': has_radar,
                'source': c.get('source', ''),
                'risk_label': c.get('risk_label', ''),
                'risk_type': c.get('risk_type', ''),
                'created_at': c.get('created_at', '')
            })

        flagged_cases.sort(key=lambda x: (
            -int(x['is_error']),
            -int(bool(x['warning']))
        ))

        sessions = AnalysisSession.query.order_by(
            AnalysisSession.created_at.desc()
        ).limit(20).all()
        flagged_sessions = []
        for s in sessions:
            pinfo = s.processing_info or {}
            warnings_list = pinfo.get('warnings', []) if isinstance(pinfo, dict) else []
            review_warnings = [w for w in warnings_list if '人工复核' in str(w) or '置信度' in str(w)]
            if review_warnings:
                flagged_sessions.append({
                    'session_id': s.session_id,
                    'status': s.status,
                    'total_cases': s.total_cases,
                    'total_gangs': s.total_gangs,
                    'warnings': review_warnings,
                    'created_at': s.created_at.isoformat() if s.created_at else None
                })

        return {
            "success": True,
            "pending_cases": flagged_cases,
            "pending_sessions": flagged_sessions,
            "total_pending_cases": len(flagged_cases),
            "total_pending_sessions": len(flagged_sessions)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.put('/{case_id}')
@db_retry()
async def api_review_case(case_id: str, request: Request,
                           current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        case = Case.query.filter_by(case_id=case_id).first()
        if not case:
            return JSONResponse(status_code=404, content={"success": False, "error": "案件不存在"})

        new_status = body.get('status', '已复核')
        notes = body.get('notes', '')
        case.status = new_status
        if notes:
            case.description = (case.description or '') + f'\n[复核备注] {notes}'
        db.session.commit()

        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'review_case', 'case', case_id,
                      {'status': new_status, 'notes': notes}, ip_address=ip)

        return {"success": True, "message": "复核完成", "case_id": case_id, "status": new_status}
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
