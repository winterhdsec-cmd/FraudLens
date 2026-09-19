"""重点人员碰撞比对验证（KeyPersonsView 宣传的「研判时自动碰撞比对」）。

为什么单独测：`/api/persons/collision` 与 `/api/analyze/check-persons` 是
「重点人员库」页面的核心卖点，但此前**零测试覆盖**；而它极易因一个条件写错
就静默失效（例如 `is_active` 过滤方向反了会让全部比对都命中不了，
返回 `matched: False` 而不是报错，肉眼完全看不出问题）。

覆盖：
  C1  启用人员：完整手机号精确碰撞命中，match_fields 含 phone
  C2  启用人员：手机号后 6 位模糊碰撞同样命中
  C3  启用人员：按银行卡号碰撞命中，match_fields 含 bank_account
  C4  **已停用人员（is_active=False）必须被排除** —— 反向断言，防过滤写反
  C5  完全无关的号码不命中（防"永远返回 True"的假阳性）
  C6  空参数不报错、返回未命中
  C7  批量比对：命中数/检查数正确，且只返回命中的那些人
  C8  批量比对传入空数组不报错
  C9  未认证访问被拒
"""
import os
import sys

os.environ.setdefault("JWT_SECRET_KEY", "verify-script-only-not-a-real-secret")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))
load_dotenv(os.path.join(_ROOT, "backend", "key.env"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from database import db  # noqa: E402
from database.p1_models import KeyPerson  # noqa: E402
from routes.deps import get_current_user  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


FAKE_USER = {"id": 1, "username": "verify_admin", "role": "admin"}

db.init_app()
main.app.dependency_overrides[get_current_user] = lambda: FAKE_USER
client = TestClient(main.app)

print("=" * 72)
print("重点人员碰撞比对验证")
print("=" * 72)

try:
    active = db.session.query(KeyPerson).filter(KeyPerson.is_active == True).first()   # noqa: E712
    inactive = db.session.query(KeyPerson).filter(KeyPerson.is_active == False).first()  # noqa: E712
    n_active = db.session.query(KeyPerson).filter(KeyPerson.is_active == True).count()   # noqa: E712
    n_inactive = db.session.query(KeyPerson).filter(KeyPerson.is_active == False).count()  # noqa: E712
    print(f"\n样本：启用 {n_active} 条 / 停用 {n_inactive} 条")

    if not active:
        check("存在启用人员可供测试", False, "库中没有 is_active=1 的记录，无法验证")
    else:
        print(f"  选用：{active.name} / {active.phone} / {active.bank_account}")

        print("\n[C1] 完整手机号精确碰撞")
        r = client.get("/api/persons/collision", params={"phone": active.phone})
        j = r.json()
        check("HTTP 200", r.status_code == 200, f"status={r.status_code}")
        check("命中", j.get("matched") is True, f"matched={j.get('matched')}")
        check("total=1", j.get("total") == 1, f"total={j.get('total')}")
        fields = [f for m in j.get("matches", []) for f in (m.get("match_fields") or [])]
        check("match_fields 含 phone", "phone" in fields, str(fields))
        check("返回命中人姓名", bool(j.get("matches") and j["matches"][0].get("name")),
              str(j.get("matches", [{}])[0].get("name")))

        print("\n[C2] 手机号后 6 位模糊碰撞")
        r2 = client.get("/api/persons/collision", params={"phone": active.phone[-6:]})
        check("模糊匹配命中", r2.json().get("matched") is True,
              f"matched={r2.json().get('matched')}")

        print("\n[C3] 按银行卡号碰撞")
        r3 = client.get("/api/persons/collision", params={"account": active.bank_account})
        j3 = r3.json()
        check("命中", j3.get("matched") is True, f"matched={j3.get('matched')}")
        f3 = [f for m in j3.get("matches", []) for f in (m.get("match_fields") or [])]
        check("match_fields 含 bank_account", "bank_account" in f3, str(f3))

    print("\n[C4] 已停用人员必须被排除（反向断言）")
    if inactive:
        r4 = client.get("/api/persons/collision", params={"phone": inactive.phone})
        check("停用人员不命中", r4.json().get("matched") is False,
              f"matched={r4.json().get('matched')}（若为 True 说明 is_active 过滤写反）")
    else:
        check("存在停用人员可供反向测试", False, "库中没有 is_active=0 的记录")

    print("\n[C5] 无关号码不命中（防假阳性）")
    r5 = client.get("/api/persons/collision", params={"phone": "10000000000"})
    check("不命中", r5.json().get("matched") is False, f"matched={r5.json().get('matched')}")

    print("\n[C6] 空参数")
    r6 = client.get("/api/persons/collision")
    check("HTTP 200 且不命中", r6.status_code == 200 and r6.json().get("matched") is False,
          f"status={r6.status_code} matched={r6.json().get('matched')}")

    print("\n[C7] 批量比对 /api/analyze/check-persons")
    if active:
        r7 = client.post("/api/analyze/check-persons", json={"persons": [
            {"name": "甲", "phone": active.phone},
            {"name": "乙", "phone": "19900000000"},
        ]})
        j7 = r7.json()
        check("HTTP 200", r7.status_code == 200, f"status={r7.status_code}")
        check("has_match=True", j7.get("has_match") is True, f"has_match={j7.get('has_match')}")
        check("total_checked=2", j7.get("total_checked") == 2, f"{j7.get('total_checked')}")
        check("total_matched=1", j7.get("total_matched") == 1, f"{j7.get('total_matched')}")
        check("只返回命中的那条", len(j7.get("results", [])) == 1)
        check("结果带回输入人信息",
              bool(j7.get("results") and j7["results"][0].get("input_person", {}).get("name") == "甲"))

    print("\n[C8] 批量比对传空数组")
    r8 = client.post("/api/analyze/check-persons", json={"persons": []})
    check("HTTP 200 且未命中", r8.status_code == 200 and r8.json().get("has_match") is False,
          f"status={r8.status_code}")

    print("\n[C9] 鉴权")
    main.app.dependency_overrides.pop(get_current_user, None)
    anon = TestClient(main.app)
    ra = anon.get("/api/persons/collision", params={"phone": "13800000000"})
    check("未带 token 被拒（401/403）", ra.status_code in (401, 403), f"status={ra.status_code}")

finally:
    main.app.dependency_overrides.pop(get_current_user, None)

print("\n" + "=" * 72)
print(f"结果：{len(PASS)} 通过 / {len(FAIL)} 失败")
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("全部通过 ✓")
sys.exit(0)
