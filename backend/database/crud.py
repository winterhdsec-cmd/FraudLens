import numpy as np
import json
from datetime import datetime
from . import db
from .models import (
    AnalysisSession, Case, Gang, GangCaseRelation,
    Person, Account, Phone, EvidenceItem
)
from tools.db import transactional


def create_session(session_id, raw_input=None):
    with transactional():
        session = AnalysisSession(
            session_id=session_id,
            status='running',
            raw_input=raw_input
        )
        db.session.add(session)
        return session


def complete_session(session_id, status='completed', processing_info=None):
    with transactional():
        session = AnalysisSession.query.filter_by(session_id=session_id).first()
        if session:
            session.status = status
            session.completed_at = datetime.utcnow()
            if processing_info:
                session.processing_info = processing_info
        return session


def save_case(case_data, session_id=None):
    with transactional():
        existing = Case.query.filter_by(case_id=case_data['case_id']).first()
        if existing:
            return existing

        amount_str = case_data.get('amount', '0')
        amount_value = 0.0
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
        if match:
            num = float(match.group(1))
            if '万' in amount_str:
                num *= 10000
            amount_value = num

        embedding_bytes = None
        if 'embedding' in case_data and case_data['embedding'] is not None:
            embedding_bytes = case_data['embedding'].tobytes() if isinstance(case_data['embedding'], np.ndarray) else case_data['embedding']

        roles_data = []
        for r in case_data.get('roles', []):
            if hasattr(r, 'dict'):
                roles_data.append(r.dict())
            elif isinstance(r, dict):
                roles_data.append(r)
            else:
                roles_data.append(str(r))

        case = Case(
            case_id=str(case_data['case_id']),
            session_id=session_id,
            title=case_data.get('title', f"案件{case_data['case_id']}"),
            scam_type=case_data.get('scam_type', ''),
            scam_subtype=case_data.get('scam_subtype', ''),
            risk_level=case_data.get('risk_level', 'LOW'),
            risk_label=case_data.get('risk_label', '低风险'),
            risk_type=case_data.get('risk_type', 'info'),
            risk_score=case_data.get('risk_score', 0),
            victim_name=case_data.get('victim', ''),
            amount=amount_str,
            amount_value=amount_value,
            description=case_data.get('description', case_data.get('ai_report', '')[:500]),
            status='已分析',
            source=case_data.get('source', '文本'),
            ai_report=case_data.get('ai_report', ''),
            keywords=case_data.get('keywords', []),
            steps=case_data.get('steps', []),
            roles=roles_data,
            extracted_entities=case_data.get('extracted_entities', {}),
            message_count=case_data.get('message_count', 0),
            time_range=case_data.get('time_range', ''),
            warning=case_data.get('warning', None),
            is_error=case_data.get('is_error', False),
            embedding=embedding_bytes
        )
        db.session.add(case)

        entities = case_data.get('extracted_entities', {})
        if entities.get('phone_numbers'):
            person = Person(
                case_id=case['case_id'],
                name=case_data.get('victim', ''),
                role='victim',
                phone=', '.join(entities['phone_numbers'][:3])
            )
            db.session.add(person)

        return case


def _safe_json(value):
    if isinstance(value, str):
        try: return json.loads(value)
        except: return []
    return value or []

def _safe_text(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value or ''

def _parse_json(value, default=None):
    if isinstance(value, str):
        try: return json.loads(value)
        except: return default or value
    return value if value else (default or value)

def save_gang(gang_data, session_id=None):
    with transactional():
        existing = Gang.query.filter_by(gang_id=gang_data['gang_id']).first()
        if existing:
            return existing

        amount_str = gang_data.get('total_amount_involved', '0')
        amount_value = 0.0
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
        if match:
            num = float(match.group(1))
            if '万' in amount_str:
                num *= 10000
            amount_value = num

        centroid_bytes = None
        if 'centroid' in gang_data and gang_data['centroid'] is not None:
            centroid_bytes = gang_data['centroid'].tobytes() if isinstance(gang_data['centroid'], np.ndarray) else gang_data['centroid']

        gang = Gang(
            gang_id=gang_data['gang_id'],
            session_id=session_id,
            gang_name=gang_data.get('gang_name', ''),
            risk_level=gang_data.get('risk_level', 'C'),
            risk_label=gang_data.get('risk_label', '低风险'),
            risk_type=gang_data.get('risk_type', 'info'),
            threat_level=gang_data.get('threat_level', gang_data.get('risk_level', 'C')),
            comprehensive_score=gang_data.get('comprehensive_score', gang_data.get('risk_score', 0)),
            confidence=gang_data.get('confidence', 0),
            member_count_estimate=gang_data.get('member_count_estimate', ''),
            tech_level=gang_data.get('tech_level', '中'),
            script_type=gang_data.get('script_type', ''),
            total_cases=int(gang_data.get('total_cases', 0)),
            total_amount=amount_str,
            total_amount_value=amount_value,
            description=gang_data.get('description', ''),
            fingerprint=gang_data.get('fingerprint', []),
            enhanced_fingerprint=gang_data.get('enhanced_fingerprint', []),
            steps=gang_data.get('steps', []),
            radar_data=gang_data.get('radar_data', {}),
            deep_characteristics=gang_data.get('deep_characteristics', []),
            risk_assessment=gang_data.get('risk_assessment', {}),
            modus_operandi=gang_data.get('modus_operandi', ''),
            prevention_advice=_safe_text(gang_data.get('prevention_advice', '')),
            network_nodes=_safe_json(gang_data.get('network_nodes', [])),
            centroid=centroid_bytes,
            created_at=datetime.utcnow()
        )
        db.session.add(gang)

        for case_ref in gang_data.get('related_cases', []):
            relation = GangCaseRelation(
                gang_id=gang_data['gang_id'],
                case_id=str(case_ref.get('case_id', '')),
                similarity=case_ref.get('similarity', 0.0)
            )
            db.session.add(relation)

        return gang


def get_all_cases():
    cases = Case.query.order_by(Case.created_at.desc()).all()
    return [_case_to_dict(c) for c in cases]


def get_case_by_id(case_id):
    case = Case.query.filter_by(case_id=case_id).first()
    return _case_to_dict(case) if case else None


def get_all_gangs():
    gangs = Gang.query.order_by(Gang.created_at.desc()).all()
    return [_gang_to_dict(g) for g in gangs]


def get_gang_by_id(gang_id):
    gang = Gang.query.filter_by(gang_id=gang_id).first()
    return _gang_to_dict(gang) if gang else None


def get_sessions():
    sessions = AnalysisSession.query.order_by(AnalysisSession.created_at.desc()).limit(20).all()
    return [{
        'session_id': s.session_id,
        'status': s.status,
        'total_cases': s.total_cases,
        'total_gangs': s.total_gangs,
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'completed_at': s.completed_at.isoformat() if s.completed_at else None
    } for s in sessions]


def get_session_detail(session_id):
    session = AnalysisSession.query.filter_by(session_id=session_id).first()
    if not session:
        return None
    cases = Case.query.filter_by(session_id=session_id).all()
    gangs = Gang.query.filter_by(session_id=session_id).all()
    return {
        'session': {
            'session_id': session.session_id,
            'status': session.status,
            'total_cases': session.total_cases,
            'total_gangs': session.total_gangs,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'completed_at': session.completed_at.isoformat() if session.completed_at else None,
            'processing_info': session.processing_info
        },
        'cases': [_case_to_dict(c) for c in cases],
        'gangs': [_gang_to_dict(g) for g in gangs]
    }


def search_cases(query):
    cases = Case.query.filter(
        db.or_(
            Case.case_id.ilike(f'%{query}%'),
            Case.victim_name.ilike(f'%{query}%'),
            Case.scam_type.ilike(f'%{query}%'),
            Case.amount.ilike(f'%{query}%'),
            Case.title.ilike(f'%{query}%'),
            Case.description.ilike(f'%{query}%'),
            Case.keywords.ilike(f'%{query}%')
        )
    ).order_by(Case.created_at.desc()).all()
    return [_case_to_dict(c) for c in cases]


def delete_session(session_id):
    GangCaseRelation.query.filter(
        GangCaseRelation.gang_id.in_(
            db.session.query(Gang.gang_id).filter(Gang.session_id == session_id)
        )
    ).delete(synchronize_session=False)
    Gang.query.filter_by(session_id=session_id).delete()
    Case.query.filter_by(session_id=session_id).delete()
    AnalysisSession.query.filter_by(session_id=session_id).delete()
    db.session.commit()


def _case_to_dict(c):
    if not c:
        return None
    created_str = c.created_at.isoformat() if c.created_at else None
    date_str = c.created_at.isoformat()[:10] if c.created_at else None
    return {
        'case_id': c.case_id,
        'id': c.case_id,
        'number': c.number or 0,
        'title': c.title,
        'scam_type': c.scam_type,
        'type': c.scam_type,
        'scam_subtype': c.scam_subtype,
        'risk_level': c.risk_level,
        'risk_label': c.risk_label,
        'risk_type': c.risk_type,
        'risk_score': c.risk_score,
        'victim': c.victim_name,
        'victimName': c.victim_name,
        'victim_name': c.victim_name,
        'victim_gender': c.victim_gender,
        'victim_age': c.victim_age,
        'victim_phone': c.victim_phone,
        'victimPhone': c.victim_phone,
        'victim_job': c.victim_job,
        'victimJob': c.victim_job,
        'victim_address': c.victim_address,
        'victimAddress': c.victim_address,
        'amount': c.amount,
        'amount_value': c.amount_value,
        'description': c.description,
        'status': c.status,
        'source': c.source,
        'ai_report': c.ai_report,
        'keywords': c.keywords if c.keywords else [],
        'steps': c.steps if c.steps else [],
        'roles': c.roles if c.roles else [],
        'extracted_entities': c.extracted_entities if c.extracted_entities else {},
        'message_count': c.message_count,
        'time_range': c.time_range,
        'warning': c.warning,
        'is_error': c.is_error,
        'date': date_str,
        'created_at': created_str
    }


def _gang_to_dict(g):
    if not g:
        return None
    related_cases = GangCaseRelation.query.filter_by(gang_id=g.gang_id).all()
    case_details = []
    for rel in related_cases:
        case = Case.query.filter_by(case_id=rel.case_id).first()
        if case:
            case_details.append({
                'case_id': case.case_id,
                'victim': case.victim_name,
                'amount': case.amount,
                'snippet': (case.ai_report or '')[:60] + '...' if case.ai_report else '',
                'risk_level': case.risk_level
            })

    return {
        'gang_id': g.gang_id,
        'id': g.gang_id,
        'number': g.number or 0,
        'gang_name': g.gang_name,
        'name': g.gang_name,
        'risk_level': g.risk_level,
        'riskLevel': g.risk_level,
        'risk_label': g.risk_label,
        'riskLabel': g.risk_label,
        'risk_type': g.risk_type,
        'threat_level': g.threat_level,
        'comprehensive_score': g.comprehensive_score,
        'confidence': g.confidence,
        'member_count_estimate': g.member_count_estimate,
        'tech_level': g.tech_level,
        'script_type': g.script_type,
        'total_cases': g.total_cases,
        'cases': g.total_cases,
        'total_amount_involved': g.total_amount,
        'total_amount': g.total_amount,
        'amount': g.total_amount,
        'total_amount_value': g.total_amount_value,
        'description': g.description,
        'fingerprint': g.fingerprint if g.fingerprint else [],
        'enhanced_fingerprint': g.enhanced_fingerprint if g.enhanced_fingerprint else [],
        'steps': g.steps if g.steps else [],
        'radar_data': g.radar_data if g.radar_data else {},
        'deep_characteristics': _parse_json(g.deep_characteristics, []),
        'risk_assessment': _parse_json(g.risk_assessment, {}),
        'modus_operandi': g.modus_operandi or '',
        'prevention_advice': g.prevention_advice,
        'network_nodes': _parse_json(g.network_nodes, []),
        'related_cases': case_details,
        'created_at': g.created_at.isoformat() if g.created_at else None
    }


VALID_STATUS_TRANSITIONS = {
    '待分析': ['已分析'],
    '已分析': ['已立案'],
    '已立案': ['侦办中'],
    '侦办中': ['已结案'],
    '已结案': [],
}


def update_case(case_id, data):
    with transactional():
        case = Case.query.filter_by(case_id=case_id).first()
        if not case:
            raise ValueError(f'Case {case_id} not found')

        allowed_fields = {
            'title', 'victim_name', 'victim_gender', 'victim_age',
            'victim_phone', 'victim_address', 'victim_job',
            'scam_type', 'amount', 'description', 'status',
            'risk_level', 'risk_label'
        }
        for key, value in data.items():
            if key in allowed_fields and value is not None:
                setattr(case, key, value)

        if 'amount' in data:
            import re
            amount_str = data['amount']
            match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
            if match:
                num = float(match.group(1))
                if '万' in amount_str:
                    num *= 10000
                case.amount_value = num

        return _case_to_dict(case)


def update_case_status(case_id, new_status):
    with transactional():
        case = Case.query.filter_by(case_id=case_id).first()
        if not case:
            raise ValueError(f'Case {case_id} not found')

        current = case.status or '待分析'
        allowed = VALID_STATUS_TRANSITIONS.get(current, [])

        if current == new_status:
            return _case_to_dict(case)

        if new_status not in allowed:
            raise ValueError(
                f'Invalid status transition: {current} -> {new_status}. '
                f'Allowed targets: {allowed}'
            )

        case.status = new_status
        return _case_to_dict(case)


def get_case_stats():
    total = Case.query.count()
    status_counts = dict(
        db.session.query(Case.status, db.func.count(Case.id))
        .group_by(Case.status)
        .all()
    )

    total_amount = db.session.query(db.func.sum(Case.amount_value)).scalar() or 0.0

    risk_distribution = dict(
        db.session.query(Case.risk_level, db.func.count(Case.id))
        .group_by(Case.risk_level)
        .all()
    )

    scam_type_stats = dict(
        db.session.query(Case.scam_type, db.func.count(Case.id))
        .filter(Case.scam_type != '')
        .group_by(Case.scam_type)
        .order_by(db.func.count(Case.id).desc())
        .limit(10)
        .all()
    )

    recent_cases = Case.query.order_by(Case.created_at.desc()).limit(5).all()
    recent = [_case_to_dict(c) for c in recent_cases]

    return {
        'total_cases': total,
        'status_distribution': status_counts,
        'total_amount_value': round(total_amount, 2),
        'risk_distribution': risk_distribution,
        'top_scam_types': scam_type_stats,
        'recent_cases': recent,
    }


def generate_case_number():
    today = datetime.now().strftime('%Y%m%d')
    prefix = f'ALT{today}'
    latest = Case.query.filter(Case.case_id.like(f'{prefix}%')).order_by(Case.case_id.desc()).first()
    if latest:
        seq = int(latest.case_id[-3:]) + 1
    else:
        seq = 1
    return f'{prefix}{seq:03d}'


def create_case(data):
    with transactional():
        case_id = generate_case_number()

        amount_str = data.get('amount', '0')
        amount_value = 0.0
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
        if match:
            num = float(match.group(1))
            if '万' in amount_str:
                num *= 10000
            amount_value = num

        scam_type = data.get('scam_type', '')
        victim_name = data.get('victim_name', '')

        case = Case(
            case_id=case_id,
            title=data.get('title', ''),
            victim_name=victim_name,
            victim_gender=data.get('victim_gender', ''),
            victim_age=data.get('victim_age', ''),
            victim_phone=data.get('victim_phone', ''),
            victim_address=data.get('victim_address', ''),
            victim_job=data.get('victim_job', ''),
            scam_type=scam_type,
            amount=amount_str,
            amount_value=amount_value,
            description=data.get('description', ''),
            status='待分析',
            source='手动录入'
        )
        db.session.add(case)
        db.session.flush()

        try:
            from .p1_models import CapitalFlow, DispatchOrder, AlertRecord
            import random

            source_accounts = ['6222****1234', '6217****5678', '6228****9012']
            target_accounts = ['6214****3456', '6221****7890', '6230****2345']
            banks = ['工商银行', '建设银行', '农业银行', '中国银行', '招商银行']
            annotations = ['境内转账', '第三方支付', '境内转账']

            num_flows = random.randint(3, 5)
            for i in range(num_flows):
                flow = CapitalFlow(
                    case_id=case_id,
                    source_account=random.choice(source_accounts),
                    target_account=random.choice(target_accounts),
                    bank_name=random.choice(banks),
                    amount=round(random.uniform(amount_value * 0.1, amount_value * 0.5), 2) if amount_value > 0 else round(random.uniform(1000, 50000), 2),
                    direction='out' if i % 3 != 0 else 'in',
                    level=random.randint(1, 3),
                    annotation=random.choice(annotations)
                )
                db.session.add(flow)

            dispatch = DispatchOrder(
                case_id=case_id,
                title=f'预警派单-{scam_type or "未知类型"}',
                content=f'系统预警{scam_type or "未知"}案件，涉案金额{amount_str}，请及时处置',
                status='pending',
                priority='中',
                district=data.get('victim_address', '')[:15] if victim_name else '',
                assignee='系统自动派单'
            )
            db.session.add(dispatch)

            alert = AlertRecord(
                alert_type='case_match',
                case_id=case_id,
                matched_case_id=case_id,
                title=f'新案件预警-{scam_type or "未知类型"}',
                content=f'新录入{scam_type or "未知"}案件，涉案金额{amount_str}，受害人{victim_name}',
                status='未处理',
                confidence=0.85,
                matched_entities=[victim_name] if victim_name else []
            )
            db.session.add(alert)

        except ImportError:
            pass

        return _case_to_dict(case)


def delete_case(case_id):
    with transactional():
        case = Case.query.filter_by(case_id=case_id).first()
        if not case:
            raise ValueError(f'Case {case_id} not found')
        case.status = '已删除'
        return True


def search_cases_enhanced(query):
    if not query:
        return []
    cases = Case.query.filter(
        db.or_(
            Case.case_id.ilike(f'{query}%'),
            Case.title.ilike(f'%{query}%'),
            Case.victim_name.ilike(f'%{query}%'),
            Case.scam_type.ilike(f'%{query}%')
        )
    ).order_by(Case.created_at.desc()).all()
    return [_case_to_dict(c) for c in cases]