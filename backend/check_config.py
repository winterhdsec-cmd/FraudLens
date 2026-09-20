"""FraudLens 配置自检（**只读**，不修改任何文件）。

为什么需要这个脚本
------------------
本项目有**两套并行的配置入口**，而且「谁生效」取决于**怎么启动**：

  · ``backend/key.env`` —— ``main.py`` 用 ``load_dotenv()`` 显式载入（本地直跑走这条）；
  · 根目录 ``.env`` —— docker-compose 用它做 ``${VAR:-default}`` 插值；同时
    ``core/config.py`` 的 pydantic-settings 配了 ``env_file=".env"``，
    而该路径是**相对当前工作目录**解析的（cwd 不同，读到的就不同）。

两者同名不同值时行为会飘。此前就因此把一个「Redis 密码不一致 → 单次调用 10 秒」
误判成线上缺陷 —— 实际上那是验证脚本手工加载了 ``.env`` 造出来的环境，
真实启动（本地 / 容器）实测都是毫秒级。

本脚本回答三个问题：
  ① 现在这份配置**实际生效**的是什么值？
  ② 两份文件之间有没有互相打架的项？
  ③ 有没有「单看每一项都正常、组合起来会出事」的配置？

用法::

    python check_config.py            # 静态检查（默认，秒回）
    python check_config.py --probe    # 额外做一次 Redis 连通与鉴权探测

退出码：发现 ERROR 返回 1，否则 0（可直接用于 CI/启动自检）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from dotenv import dotenv_values

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent
ENV_FILE = ROOT / ".env"
KEY_FILE = BACKEND / "key.env"

SENSITIVE_HINTS = ("PASSWORD", "KEY", "SECRET", "TOKEN")
WEAK_SECRETS = ("fraudlens-jwt-secret-key-2024", "secret", "changeme", "your-secret-key")

ERRORS: list = []
WARNS: list = []
OKS: list = []


def mask(name: str, val) -> str:
    if val is None or val == "":
        return "(空)"
    s = str(val)
    if any(h in name.upper() for h in SENSITIVE_HINTS):
        return f"{s[:4]}****{s[-2:]}" if len(s) > 6 else "****"
    return s


def err(msg: str) -> None:
    ERRORS.append(msg)
    print(f"  [错误] {msg}")


def warn(msg: str) -> None:
    WARNS.append(msg)
    print(f"  [警告] {msg}")


def ok(msg: str) -> None:
    OKS.append(msg)
    print(f"  [正常] {msg}")


def main() -> int:
    ap = argparse.ArgumentParser(description="FraudLens 配置自检（只读）")
    ap.add_argument("--probe", action="store_true", help="额外探测 Redis 连通与鉴权")
    args = ap.parse_args()

    print("=" * 72)
    print("FraudLens 配置自检（只读，不修改任何文件）")
    print("=" * 72)

    env_vals = dict(dotenv_values(ENV_FILE)) if ENV_FILE.exists() else {}
    key_vals = dict(dotenv_values(KEY_FILE)) if KEY_FILE.exists() else {}

    # ---------------------------------------------------------------- 1
    print("\n【1】两份配置文件")
    print(f"  {ENV_FILE}")
    print(f"      存在={ENV_FILE.exists()}  条目={len(env_vals)}"
          f"        （docker-compose 插值用）")
    print(f"  {KEY_FILE}")
    print(f"      存在={KEY_FILE.exists()}  条目={len(key_vals)}"
          f"        （main.py 显式加载，本地直跑用）")
    if not KEY_FILE.exists():
        err("backend/key.env 不存在 —— 本地直跑会拿不到任何配置（全走默认值）")

    # ---------------------------------------------------------------- 2
    shared = sorted(set(env_vals) & set(key_vals))
    print(f"\n【2】两份文件都定义了、需保持一致的项（{len(shared)} 个）")
    conflicts = []
    for name in shared:
        a, b = env_vals.get(name), key_vals.get(name)
        if a == b:
            print(f"  {name:26s} 一致   {mask(name, a)}")
        else:
            conflicts.append(name)
            print(f"  {name:26s} ★不一致  .env={mask(name, a)}   key.env={mask(name, b)}")
    if conflicts:
        warn(f"{len(conflicts)} 个同名项两处取值不同：{', '.join(conflicts)}")
        if "JWT_SECRET_KEY" in conflicts:
            err("JWT_SECRET_KEY 两处取值不同 —— 本地直跑与容器部署签发的 token 互不通用，"
                "切换部署方式会让所有用户被登出。请统一为同一个值（改哪份由你决定）")
    else:
        ok("同名项取值全部一致")

    # ---------------------------------------------------------------- 3
    only_env = sorted(set(env_vals) - set(key_vals))
    only_key = sorted(set(key_vals) - set(env_vals))
    print("\n【3】只在单边定义的项")
    if only_env:
        print("  仅 .env（本地直跑时**不存在**，除非 cwd 让 pydantic 读到 .env）：")
        for n in only_env:
            print(f"    {n:26s} {mask(n, env_vals.get(n))}")
    if only_key:
        print("  仅 key.env（容器里由 docker-compose 的 environment 显式传入）：")
        for n in only_key:
            print(f"    {n:26s} {mask(n, key_vals.get(n))}")

    # ---------------------------------------------------------------- 4
    print("\n【4】实际生效值（按 main.py 的加载方式：只 load key.env）")
    load_dotenv(KEY_FILE)
    try:
        sys.path.insert(0, str(BACKEND))
        from core.config import settings  # noqa: E402
    except Exception as e:  # noqa: BLE001
        err(f"无法加载 core.config.settings: {type(e).__name__}: {e}")
        settings = None

    if settings is not None:
        for name in ("ENV", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER",
                     "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "REDIS_AUTOSTART",
                     "DISABLE_CLOUD_LLM", "CLOUD_LLM_MASK",
                     "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL", "JWT_SECRET_KEY", "TLS_ENABLED"):
            val = getattr(settings, name, "<未定义>")
            print(f"    {name:26s} {mask(name, val)}")

        # ---- cwd 风险：pydantic 的 env_file=".env" 是按 cwd 解析的
        cwd_env = Path(".env")
        print("\n【5】pydantic 兜底 env_file 的解析风险")
        print(f"    当前工作目录 = {Path.cwd()}")
        if cwd_env.exists():
            cwd_vals = dict(dotenv_values(cwd_env))
            extra = sorted(set(cwd_vals) - set(key_vals))
            warn(f"    当前 cwd 下存在 .env —— pydantic 会把 key.env 里**没有**的 {len(extra)} 项读进来："
                 f"{', '.join(extra[:8])}")
            if "REDIS_PASSWORD" in extra:
                warn("    其中含 REDIS_PASSWORD —— 而内置 Redis（REDIS_AUTOSTART=1）通常**未启用鉴权**，"
                     "两者不一致时每次取 Redis 客户端都会先吃一次失败的 AUTH 往返。"
                     "建议：要么删掉这个 .env 项，要么从 backend/ 目录启动")
        else:
            ok("    当前 cwd 下无 .env —— pydantic 只用 key.env 的值，行为与预期一致")

        # ---- 云端 LLM 组合
        print("\n【6】云端大模型配置组合")
        cloud_on = str(getattr(settings, "DISABLE_CLOUD_LLM", "1")) == "0"
        has_key = bool(getattr(settings, "DEEPSEEK_API_KEY", ""))
        masked = str(getattr(settings, "CLOUD_LLM_MASK", "1"))
        if cloud_on and not has_key:
            err("DISABLE_CLOUD_LLM=0（云端已启用）但 DEEPSEEK_API_KEY 为空 —— "
                "凡是走云端的分析会直接失败，且错误信息不指向配置")
        elif cloud_on:
            ok(f"云端已启用，且 API key 已配置（{mask('DEEPSEEK_API_KEY', getattr(settings, 'DEEPSEEK_API_KEY', ''))}）")
        else:
            ok("云端 LLM 已关闭（DISABLE_CLOUD_LLM=1，数据不出域）")
        if cloud_on and masked != "1":
            err(f"云端已启用但 CLOUD_LLM_MASK={masked}（应为 1）—— "
                "出向文本未脱敏，与对外统一口径「本地优先 + 出向脱敏」冲突")
        elif cloud_on:
            ok("出向脱敏已开启（CLOUD_LLM_MASK=1）")

        # ---- Redis 组合
        print("\n【7】Redis 配置组合")
        redis_pw = getattr(settings, "REDIS_PASSWORD", None)
        autostart = str(getattr(settings, "REDIS_AUTOSTART", "0"))
        if autostart == "1" and redis_pw:
            warn("REDIS_AUTOSTART=1（内置 Redis）且配置了 REDIS_PASSWORD —— "
                 "内置 Redis 默认不启用鉴权，两者不一致会多一次注定失败的鉴权往返")
        elif autostart == "1":
            ok("内置 Redis 自启，且未配置密码（与未鉴权的内置实例一致）")
        else:
            ok("未启用内置 Redis（REDIS_AUTOSTART=0），依赖外部 Redis 实例")

        # ---- 密钥强度
        print("\n【8】密钥强度")
        jwt = str(getattr(settings, "JWT_SECRET_KEY", ""))
        if not jwt:
            err("JWT_SECRET_KEY 为空 —— 必须配置，否则 token 签名不可用于任何真实场景")
        elif jwt in WEAK_SECRETS or len(jwt) < 24:
            warn(f"JWT_SECRET_KEY 偏弱（长度 {len(jwt)}，疑似默认值）—— 演示可接受，正式部署请更换")
        else:
            ok(f"JWT_SECRET_KEY 已配置（长度 {len(jwt)}）")

        # ---- 传输安全
        if str(getattr(settings, "ENV", "production")) == "production" and str(getattr(settings, "TLS_ENABLED", "0")) != "1":
            warn("ENV=production 但 TLS_ENABLED!=1 —— 内网演示可接受，对外提供前需启用 TLS")

    # ---------------------------------------------------------------- probe
    if args.probe:
        print("\n【9】Redis 连通与鉴权探测（--probe）")
        try:
            import socket
            import time
            host = getattr(settings, "REDIS_HOST", "localhost") if settings else "localhost"
            port = int(getattr(settings, "REDIS_PORT", 6379) if settings else 6379)
            pw = getattr(settings, "REDIS_PASSWORD", None) if settings else None

            t0 = time.perf_counter()
            reachable = False
            s = socket.socket()
            s.settimeout(1.5)
            try:
                s.connect((host, port))
                reachable = True
                print(f"    端口 {host}:{port} 可连接（{((time.perf_counter()-t0)*1000):.0f}ms）")
            except Exception as e:  # noqa: BLE001
                warn(f"    端口 {host}:{port} 不可连接（{type(e).__name__}）—— "
                     "若为本地直跑，内置 Redis 由 main.py 启动时自启（REDIS_AUTOSTART=1）；"
                     "本脚本不负责拉起它，此处失败**不代表配置有误**")
            finally:
                s.close()

            if not reachable:
                print("    跳过鉴权探测（端口未通）")
            else:
                import redis  # noqa: E402
                c = redis.Redis(host=host, port=port, password=pw or None,
                                socket_timeout=1.0, socket_connect_timeout=0.6,
                                decode_responses=True)
                t0 = time.perf_counter()
                try:
                    c.ping()
                    ok(f"    ping 成功（{((time.perf_counter()-t0)*1000):.0f}ms）")
                except Exception as e:  # noqa: BLE001
                    msg = str(e)
                    warn(f"    ping 失败（{((time.perf_counter()-t0)*1000):.0f}ms）："
                         f"{type(e).__name__}: {msg[:80]}")
                    if "no password is set" in msg:
                        warn("    服务端未启用鉴权但配置了密码 —— core.redis_pool 会自动去密码重连，"
                             "但首次取客户端仍会多一次注定失败的往返（建议清掉配置项）")
        except Exception as e:  # noqa: BLE001
            warn(f"    探测跳过：{type(e).__name__}: {e}")

    # ---------------------------------------------------------------- 汇总
    print("\n" + "=" * 72)
    print(f"汇总：正常 {len(OKS)} / 警告 {len(WARNS)} / 错误 {len(ERRORS)}")
    if ERRORS:
        print("\n必须处理：")
        for m in ERRORS:
            print(f"  ✗ {m}")
    if WARNS:
        print("\n建议关注：")
        for m in WARNS:
            print(f"  ! {m}")
    if not ERRORS and not WARNS:
        print("配置自检未发现问题。")
    print("=" * 72)
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
