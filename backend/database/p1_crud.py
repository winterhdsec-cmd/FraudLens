from datetime import datetime
from . import db
from database.p1_models import CapitalFlow, DispatchOrder, KeyPerson
from sqlalchemy import or_
from tools.db import transactional


# ========== Capital Flow ==========

def save_capital_flow(data):
    with transactional():
        flow = CapitalFlow(
            case_id=data.get('case_id', ''),
            source_account=data.get('source_account', ''),
            target_account=data.get('target_account', ''),
            bank_name=data.get('bank_name', ''),
            amount=float(data.get('amount', 0)),
            transaction_time=data.get('transaction_time'),
            direction=data.get('direction', 'out'),
            level=int(data.get('level', 1)),
            annotation=data.get('annotation', '')
        )
        db.session.add(flow)
        return flow.to_dict()


def get_capital_flows(case_id=None):
    try:
        query = CapitalFlow.query.order_by(CapitalFlow.transaction_time.desc())
        if case_id:
            query = query.filter_by(case_id=case_id)
        flows = query.all()
        return [f.to_dict() for f in flows]
    except Exception as e:
        raise e


def get_capital_flow_graph(case_id):
    try:
        flows = CapitalFlow.query.filter_by(case_id=case_id).order_by(CapitalFlow.transaction_time).all()

        nodes_map = {}
        edges = []

        for f in flows:
            if f.source_account and f.source_account not in nodes_map:
                nodes_map[f.source_account] = {
                    'id': f.source_account,
                    'name': f.source_account,
                    'bank': f.bank_name,
                    'type': 'account',
                    'direction': 'out'
                }
            if f.target_account and f.target_account not in nodes_map:
                nodes_map[f.target_account] = {
                    'id': f.target_account,
                    'name': f.target_account,
                    'bank': f.bank_name,
                    'type': 'account',
                    'direction': 'in'
                }
            edges.append({
                'source': f.source_account,
                'target': f.target_account,
                'amount': f.amount,
                'time': f.transaction_time.isoformat() if f.transaction_time else None,
                'level': f.level,
                'annotation': f.annotation
            })

        return {
            'nodes': list(nodes_map.values()),
            'edges': edges,
            'total_amount': sum(f.amount for f in flows)
        }
    except Exception as e:
        raise e


# ========== Dispatch ==========

def create_dispatch(data):
    with transactional():
        dispatch = DispatchOrder(
            alert_id=data.get('alert_id', ''),
            case_id=data.get('case_id', ''),
            assigned_dept=data.get('assigned_dept', ''),
            assigned_officer=data.get('assigned_officer', ''),
            status='pending',
            dispatch_time=data.get('dispatch_time', datetime.utcnow()),
            deadline=data.get('deadline'),
            created_by=data.get('created_by')
        )
        db.session.add(dispatch)
        return dispatch.to_dict()


def sign_dispatch(dispatch_id):
    with transactional():
        dispatch = db.session.get(DispatchOrder, dispatch_id)
        if not dispatch:
            raise ValueError('派单不存在')
        if dispatch.status != 'pending':
            raise ValueError(f'当前状态({dispatch.status})不允许签收')
        dispatch.status = 'signed'
        dispatch.sign_time = datetime.utcnow()
        return dispatch.to_dict()


def complete_dispatch(dispatch_id, feedback):
    with transactional():
        dispatch = db.session.get(DispatchOrder, dispatch_id)
        if not dispatch:
            raise ValueError('派单不存在')
        if dispatch.status != 'signed':
            raise ValueError(f'当前状态({dispatch.status})不允许完成')
        dispatch.status = 'completed'
        dispatch.feedback = feedback
        return dispatch.to_dict()


def get_dispatch_orders(status=None):
    try:
        query = DispatchOrder.query.order_by(DispatchOrder.created_at.desc())
        if status:
            query = query.filter_by(status=status)
        orders = query.all()
        return [o.to_dict() for o in orders]
    except Exception as e:
        raise e


def get_dispatch_by_id(dispatch_id):
    try:
        dispatch = db.session.get(DispatchOrder, dispatch_id)
        return dispatch.to_dict() if dispatch else None
    except Exception as e:
        raise e


# ========== Key Person ==========

def save_key_person(data):
    with transactional():
        id_number = data.get('id_number', '')
        if not id_number:
            raise ValueError('身份证号不能为空')

        existing = KeyPerson.query.filter_by(id_number=id_number).first()
        if existing:
            existing.name = data.get('name', existing.name)
            existing.gender = data.get('gender', existing.gender)
            existing.age = data.get('age', existing.age)
            existing.phone = data.get('phone', existing.phone)
            existing.bank_account = data.get('bank_account', existing.bank_account)
            existing.address = data.get('address', existing.address)
            existing.risk_level = data.get('risk_level', existing.risk_level)
            existing.risk_label = data.get('risk_label', existing.risk_label)
            existing.person_type = data.get('person_type', existing.person_type)
            existing.tags = data.get('tags', existing.tags)
            existing.case_ids = data.get('case_ids', existing.case_ids)
            existing.source = data.get('source', existing.source)
            existing.notes = data.get('notes', existing.notes)
            existing.is_active = data.get('is_active', existing.is_active)
            return existing.to_dict()

        person = KeyPerson(
            name=data.get('name', ''),
            id_number=id_number,
            gender=data.get('gender', ''),
            age=data.get('age', ''),
            phone=data.get('phone', ''),
            bank_account=data.get('bank_account', ''),
            address=data.get('address', ''),
            risk_level=data.get('risk_level', 'B'),
            risk_label=data.get('risk_label', '中风险'),
            person_type=data.get('person_type', '前科人员'),
            tags=data.get('tags', []),
            case_ids=data.get('case_ids', []),
            source=data.get('source', ''),
            notes=data.get('notes', ''),
            is_active=True
        )
        db.session.add(person)
        return person.to_dict()


def get_key_persons(search=None, risk_level=None, person_type=None):
    try:
        query = KeyPerson.query.filter_by(is_active=True)
        if search:
            query = query.filter(
                or_(
                    KeyPerson.name.ilike(f'%{search}%'),
                    KeyPerson.id_number.ilike(f'%{search}%'),
                    KeyPerson.phone.ilike(f'%{search}%')
                )
            )
        if risk_level:
            query = query.filter_by(risk_level=risk_level)
        if person_type:
            query = query.filter_by(person_type=person_type)
        persons = query.order_by(KeyPerson.updated_at.desc()).all()
        return [p.to_dict() for p in persons]
    except Exception as e:
        raise e


def get_key_person_by_id(person_id):
    try:
        person = db.session.get(KeyPerson, person_id)
        return person.to_dict() if person else None
    except Exception as e:
        raise e


def search_key_persons_by_phone_or_account(query_str):
    try:
        persons = KeyPerson.query.filter(
            KeyPerson.is_active == True,
            or_(
                KeyPerson.phone.ilike(f'%{query_str}%'),
                KeyPerson.bank_account.ilike(f'%{query_str}%')
            )
        ).all()
        return [p.to_dict() for p in persons]
    except Exception as e:
        raise e


def delete_key_person(person_id):
    with transactional():
        person = db.session.get(KeyPerson, person_id)
        if not person:
            raise ValueError('重点人员不存在')
        person.is_active = False
        return {'success': True, 'message': '已移除'}


def collision_check(phone=None, account=None, id_number=None):
    try:
        results = []
        conditions = []
        if phone:
            conditions.append(KeyPerson.phone.ilike(f'%{phone}%'))
        if account:
            conditions.append(KeyPerson.bank_account.ilike(f'%{account}%'))
        if id_number:
            conditions.append(KeyPerson.id_number == id_number)

        if not conditions:
            return {'matched': False, 'matches': []}

        persons = KeyPerson.query.filter(
            KeyPerson.is_active == True,
            or_(*conditions)
        ).all()

        for p in persons:
            match_fields = []
            if phone and p.phone and phone in p.phone:
                match_fields.append('phone')
            if account and p.bank_account and account in p.bank_account:
                match_fields.append('bank_account')
            if id_number and p.id_number and p.id_number == id_number:
                match_fields.append('id_number')

            results.append({
                **p.to_dict(),
                'match_fields': match_fields
            })

        return {
            'matched': len(results) > 0,
            'matches': results,
            'total': len(results)
        }
    except Exception as e:
        raise e