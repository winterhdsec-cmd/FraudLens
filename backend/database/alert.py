from datetime import datetime
from . import db
from .models import Case
from .crud import _case_to_dict

_alerts = []
_next_id = 1

ALERT_THRESHOLD_CONFIDENCE = 0.6


def _compute_confidence(matched_count, total_new, total_existing):
    if matched_count == 0:
        return 0.0
    max_possible = min(len(total_new), len(total_existing)) if total_new and total_existing else 1
    if max_possible == 0:
        return 0.0
    return round(min(matched_count / max_possible, 1.0), 4)


class Alert:
    def __init__(self, alert_id, alert_type, case_id, matched_case_id,
                 matched_entities, confidence, created_at=None):
        self.id = alert_id
        self.alert_type = alert_type
        self.case_id = case_id
        self.matched_case_id = matched_case_id
        self.matched_entities = matched_entities
        self.confidence = confidence
        self.created_at = created_at or datetime.utcnow()
        self.resolved = False
        self.resolved_at = None

    def to_dict(self):
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'case_id': self.case_id,
            'matched_case_id': self.matched_case_id,
            'matched_entities': self.matched_entities,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class AlertEngine:
    def check_new_case(self, case_data):
        global _next_id, _alerts
        alerts = []

        entities = case_data.get('extracted_entities', {})
        if not entities:
            return alerts

        case_id = case_data.get('case_id', '')
        phone_numbers = set(entities.get('phone_numbers', []) or [])
        bank_accounts = set(entities.get('bank_accounts', []) or [])
        ip_addresses = set(entities.get('ip_addresses', []) or [])
        app_names = set(entities.get('app_names', []) or [])

        all_cases = Case.query.order_by(Case.case_id).all()
        existing_dicts = [_case_to_dict(c) for c in all_cases]

        for existing in existing_dicts:
            if existing.get('case_id') == case_id:
                continue

            existing_entities = existing.get('extracted_entities', {})
            if not existing_entities:
                continue

            match_info = []

            existing_phones = set(existing_entities.get('phone_numbers', []) or [])
            common_phones = phone_numbers & existing_phones
            if common_phones:
                confidence = _compute_confidence(
                    len(common_phones), phone_numbers, existing_phones
                )
                if confidence >= ALERT_THRESHOLD_CONFIDENCE:
                    alert = Alert(
                        alert_id=_next_id,
                        alert_type='phone_match',
                        case_id=case_id,
                        matched_case_id=existing['case_id'],
                        matched_entities=list(common_phones),
                        confidence=confidence
                    )
                    _alerts.append(alert)
                    alerts.append(alert.to_dict())
                    _next_id += 1
                    match_info.append(('phone_match', common_phones, confidence))

            existing_banks = set(existing_entities.get('bank_accounts', []) or [])
            common_banks = bank_accounts & existing_banks
            if common_banks:
                confidence = _compute_confidence(
                    len(common_banks), bank_accounts, existing_banks
                )
                if confidence >= ALERT_THRESHOLD_CONFIDENCE:
                    alert = Alert(
                        alert_id=_next_id,
                        alert_type='bank_match',
                        case_id=case_id,
                        matched_case_id=existing['case_id'],
                        matched_entities=list(common_banks),
                        confidence=confidence
                    )
                    _alerts.append(alert)
                    alerts.append(alert.to_dict())
                    _next_id += 1
                    match_info.append(('bank_match', common_banks, confidence))

            existing_ips = set(existing_entities.get('ips', []) or [])
            common_ips = ip_addresses & existing_ips
            if common_ips:
                confidence = _compute_confidence(
                    len(common_ips), ip_addresses, existing_ips
                )
                if confidence >= ALERT_THRESHOLD_CONFIDENCE:
                    alert = Alert(
                        alert_id=_next_id,
                        alert_type='ip_match',
                        case_id=case_id,
                        matched_case_id=existing['case_id'],
                        matched_entities=list(common_ips),
                        confidence=confidence
                    )
                    _alerts.append(alert)
                    alerts.append(alert.to_dict())
                    _next_id += 1
                    match_info.append(('ip_match', common_ips, confidence))

            existing_apps = set(existing_entities.get('app_names', []) or [])
            common_apps = app_names & existing_apps
            if common_apps:
                confidence = _compute_confidence(
                    len(common_apps), app_names, existing_apps
                )
                if confidence >= ALERT_THRESHOLD_CONFIDENCE:
                    alert = Alert(
                        alert_id=_next_id,
                        alert_type='app_match',
                        case_id=case_id,
                        matched_case_id=existing['case_id'],
                        matched_entities=list(common_apps),
                        confidence=confidence
                    )
                    _alerts.append(alert)
                    alerts.append(alert.to_dict())
                    _next_id += 1
                    match_info.append(('app_match', common_apps, confidence))

        return alerts

    def get_active_alerts(self):
        active = [a for a in _alerts if not a.resolved]
        return [a.to_dict() for a in active]

    def resolve_alert(self, alert_id):
        for alert in _alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                return alert.to_dict()
        return None


alert_engine = AlertEngine()