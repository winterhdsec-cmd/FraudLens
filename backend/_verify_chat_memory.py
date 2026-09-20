"""G3 会话记忆持久化 - 端到端验证脚本

验证点：
1. ShortTermMemory 写入后能从「全新实例」读回（模拟进程重启 / 实例被淘汰）
2. bind_session(load=True) 能恢复历史
3. clear() 同时清内存与 Redis
4. ChatAgent.ensure_session 幂等且能载入历史
5. ChatAgent.restore_session 优先 Redis、回落 checkpoint
"""
import os
import sys
import uuid
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent
_ROOT = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))
# 路由模块导入 deps.py 会强制要求 JWT_SECRET_KEY，验证脚本补一个测试值
os.environ.setdefault("JWT_SECRET_KEY", "verify-script-only-not-a-real-secret")

# 必须先加载 .env：ensure_embedded_redis() 只在 REDIS_AUTOSTART=1 时才会拉起
# 内置 Redis。若不加载，脚本会退化为"依赖环境里碰巧有 Redis"，测试结果不可信。
from dotenv import load_dotenv  # noqa: E402

# 只加载 key.env —— 与 main.py 保持一致（main.py 只 load_dotenv('backend/key.env')）。
# 不加载根目录 .env：python-dotenv 默认 override=False（先加载者胜出），
# 会把 .env 的 REDIS_PASSWORD 等值带进来，造出与生产不一致的配置环境。
load_dotenv(_BACKEND / "key.env")

from memory.short_term import ShortTermMemory, HISTORY_KEY_PREFIX  # noqa: E402
from core.redis_pool import get_redis_pool  # noqa: E402
from core.redis_embedded import wait_for_redis  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' — ' + extra) if extra else ''}")


def main():
    print("=" * 68)
    print("G3 会话记忆持久化 验证")
    print("=" * 68)

    # 自举并**等待**内置 Redis 就绪：否则本脚本会因"环境里碰巧有没有 Redis"
    # 而时通时败，最坏情况是静默走内存兜底、却报告持久化验证通过。
    wait_for_redis()

    pool = get_redis_pool()
    print(f"\n[0] Redis 可用性: {'可用（真实持久化）' if pool else '不可用（将降级纯内存，无法验证持久化）'}")
    if pool is None:
        print("\n!! Redis 不可用，本脚本无法验证持久化路径。")
        print("   请先启动 Redis 后重跑。")
        return 2

    sid = f"verify_{uuid.uuid4().hex[:10]}"

    # --- 1. 写入 -> 全新实例读回 ---
    print("\n[1] 写入后由全新实例读回（模拟进程重启）")
    m1 = ShortTermMemory(session_id=sid)
    m1.add_message("user", "帮我查一下最近的冒充公检法案件")
    m1.add_message("assistant", "已找到 12 起相关案件，其中高风险 3 起。")
    m1.add_message("user", "把高风险的详情发我")
    check("写入 3 条到内存", len(m1.get_messages()) == 3)

    m2 = ShortTermMemory(session_id=sid)          # 全新实例，内存为空
    check("新实例初始内存为空", len(m2.get_messages()) == 0)
    restored = m2.bind_session(sid, load=True)
    check("bind_session(load=True) 返回 True", restored is True)
    check("从 Redis 恢复出 3 条", len(m2.get_messages()) == 3,
          f"实际 {len(m2.get_messages())}")
    check("内容逐字一致",
          [x["content"] for x in m2.get_messages()] == [x["content"] for x in m1.get_messages()])

    # --- 2. 原子追加（不丢历史） ---
    print("\n[2] 增量追加不丢历史")
    m3 = ShortTermMemory(session_id=sid)
    m3.bind_session(sid, load=True)
    m3.add_message("assistant", "已为您导出高风险案件清单。")
    m4 = ShortTermMemory(session_id=sid)
    m4.bind_session(sid, load=True)
    check("追加后为 4 条", len(m4.get_messages()) == 4, f"实际 {len(m4.get_messages())}")
    check("最新一条正确", m4.get_messages()[-1]["content"] == "已为您导出高风险案件清单。")

    # --- 3. 窗口裁剪（maxlen 生效，Redis 保留更长） ---
    print("\n[3] 内存窗口 maxlen 生效")
    m5 = ShortTermMemory(max_messages=5, session_id=sid)
    m5.bind_session(sid, load=True)
    for i in range(10):
        m5.add_message("user", f"补充问题 {i}")
    check("内存窗口截断为 5 条", len(m5.get_messages()) == 5, f"实际 {len(m5.get_messages())}")
    with pool.get_client() as c:
        total = c.llen(f"{HISTORY_KEY_PREFIX}{sid}")
    check("Redis 侧保留更多（>5）", total > 5, f"实际 {total}")

    # --- 4. clear 双清 ---
    print("\n[4] clear() 同时清内存与 Redis")
    m6 = ShortTermMemory(session_id=sid)
    m6.bind_session(sid, load=True)
    check("清空前有历史", len(m6.get_messages()) > 0)
    m6.clear()
    check("内存已清空", len(m6.get_messages()) == 0)
    m7 = ShortTermMemory(session_id=sid)
    check("Redis 已清空（新实例读不到）", m7.bind_session(sid, load=True) is False)

    # --- 5. ChatAgent.ensure_session ---
    print("\n[5] ChatAgent.ensure_session 幂等 + 载入历史")
    from agents.chat_agent import ChatAgent

    sid2 = f"verify_{uuid.uuid4().hex[:10]}"
    seed = ShortTermMemory(session_id=sid2)
    seed.add_message("user", "杀猪盘有什么特征")
    seed.add_message("assistant", "主要特征包括长期情感铺垫、虚假投资平台引流等。")

    agent = ChatAgent()
    r1 = agent.ensure_session(sid2)
    check("ensure_session 返回同一 session_id", r1 == sid2)
    check("载入历史 2 条", len(agent.get_history()) == 2, f"实际 {len(agent.get_history())}")

    r2 = agent.ensure_session(sid2)
    check("二次调用幂等（历史未翻倍）", len(agent.get_history()) == 2,
          f"实际 {len(agent.get_history())}")

    sid3 = agent.ensure_session()
    check("无参调用创建新 session", sid3.startswith("chat_"))
    check("新 session 历史为空", len(agent.get_history()) == 0)

    # --- 6. restore_session 优先 Redis ---
    print("\n[6] restore_session 优先 Redis")
    agent2 = ChatAgent()
    ok = agent2.restore_session(sid2)
    check("restore_session 返回 True", ok is True)
    check("恢复 2 条", len(agent2.get_history()) == 2, f"实际 {len(agent2.get_history())}")

    # --- 7. 路由层读路径（不依赖实例） ---
    print("\n[7] 路由层 get_persisted_history 直读 Redis")
    from routes.chat import get_persisted_history, list_persisted_sessions
    hist = get_persisted_history(sid2)
    check("直读历史 2 条", len(hist) == 2, f"实际 {len(hist)}")
    listing = list_persisted_sessions()
    ids = [s["id"] for s in listing]
    check("会话列表含目标会话", sid2 in ids)
    target = next((s for s in listing if s["id"] == sid2), None)
    check("列表带标题", bool(target and target.get("title")), str(target))
    check("列表带消息数", bool(target and target.get("messageCount") == 2), str(target))

    # --- 8. 清理测试数据 ---
    print("\n[8] 清理测试数据")
    for s in (sid, sid2, sid3):
        try:
            ShortTermMemory(session_id=s).clear()
        except Exception:
            pass
    with pool.get_client() as c:
        left = list(c.scan_iter(match=f"{HISTORY_KEY_PREFIX}verify_*", count=100))
    check("测试会话已清理", len(left) == 0, f"残留 {len(left)}")

    print("\n" + "=" * 68)
    print(f"结果: {len(PASS)} 通过 / {len(FAIL)} 失败")
    if FAIL:
        print("失败项:")
        for f in FAIL:
            print(f"  - {f}")
    print("=" * 68)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
