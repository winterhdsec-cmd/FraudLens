"""
Alert routes.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from database.crud import get_all_cases
from .deps import get_current_user, db_retry

router = APIRouter(prefix='/api/alerts', tags=['预警'])


@router.get('')
@db_retry()
async def api_get_alerts(current_user: dict = Depends(get_current_user)):
    try:
        from database.alert import alert_engine
        alerts = alert_engine.get_active_alerts()
        return {"success": True, "alerts": alerts, "total": len(alerts)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/{alert_id}/resolve')
async def api_resolve_alert(alert_id: int):
    try:
        from database.alert import alert_engine
        result = alert_engine.resolve_alert(alert_id)
        if result:
            return {"success": True, "message": "警报已解决"}
        return JSONResponse(status_code=404, content={"success": False, "error": "警报不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('/check')
async def api_check_alerts():
    try:
        from database.alert import alert_engine
        cases = get_all_cases()
        if not cases:
            return {"success": True, "alerts": []}
        latest = cases[0]
        alerts = alert_engine.check_new_case(latest)
        return {"success": True, "alerts": alerts}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})