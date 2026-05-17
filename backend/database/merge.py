from datetime import datetime
from . import db
from .models import MergeSuggestion, Case, Gang, GangCaseRelation


ENTITY_FIELDS = ['phone_numbers', 'bank_accounts', 'ips', 'app_names']


def _extract_entity_set(case):
    entities = case.get('extracted_entities', {})
    if not entities:
        return set()
    result = set()
    for field in ENTITY_FIELDS:
        values = entities.get(field, [])
        if isinstance(values, list):
            for v in values:
                result.add(f'{field}:{v}')
    return result


def _compute_similarity(case_a, case_b):
    set_a = _extract_entity_set(case_a)
    set_b = _extract_entity_set(case_b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return round(len(intersection) / len(union), 4)


def _build_reason(case_a, case_b):
    entities_a = case_a.get('extracted_entities', {})
    entities_b = case_b.get('extracted_entities', {})
    overlaps = []
    for field in ENTITY_FIELDS:
        vals_a = set(entities_a.get(field, []) or [])
        vals_b = set(entities_b.get(field, []) or [])
        common = vals_a & vals_b
        if common:
            overlaps.append(f'{field}: {", ".join(str(v) for v in list(common)[:3])}')
    if overlaps:
        return '重叠实体: ' + '; '.join(overlaps)
    return '实体相似度匹配'


def suggest_merges(cases):
    if not cases or len(cases) < 2:
        return []

    suggestions = []
    skip_pairs = set()

    existing = MergeSuggestion.query.filter(
        MergeSuggestion.status.in_(['pending', 'approved'])
    ).all()
    for e in existing:
        skip_pairs.add((e.case_id_a, e.case_id_b))
        skip_pairs.add((e.case_id_b, e.case_id_a))

    for i in range(len(cases)):
        for j in range(i + 1, len(cases)):
            case_a = cases[i]
            case_b = cases[j]
            id_a = case_a.get('case_id', case_a.case_id if not isinstance(case_a, dict) else '')
            id_b = case_b.get('case_id', case_b.case_id if not isinstance(case_b, dict) else '')

            if not id_a or not id_b:
                continue
            if (id_a, id_b) in skip_pairs or (id_b, id_a) in skip_pairs:
                continue

            similarity = _compute_similarity(case_a, case_b)
            if similarity >= 0.1:
                reason = _build_reason(case_a, case_b)
                suggestion = MergeSuggestion(
                    case_id_a=id_a,
                    case_id_b=id_b,
                    similarity=similarity,
                    reason=reason,
                    status='pending'
                )
                db.session.add(suggestion)
                suggestions.append(suggestion)

    db.session.commit()
    return suggestions


def confirm_merge(case_id_a, case_id_b, gang_id, user_id):
    suggestion = MergeSuggestion.query.filter(
        ((MergeSuggestion.case_id_a == case_id_a) & (MergeSuggestion.case_id_b == case_id_b)) |
        ((MergeSuggestion.case_id_a == case_id_b) & (MergeSuggestion.case_id_b == case_id_a))
    ).filter(MergeSuggestion.status == 'pending').first()

    if not suggestion:
        raise ValueError('No pending merge suggestion found for this pair')

    gang = Gang.query.filter_by(gang_id=gang_id).first()
    if not gang:
        raise ValueError(f'Gang {gang_id} not found')

    for cid in [case_id_a, case_id_b]:
        existing = GangCaseRelation.query.filter_by(
            gang_id=gang_id, case_id=cid
        ).first()
        if not existing:
            relation = GangCaseRelation(
                gang_id=gang_id,
                case_id=cid,
                similarity=suggestion.similarity
            )
            db.session.add(relation)

    suggestion.status = 'approved'
    suggestion.reviewed_by = user_id
    suggestion.reviewed_at = datetime.utcnow()

    db.session.commit()
    return {'gang_id': gang_id, 'case_ids': [case_id_a, case_id_b]}


def get_pending_merges():
    suggestions = MergeSuggestion.query.filter_by(status='pending').order_by(
        MergeSuggestion.similarity.desc()
    ).all()
    result = []
    for s in suggestions:
        case_a = Case.query.filter_by(case_id=s.case_id_a).first()
        case_b = Case.query.filter_by(case_id=s.case_id_b).first()
        result.append({
            'id': s.id,
            'case_id_a': s.case_id_a,
            'case_id_b': s.case_id_b,
            'similarity': s.similarity,
            'reason': s.reason,
            'status': s.status,
            'case_a_title': case_a.title if case_a else '',
            'case_b_title': case_b.title if case_b else '',
            'case_a_victim': case_a.victim_name if case_a else '',
            'case_b_victim': case_b.victim_name if case_b else '',
            'created_at': s.created_at.isoformat() if s.created_at else None
        })
    return result