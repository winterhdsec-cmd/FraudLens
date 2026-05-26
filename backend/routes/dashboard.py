"""
Dashboard routes.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from database.crud import get_sessions, get_session_detail
from .deps import get_current_user, db_retry

router = APIRouter(prefix='/api/dashboard', tags=['看板'])


@router.get('')
@db_retry()
async def api_dashboard(current_user: dict = Depends(get_current_user)):
    try:
        from database.dashboard import get_dashboard_data
        data = get_dashboard_data()
        return {"success": True, "data": data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/trend')
async def api_dashboard_trend():
    try:
        from database.dashboard import get_dashboard_data
        data = get_dashboard_data()
        return {"success": True, "trend": data['trend_data']}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/latest-session')
async def api_latest_session():
    try:
        sessions = get_sessions()
        if sessions:
            sid = sessions[0]['session_id']
            detail = get_session_detail(sid)
            if detail:
                return {"success": True, **detail}
        return {"success": True, "session": None, "cases": [], "gangs": []}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})