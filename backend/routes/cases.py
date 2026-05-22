"""
Case CRUD routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from database.crud import (
    get_all_cases, get_case_by_id, get_case_stats,
    update_case_status, create_case, delete_case,
    update_case, search_cases_enhanced
)
from .deps import get_current_user, log_operation

router = APIRouter(prefix='/api/cases', tags=['案件'])


@router.get('')
async def api_get_cases():
    try:
        cases = get_all_cases()
        return {"success": True, "cases": cases, "total": len(cases)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/stats')
async def api_case_stats():
    try:
        stats = get_case_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/search')
async def api_search_cases(q: str = ''):
    try:
        if not q:
            return {"success": True, "cases": []}
        cases = search_cases_enhanced(q)
        return {"success": True, "cases": cases, "total": len(cases)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/{case_id}')
async def api_get_case(case_id: str):
    try:
        case = get_case_by_id(case_id)
        if case:
            return {"success": True, "case": case}
        return JSONResponse(status_code=404, content={"success": False, "error": "案件不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.put('/{case_id}')
async def api_update_case(case_id: str, request: Request,
                           current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        result = update_case(case_id, body)
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'update', 'case', case_id, ip_address=ip)
        return {"success": True, "case": result}
    except ValueError as e:
        return JSONResponse(status_code=404, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.put('/{case_id}/status')
async def api_update_case_status(case_id: str, request: Request,
                                  current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        new_status = body.get('status', '')
        if not new_status:
            raise HTTPException(status_code=400, detail="缺少状态参数")
        result = update_case_status(case_id, new_status)
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'update_status', 'case', case_id, {'new_status': new_status}, ip_address=ip)
        return {"success": True, "case": result}
    except HTTPException:
        raise
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post('')
async def api_create_case(request: Request,
                           current_user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
        case = create_case(body)
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'create', 'case', case['case_id'], ip_address=ip)
        return {"success": True, "case": case}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.delete('/{case_id}')
async def api_delete_case(case_id: str, request: Request,
                           current_user: dict = Depends(get_current_user)):
    try:
        delete_case(case_id)
        ip = request.client.host if request.client else ''
        log_operation(current_user['id'], current_user.get('username', ''),
                      'delete', 'case', case_id, ip_address=ip)
        return {"success": True, "message": "已删除"}
    except ValueError as e:
        return JSONResponse(status_code=404, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})