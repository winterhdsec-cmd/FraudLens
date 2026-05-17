import re
import csv
from datetime import datetime
from . import db
from .models import Case
from .crud import save_case


def parse_amount(amount_str):
    if not amount_str:
        return 0.0
    amount_str = str(amount_str).strip().replace(',', '').replace('，', '')
    amount_str = amount_str.replace('元', '').replace('¥', '').replace('￥', '').strip()

    match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
    if not match:
        return 0.0

    num = float(match.group(1))
    if '万' in amount_str:
        num *= 10000
    elif '千' in amount_str:
        num *= 1000
    elif '亿' in amount_str:
        num *= 100000000

    return num


def _generate_case_id():
    year = datetime.utcnow().strftime('%Y')
    prefix = f'FC-{year}-'

    latest = Case.query.filter(
        Case.case_id.like(f'{prefix}%')
    ).order_by(Case.case_id.desc()).first()

    if latest:
        last_num = int(latest.case_id.split('-')[-1])
        new_num = last_num + 1
    else:
        new_num = 1

    return f'{prefix}{new_num:05d}'


def _build_case_dict(row):
    content = str(row.get('content', row.get('text', '')))
    victim = str(row.get('victim', row.get('victim_name', '')))
    amount_raw = str(row.get('amount', ''))
    scam_type = str(row.get('scam_type', row.get('type', '')))
    description = str(row.get('description', row.get('desc', '')))
    phone = str(row.get('phone', row.get('phone_number', '')))
    bank_account = str(row.get('bank_account', row.get('account', '')))

    amount_value = parse_amount(amount_raw)

    extracted_entities = {}
    if phone:
        phones = [p.strip() for p in phone.replace('，', ',').split(',') if p.strip()]
        if phones:
            extracted_entities['phone_numbers'] = phones
    if bank_account:
        accounts = [a.strip() for a in bank_account.replace('，', ',').split(',') if a.strip()]
        if accounts:
            extracted_entities['bank_accounts'] = accounts

    return {
        'case_id': _generate_case_id(),
        'title': f'{scam_type or "导入"}案件' if not victim else f'{victim}-{scam_type or "导入"}案件',
        'victim': victim,
        'amount': amount_raw,
        'amount_value': amount_value,
        'scam_type': scam_type,
        'description': description or content[:500],
        'source': '导入',
        'status': '待分析',
        'extracted_entities': extracted_entities,
        'content': content
    }


def import_from_csv(filepath):
    errors = []
    imported = 0
    total_amount = 0.0

    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    case_dict = _build_case_dict(row)
                    save_case(case_dict)
                    imported += 1
                    total_amount += case_dict['amount_value']
                except Exception as e:
                    errors.append({'row': row_num, 'error': str(e)})
    except Exception as e:
        errors.append({'row': 0, 'error': f'文件读取失败: {str(e)}'})

    return {
        'total_imported': imported,
        'errors': errors,
        'total_amount': round(total_amount, 2)
    }


def import_from_excel(filepath):
    try:
        import openpyxl
    except ImportError:
        return {
            'total_imported': 0,
            'errors': [{'row': 0, 'error': 'openpyxl 未安装，请执行 pip install openpyxl'}],
            'total_amount': 0.0
        }

    errors = []
    imported = 0
    total_amount = 0.0

    try:
        wb = openpyxl.load_workbook(filepath, read_only=True)
        ws = wb.active

        rows_iter = ws.iter_rows(values_only=True)
        header = [str(c).lower().strip() if c else '' for c in next(rows_iter, [])]

        for row_num, row in enumerate(rows_iter, start=2):
            try:
                row_dict = {}
                for idx, value in enumerate(row):
                    if idx < len(header):
                        row_dict[header[idx]] = str(value) if value is not None else ''

                case_dict = _build_case_dict(row_dict)
                save_case(case_dict)
                imported += 1
                total_amount += case_dict['amount_value']
            except Exception as e:
                errors.append({'row': row_num, 'error': str(e)})

        wb.close()
    except Exception as e:
        errors.append({'row': 0, 'error': f'文件读取失败: {str(e)}'})

    return {
        'total_imported': imported,
        'errors': errors,
        'total_amount': round(total_amount, 2)
    }