import urllib.request as u, urllib.error
PX = "http://localhost:5003"
for _ in range(5):
    try:
        u.urlopen(u.Request(PX + "/api/cases", headers={"Authorization": "Bearer x"}))
    except urllib.error.HTTPError:
        pass
t = u.urlopen(PX + "/api/metrics/prometheus", timeout=5).read().decode()
rec = [l for l in t.splitlines() if l.startswith("http_requests_total") and not l.startswith("#")]
print("RECORDED http_requests_total lines:", len(rec))
for l in rec[:3]:
    print("  ", l)
codes = {}; first = None
for i in range(1, 71):
    try:
        r = u.urlopen(u.Request(PX + "/api/cases", headers={"Authorization": "Bearer x"}))
        c = r.status
    except urllib.error.HTTPError as e:
        c = e.code
    codes[c] = codes.get(c, 0) + 1
    if c == 429 and first is None:
        first = i
print("G6 codes:", codes, "| first 429 @", first)
r = u.urlopen(PX + "/ready", timeout=5)
h = dict(r.headers)
for k in ("X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy", "X-XSS-Protection"):
    print("G5", k, "->", h.get(k.lower()) or h.get(k))
