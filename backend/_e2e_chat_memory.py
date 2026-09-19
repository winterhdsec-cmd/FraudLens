"""G3 会话记忆持久化 - 路由层 E2E 验证（ASGI 直连，无需启动端口）

覆盖真实 HTTP 路径：
  GET    /api/chat/sessions                    （列表）
  GET    /api/chat/sessions/{id}/history       （取历史）
  DELETE /api/chat/sessions/{id}               （清空）
并验证「模拟重启」：清空模块级会话池后仍能从 Redis 取回历史。
"""
import os
import sys
import uuid
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent
_ROOT = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))
os.environ.setdefault("JWT_SECRET_KEY", "e2e-script-only-secret")

# 必须先加载 .env：ensure_embedded_redis() 只在 REDIS_AUTOSTART=1 时才会拉起
# 内置 Redis。若不加载，脚本会退化为"依赖环境里碰巧有 Redis"，测试结果不可信。
from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env")
load_dotenv(_BACKEND / "key.env")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from routes.chat import router as chat_router  # noqa: E402
from routes.deps import get_current_user  # noqa: E402
from memory.short_term import ShortTermMemory  # noqa: E402
from core.redis_embedded import wait_for_redis  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' — ' + extra) if extra else ''}")


def main():
    print("=" * 68)
    print("G3 会话记忆持久化 · 路由层 E2E")
    print("=" * 68)

    # 自举并**等待**内置 Redis 就绪：本脚本自建 FastAPI app、不导入 main，
    # 因此不会自动拉起 Redis；不补这一步就会因环境里有没有 Redis 而时通时败。
    wait_for_redis()

    app = FastAPI()
    app.include_router(chat_router)

    # 绕过鉴权（本测试只验证会话持久化，不验证 RBAC）
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 1, "username": "e2e_tester", "role": "admin"
    }
    client = TestClient(app)

    sid = f"e2e_{uuid.uuid4().hex[:10]}"

    # --- 1. 预置历史（模拟用户之前聊过） ---
    print("\n[1] 预置会话历史到 Redis")
    seed = ShortTermMemory(session_id=sid)
    seed.add_message("user", "帮我查一下最近的冒充公检法案件")
    seed.add_message("assistant", "已找到 12 起相关案件，其中高风险 3 起。")
    check("预置 2 条", len(seed.get_messages()) == 2)

    # --- 2. GET history 能读到 ---
    print("\n[2] GET /api/chat/sessions/{id}/history")
    r = client.get(f"/api/chat/sessions/{sid}/history")
    check("HTTP 200", r.status_code == 200, f"实际 {r.status_code}")
    body = r.json()
    check("返回 2 条", body.get("count") == 2, f"实际 {body.get('count')}")
    check("session_id 正确", body.get("session_id") == sid)
    check("首条为 user 提问",
          body["messages"][0]["content"].startswith("帮我查一下"),
          body["messages"][0]["content"][:20])
    check("消息带 role/content/timestamp",
          all(k in body["messages"][0] for k in ("role", "content", "timestamp")))

    # --- 3. GET /sessions 列表 ---
    print("\n[3] GET /api/chat/sessions（服务端会话列表）")
    r2 = client.get("/api/chat/sessions")
    check("HTTP 200", r2.status_code == 200, f"实际 {r2.status_code}")
    lst = r2.json().get("sessions", [])
    mine = next((s for s in lst if s["id"] == sid), None)
    check("列表中能找到该会话", mine is not None)
    check("标题取自首条 user 消息",
          bool(mine and mine["title"].startswith("帮我查一下")),
          str(mine))
    check("消息数为 2", bool(mine and mine["messageCount"] == 2), str(mine))

    # --- 4. 模拟服务重启：清空会话池，历史仍可取回 ---
    print("\n[4] 模拟服务重启（清空 Agent 会话池）")
    import routes.chat as chat_mod
    with chat_mod._chat_agents_lock:
        chat_mod._chat_agents.clear()
    check("会话池已清空", len(chat_mod._chat_agents) == 0)

    r3 = client.get(f"/api/chat/sessions/{sid}/history")
    check("重启后仍能取回历史", r3.status_code == 200 and r3.json()["count"] == 2,
          f"status={r3.status_code} count={r3.json().get('count') if r3.status_code == 200 else 'N/A'}")

    # --- 5. 另一会话不互相污染 ---
    print("\n[5] 会话隔离")
    sid_other = f"e2e_{uuid.uuid4().hex[:10]}"
    other = ShortTermMemory(session_id=sid_other)
    other.add_message("user", "完全不同的会话")
    r4 = client.get(f"/api/chat/sessions/{sid}/history")
    check("原会话仍为 2 条（未被污染）", r4.json()["count"] == 2, f"实际 {r4.json()['count']}")
    r5 = client.get(f"/api/chat/sessions/{sid_other}/history")
    check("新会话为 1 条", r5.json()["count"] == 1, f"实际 {r5.json()['count']}")

    # --- 6. DELETE 清空 ---
    print("\n[6] DELETE /api/chat/sessions/{id}")
    r6 = client.delete(f"/api/chat/sessions/{sid}")
    check("HTTP 200", r6.status_code == 200, f"实际 {r6.status_code}")
    r7 = client.get(f"/api/chat/sessions/{sid}/history")
    check("清空后历史为空", r7.json()["count"] == 0, f"实际 {r7.json()['count']}")

    r8 = client.get(f"/api/chat/sessions/{sid_other}/history")
    check("清空不影响其它会话", r8.json()["count"] == 1, f"实际 {r8.json()['count']}")

    # --- 7. 无历史会话返回空而非 500 ---
    print("\n[7] 未知会话返回空（不报 500）")
    r9 = client.get(f"/api/chat/sessions/nonexistent_{uuid.uuid4().hex[:8]}/history")
    check("HTTP 200", r9.status_code == 200, f"实际 {r9.status_code}")
    check("count 为 0", r9.json()["count"] == 0)

    # --- 8. 清理 ---
    print("\n[8] 清理测试数据")
    ShortTermMemory(session_id=sid).clear()
    ShortTermMemory(session_id=sid_other).clear()
    from core.redis_pool import get_redis_pool
    from memory.short_term import HISTORY_KEY_PREFIX
    with get_redis_pool().get_client() as c:
        left = list(c.scan_iter(match=f"{HISTORY_KEY_PREFIX}e2e_*", count=100))
    check("测试会话已清理", len(left) == 0, f"残留 {len(left)}")

    print("\n" + "=" * 68)
    print(f"结果: {len(PASS)} 通过 / {len(FAIL)} 失败")
    for f in FAIL:
        print(f"  - {f}")
    print("=" * 68)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
