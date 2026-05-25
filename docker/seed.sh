#!/bin/bash
set -e

echo "============================================"
echo "  FraudLens Seed Data Injection"
echo "============================================"

BACKEND_URL="http://backend:5003"

echo "[1/3] Waiting for backend to be healthy..."
for i in $(seq 1 60); do
    if python -c "import urllib.request; urllib.request.urlopen('${BACKEND_URL}/health')" 2>/dev/null; then
        echo "  Backend is ready!"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "  [ERROR] Backend timeout after 120s"
        exit 1
    fi
    sleep 2
done

echo "[2/3] Logging in to get auth token..."
TOKEN=$(python -c "
import urllib.request, json, os
data = json.dumps({'username': 'admin', 'password': 'admin123'}).encode()
req = urllib.request.Request('${BACKEND_URL}/api/auth/login', data=data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
print(result.get('access_token', ''))
" 2>/dev/null)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "None" ]; then
    echo "  [ERROR] Failed to login"
    exit 1
fi
echo "  Login successful!"

echo "[3/3] Injecting seed data via API..."
python -c "
import urllib.request, json

token = '${TOKEN}'
url = '${BACKEND_URL}/api/seed'
req = urllib.request.Request(url, data=b'', headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
req.method = 'POST'
resp = urllib.request.urlopen(req, timeout=120)
result = json.loads(resp.read())
if result.get('success'):
    print('  Seed data injected successfully!')
else:
    print(f'  [WARN] Seed injection response: {result}')
" 2>/dev/null

echo ""
echo "============================================"
echo "  Seed data injection complete!"
echo "============================================"
