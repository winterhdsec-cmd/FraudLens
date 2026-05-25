"""
Gang routes.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from database import db
from database.models import Gang
from database.crud import get_all_gangs, get_gang_by_id
from routes.cases import _compute_gang_radar

router = APIRouter(prefix='/api/gangs', tags=['团伙'])


@router.get('')
async def api_get_gangs():
    try:
        gangs = get_all_gangs()
        return {"success": True, "gangs": gangs, "total": len(gangs)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/{gang_id}')
async def api_get_gang(gang_id: str):
    try:
        gang = get_gang_by_id(gang_id)
        if gang:
            return {"success": True, "gang": gang}
        return JSONResponse(status_code=404, content={"success": False, "error": "团伙不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/{gang_id}/radar')
async def api_get_gang_radar(gang_id: str):
    try:
        gang = db.session.query(Gang).filter(Gang.gang_id == gang_id).first()
        if not gang:
            return JSONResponse(status_code=404, content={"success": False, "error": "团伙不存在"})
        radar = _compute_gang_radar(gang)
        return {"success": True, "gang_id": gang_id, "radar": radar}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})