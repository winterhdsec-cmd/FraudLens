"""
Merge routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from database.crud import get_all_cases
from .deps import get_current_user, log_operation, db_retry
from schemas.merge import MergeConfirmRequest

router = APIRouter(prefix='/api/merges', tags=['合并'])


@router.post('/suggest')
@db_retry()
async def api_suggest_merges(current_user: dict = Depends(get_current_user)):
    try:
        from database.merge import suggest_merges
        cases = get_all_cases()
        suggestions = suggest_merges(cases)
        return {
            "success": True,
            "suggestions": [{
                'id': s.id, 'case_id_a': s.case_id_a,
                'case_id_b': s.case_id_b, 'similarity': s.similarity,
                'reason': s.reason
            } for s in suggestions],
            "total": len(suggestions)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/confirm')
@db_retry()
async def api_confirm_merge(data: MergeConfirmRequest, request: Request,
                             current_user: dict = Depends(get_current_user)):
    try:
        from database.merge import confirm_merge
        confirm_merge(data.case_id_a, data.case_id_b, data.gang_id, current_user['id'])
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'confirm_merge', 'merge', f"{data.case_id_a}+{data.case_id_b}", ip_address=ip)
        return {"success": True, "message": "合并成功"}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/pending')
@db_retry()
async def api_pending_merges(current_user: dict = Depends(get_current_user)):
    try:
        from database.merge import get_pending_merges
        suggestions = get_pending_merges()
        return {"success": True, "suggestions": suggestions}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('')
@db_retry()
async def api_list_merges(status: str = Query('pending', description='pending/approved/rejected/all'),
                          limit: int = Query(200, ge=1, le=500),
                          offset: int = Query(0, ge=0),
                          current_user: dict = Depends(get_current_user)):
    """并案建议列表（带两侧案件信息与复核元数据），供办案工作台并案建议面板使用。"""
    try:
        from database.merge import get_merges, get_merge_status_summary
        items, total = get_merges(status=status, limit=limit, offset=offset)
        return {
            "success": True,
            "suggestions": items,
            "total": total,
            "summary": get_merge_status_summary()
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/{suggestion_id}/reject')
@db_retry()
async def api_reject_merge(suggestion_id: int, request: Request,
                           payload: dict = None,
                           current_user: dict = Depends(get_current_user)):
    """驳回一条并案建议：仅标记状态，不建立团伙关联。"""
    try:
        from database.merge import reject_merge
        reason = ''
        if isinstance(payload, dict):
            reason = str(payload.get('reason') or '')[:100]
        result = reject_merge(suggestion_id, current_user['id'], reason)
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'reject_merge', 'merge', str(suggestion_id), ip_address=ip)
        return {"success": True, "message": "已驳回并案建议", "data": result}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})