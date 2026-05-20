"""
Gang routes.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from database.crud import get_all_gangs, get_gang_by_id

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