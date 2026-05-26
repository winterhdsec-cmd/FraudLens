"""
Session routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from database.crud import get_sessions, get_session_detail, delete_session
from .deps import get_current_user, log_operation, db_retry

router = APIRouter(prefix='/api/sessions', tags=['会话'])


@router.get('')
@db_retry()
async def api_get_sessions(current_user: dict = Depends(get_current_user)):
    try:
        sessions = get_sessions()
        return {"success": True, "sessions": sessions}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/{session_id}')
@db_retry()
async def api_get_session_detail_route(session_id: str, current_user: dict = Depends(get_current_user)):
    try:
        detail = get_session_detail(session_id)
        if detail:
            return {"success": True, **detail}
        return JSONResponse(status_code=404, content={"success": False, "error": "会话不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.delete('/{session_id}')
@db_retry()
async def api_delete_session_route(session_id: str, request: Request,
                                    current_user: dict = Depends(get_current_user)):
    try:
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'delete_session', 'session', session_id, ip_address=ip)
        delete_session(session_id)
        return {"success": True, "message": "删除成功"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})