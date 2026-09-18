from fastapi import FastAPI
from fastapi.testclient import TestClient
import routes.files as files_mod
from routes.deps import get_current_user

app = FastAPI()
app.include_router(files_mod.router)

def dummy_user():
    return {"username": "tester", "role": "admin", "id": 1}

app.dependency_overrides[get_current_user] = dummy_user

c = TestClient(app)

csv_bytes = (
    b"SENDER_ACCOUNT_ID,RECEIVER_ACCOUNT_ID,AMOUNT,TIMESTAMP\n"
    b"62280001,62170002,12000,2026-01-10 09:00\n"
    b"62170002,62280003,11000,2026-01-11 10:00\n"
)
r = c.post("/api/import-fund-flow", files={"file": ("flow.csv", csv_bytes, "text/csv")})
print("STATUS", r.status_code)
j = r.json()
print("SUCCESS", j.get("success"))
print("N_TX", len(j.get("accounts_tx", [])))
print("STATS", j.get("stats"))
print("NOTE", j.get("note"))

# 中文表头
csv_cn = b"\xbf\xee\xbf\xee\xd5\xcb\xba\xc5\xa2\xb3,\xca\xfd\xbf\xee\xd5\xcb\xba\xc5,\xbd\xf0\xea\xee,\xbd\xbb\xd2\xb5\xca\xb1\xbc\xe4\n".decode("gbk").encode("utf-8") if False else "付款账号,收款账号,金额,交易时间\naaa111,bbb222,5000,2026-02-01\n".encode("utf-8")
r2 = c.post("/api/import-fund-flow", files={"file": ("cn.csv", csv_cn, "text/csv")})
print("CN_STATUS", r2.status_code, "N_TX", len(r2.json().get("accounts_tx", [])))
