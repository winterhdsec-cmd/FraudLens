import requests, json, sys

BASE = 'http://localhost:5000'
passed = 0
failed = 0

def check(name, ok, detail=''):
    global passed, failed
    if ok: passed += 1
    else: failed += 1
    icon = 'PASS' if ok else 'FAIL'
    print(f'  [{icon}] {name}')
    if detail: print(f'     {detail}')

print('='*60)
print('FastAPI 全流程测试')
print('='*60)

# 1. Health
try:
    r = requests.get(BASE + '/health', timeout=5)
    check('Health check', r.json().get('status') == 'healthy')
except Exception as e:
    check('Health check', False, str(e))

# 2. Login
try:
    r = requests.post(BASE + '/api/auth/login',
                      json={'username': 'admin', 'password': 'admin123'})
    data = r.json()
    check('Admin login', data['success'])
    TOKEN = data['access_token']
except Exception as e:
    check('Admin login', False, str(e))
    sys.exit(1)

HEADERS = {'Authorization': 'Bearer ' + TOKEN}

# 3. Analysis
try:
    messages = ['你好京东客服', '我贷款异常怎么办', '请转账到安全账户', '好的我转5万']
    r = requests.post(BASE + '/agent-analyze',
                      json={'messages': messages}, timeout=120)
    data = r.json()
    ok = data.get('success', False)
    cases = data.get('raw_cases', [])
    gangs = data.get('gangs', [])
    info = data.get('processing_info', {})
    detail = 'cases=%d gangs=%d time=%sms' % (len(cases), len(gangs), info.get('processing_time_ms', 'N/A'))
    check('Analysis API', ok, detail)
except Exception as e:
    check('Analysis API', False, str(e))
    cases = []
    gangs = []

# 4. DB cases
try:
    r = requests.get(BASE + '/api/cases', headers=HEADERS)
    db_cases = r.json().get('cases', [])
    check('DB cases', len(db_cases) > 0, 'count=%d' % len(db_cases))
except Exception as e:
    check('DB cases', False, str(e))

# 5. DB gangs
try:
    r = requests.get(BASE + '/api/gangs', headers=HEADERS)
    db_gangs = r.json().get('gangs', [])
    check('DB gangs', len(db_gangs) > 0, 'count=%d' % len(db_gangs))
except Exception as e:
    check('DB gangs', False, str(e))

# 6. Dashboard
try:
    r = requests.get(BASE + '/api/dashboard', headers=HEADERS)
    dash = r.json().get('data', {})
    check('Dashboard', bool(dash),
          'cases=%d gangs=%d' % (dash.get('total_cases', 0), dash.get('total_gangs', 0)))
except Exception as e:
    check('Dashboard', False, str(e))

# 7. Case status transition
try:
    if cases:
        cid = cases[0]['case_id']
        r = requests.put(BASE + '/api/cases/%s/status' % cid,
                         json={'status': '已立案'}, headers=HEADERS)
        check('Status transition', r.json().get('success', False))
except Exception as e:
    check('Status transition', False, str(e))

# 8. Report generation
try:
    if cases:
        cid = cases[0]['case_id']
        r = requests.get(BASE + '/api/reports/case/%s?format=pdf' % cid)
        check('PDF report', r.json().get('success', False))
except Exception as e:
    check('PDF report', False, str(e))

# Summary
total = passed + failed
print()
print('='*60)
pct = passed/total*100 if total > 0 else 0
print('Results: %d/%d passed (%.0f%%)' % (passed, total, pct))
print('='*60)
sys.exit(0 if failed == 0 else 1)