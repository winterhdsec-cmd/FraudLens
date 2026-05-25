from datetime import datetime
from . import db
from .models import Case, AlertRecord
from .crud import _case_to_dict
from tools.redis_utils import alert_store_set, alert_store_get, alert_store_delete, alert_list_all, redis_available
from tools.response import logger

ALERT_THRESHOLD_CONFIDENCE = 0.6

# 内存 fallback（Redis 不可用时）
_memory_alerts = []
_memory_next_id = 1


def _compute_confidence(matched_count, total_new, total_existing):
    if matched_count == 0:
        return 0.0
    max_possible = min(len(total_new), len(total_existing)) if total_new and total_existing else 1
    if max_possible == 0:
        return 0.0
    return round(min(matched_count / max_possible, 1.0), 4)


class AlertEngine:
    def check_new_case(self, case_data):
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
            existing_phones = set(existing_entities.get('phone_numbers', []) or [])
            common_phones = phone_numbers & existing_phones
            if common_phones:
                confidence = _compute_confidence(len(common_phones), phone_numbers, existing_phones)
                if confidence >= ALERT_THRESHOLD_CONFIDENCE:
                    alert = self._save_alert('phone_match', case_id, existing['case_id'], list(common_phones), confidence)
                    alerts.append(alert)

            existing_banks = set(existing_entities.get('bank_accounts', []) or [])
            common_banks = bank_accounts & existing_banks
            if common_banks:
                confidence = _compute_confidence(len(common_banks), bank_accounts, existing_banks)
                if confidence >= ALERT_THRESHOLD_CONFIDENCE:
                    alert = self._save_alert('bank_match', case_id, existing['case_id'], list(common_banks), confidence)
                    alerts.append(alert)

            existing_ips = set(existing_entities.get('ips', []) or [])
            common_ips = ip_addresses & existing_ips
            if common_ips:
                confidence = _compute_confidence(len(common_ips), ip_addresses, existing_ips)
                if confidence >= ALERT_THRESHOLD_CONFIDENCE:
                    alert = self._save_alert('ip_match', case_id, existing['case_id'], list(common_ips), confidence)
                    alerts.append(alert)

            existing_apps = set(existing_entities.get('app_names', []) or [])
            common_apps = app_names & existing_apps
            if common_apps:
                confidence = _compute_confidence(len(common_apps), app_names, existing_apps)
                if confidence >= ALERT_THRESHOLD_CONFIDENCE:
                    alert = self._save_alert('app_match', case_id, existing['case_id'], list(common_apps), confidence)
                    alerts.append(alert)
        return alerts

    def _save_alert(self, alert_type, case_id, matched_case_id, matched_entities, confidence):
        record = AlertRecord(
            alert_type=alert_type,
            case_id=case_id,
            matched_case_id=matched_case_id,
            matched_entities=matched_entities,
            confidence=confidence
        )
        db.session.add(record)
        db.session.commit()
        result = record.to_dict()
        redis_ok = alert_store_set(record.id, result)
        logger.info(f"预警已生成: type={alert_type} id={record.id} case={case_id}->{matched_case_id} (redis={redis_ok})")
        return result

    def get_active_alerts(self):
        if redis_available():
            all_alerts = alert_list_all()
            return [a for a in all_alerts if not a.get('resolved')]
        try:
            records = AlertRecord.query.filter_by(resolved=False).order_by(AlertRecord.created_at.desc()).all()
            return [r.to_dict() for r in records]
        except Exception as e:
            logger.error(f"查询预警数据库失败: {e}")
            global _memory_alerts
            active = [a for a in _memory_alerts if not a.get('resolved')]
            return active

    def resolve_alert(self, alert_id):
        try:
            record = db.session.get(AlertRecord, alert_id)
            if record:
                record.resolved = True
                record.resolved_at = datetime.utcnow()
                db.session.commit()
                result = record.to_dict()
                alert_store_set(alert_id, result)
                return result
            return None
        except Exception as e:
            logger.error(f"解决预警失败 (id={alert_id}): {e}")
            global _memory_alerts
            for alert in _memory_alerts:
                if alert.get('id') == alert_id:
                    alert['resolved'] = True
                    alert['resolved_at'] = datetime.utcnow().isoformat()
                    return alert
            return None


alert_engine = AlertEngine()