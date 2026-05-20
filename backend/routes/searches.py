"""
Search routes.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from database.crud import search_cases, _case_to_dict

router = APIRouter(prefix='/api/search', tags=['搜索'])


@router.get('')
async def api_search(q: str = Query('', alias='q')):
    try:
        if not q:
            return {"success": True, "cases": []}
        cases = search_cases(q)
        return {"success": True, "cases": cases, "total": len(cases)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get('/advanced')
async def api_advanced_search(type: str = Query('', alias='type'),
                               value: str = Query('', alias='value')):
    try:
        if not type or not value:
            raise HTTPException(status_code=400, detail="请指定搜索类型和关键词")
        from database.models import Case
        cases = Case.query.order_by(Case.created_at.desc()).all()
        results = []
        for c in cases:
            entities = c.extracted_entities or {}
            if type == 'phone' and value in str(entities.get('phone_numbers', [])):
                results.append(c)
            elif type == 'bank' and value in str(entities.get('bank_accounts', [])):
                results.append(c)
            elif type == 'ip' and value in str(entities.get('ips', entities.get('ip_addresses', []))):
                results.append(c)
            elif type == 'app' and value in str(entities.get('app_names', [])):
                results.append(c)
        return {"success": True, "cases": [_case_to_dict(c) for c in results], "total": len(results)}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})