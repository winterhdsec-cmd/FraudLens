from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database.p1_crud import (
    save_capital_flow, get_capital_flows, get_capital_flow_graph,
    create_dispatch, sign_dispatch, complete_dispatch,
    get_dispatch_orders, get_dispatch_by_id,
    save_key_person, get_key_persons, get_key_person_by_id,
    search_key_persons_by_phone_or_account, delete_key_person,
    collision_check
)

router = APIRouter()


# ========== Pydantic Schemas ==========

class CapitalFlowCreate(BaseModel):
    case_id: str
    source_account: str = ''
    target_account: str = ''
    bank_name: str = ''
    amount: float = 0.0
    transaction_time: Optional[datetime] = None
    direction: str = 'out'
    level: int = 1
    annotation: str = ''


class DispatchCreate(BaseModel):
    alert_id: str = ''
    case_id: str
    assigned_dept: str = ''
    assigned_officer: str = ''
    deadline: Optional[datetime] = None
    created_by: Optional[int] = None


class DispatchComplete(BaseModel):
    feedback: str


class KeyPersonCreate(BaseModel):
    name: str = ''
    id_number: str
    gender: str = ''
    age: str = ''
    phone: str = ''
    bank_account: str = ''
    address: str = ''
    risk_level: str = 'B'
    risk_label: str = '中风险'
    person_type: str = '前科人员'
    tags: list = []
    case_ids: list = []
    source: str = ''
    notes: str = ''


class CheckPersonsItem(BaseModel):
    name: str = ''
    phone: str = ''
    bank_account: str = ''
    id_number: str = ''


class CheckPersonsRequest(BaseModel):
    persons: list[CheckPersonsItem]


# ========== Capital Flow Routes ==========

@router.post('/api/capital/flows')
async def api_create_capital_flow(data: CapitalFlowCreate):
    try:
        result = save_capital_flow(data.dict())
        return {'success': True, 'flow': result}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/capital/flows')
async def api_list_capital_flows(case_id: Optional[str] = Query(None)):
    try:
        flows = get_capital_flows(case_id)
        return {'success': True, 'flows': flows, 'total': len(flows)}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/capital/graph/{case_id}')
async def api_capital_flow_graph(case_id: str):
    try:
        graph = get_capital_flow_graph(case_id)
        return {'success': True, 'graph': graph}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


# ========== Dispatch Routes ==========

@router.post('/api/dispatch/create')
async def api_create_dispatch(data: DispatchCreate):
    try:
        result = create_dispatch(data.dict())
        return {'success': True, 'dispatch': result}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.put('/api/dispatch/{dispatch_id}/sign')
async def api_sign_dispatch(dispatch_id: int):
    try:
        result = sign_dispatch(dispatch_id)
        return {'success': True, 'dispatch': result}
    except ValueError as e:
        return JSONResponse(status_code=400, content={'success': False, 'error': str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.put('/api/dispatch/{dispatch_id}/complete')
async def api_complete_dispatch(dispatch_id: int, data: DispatchComplete):
    try:
        result = complete_dispatch(dispatch_id, data.feedback)
        return {'success': True, 'dispatch': result}
    except ValueError as e:
        return JSONResponse(status_code=400, content={'success': False, 'error': str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/dispatch/list')
async def api_list_dispatch(status: Optional[str] = Query(None)):
    try:
        orders = get_dispatch_orders(status)
        return {'success': True, 'orders': orders, 'total': len(orders)}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/dispatch/{dispatch_id}')
async def api_get_dispatch(dispatch_id: int):
    try:
        order = get_dispatch_by_id(dispatch_id)
        if order:
            return {'success': True, 'dispatch': order}
        return JSONResponse(status_code=404, content={'success': False, 'error': '派单不存在'})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


# ========== Key Person Routes ==========

@router.post('/api/persons/key')
async def api_create_key_person(data: KeyPersonCreate):
    try:
        result = save_key_person(data.dict())
        return {'success': True, 'person': result}
    except ValueError as e:
        return JSONResponse(status_code=400, content={'success': False, 'error': str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/persons/key')
async def api_list_key_persons(
    search: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    person_type: Optional[str] = Query(None)
):
    try:
        persons = get_key_persons(search, risk_level, person_type)
        return {'success': True, 'persons': persons, 'total': len(persons)}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/persons/key/{person_id}')
async def api_get_key_person(person_id: int):
    try:
        person = get_key_person_by_id(person_id)
        if person:
            return {'success': True, 'person': person}
        return JSONResponse(status_code=404, content={'success': False, 'error': '重点人员不存在'})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.delete('/api/persons/key/{person_id}')
async def api_delete_key_person(person_id: int):
    try:
        result = delete_key_person(person_id)
        return {'success': True, **result}
    except ValueError as e:
        return JSONResponse(status_code=404, content={'success': False, 'error': str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@router.get('/api/persons/collision')
async def api_collision_check(
    phone: Optional[str] = Query(None),
    account: Optional[str] = Query(None),
    id_number: Optional[str] = Query(None)
):
    try:
        result = collision_check(phone, account, id_number)
        return {'success': True, **result}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


# ========== Intrusion Detection during analysis ==========

@router.post('/api/analyze/check-persons')
async def api_check_extracted_persons(data: CheckPersonsRequest):
    try:
        all_matches = []
        for person in data.persons:
            p = person.dict()
            result = collision_check(
                phone=p.get('phone'),
                account=p.get('bank_account'),
                id_number=p.get('id_number')
            )
            if result['matched']:
                all_matches.append({
                    'input_person': p,
                    'matches': result['matches']
                })

        return {
            'success': True,
            'has_match': len(all_matches) > 0,
            'results': all_matches,
            'total_checked': len(data.persons),
            'total_matched': len(all_matches)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})