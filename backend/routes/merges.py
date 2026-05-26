"""
Merge routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from database.crud import get_all_cases
from .deps import get_current_user, log_operation, MergeConfirmRequest, db_retry

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