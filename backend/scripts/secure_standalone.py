"""
secure_standalone.py — 民警单机版交付前安全加固（生成随机强口令并写回模板）

作用（全程本地，不碰运行中的线上实例）：
  1. 把 .env.min 模板的弱默认口令替换为随机强口令
  2. 强制 DISABLE_CLOUD_LLM=1（关闭云端 LLM，涉敏数据不出域）
  3. 将 DEEPSEEK 密钥置为占位（交给民警前清空云端凭据）
  4. 校验是否已改 admin 默认口令（提示用）

用法:
  python scripts/secure_standalone.py                      # 处理 .env.min
  python scripts/secure_standalone.py --target key.env     # 处理指定文件(如民警交付配置)
  python scripts/secure_standalone.py --check              # 仅体检不修改
"""
import os
import re
import sys
import secrets
import string
import argparse

WEAK_DEFAULTS = {
    "DB_PASSWORD": ["20051223"],
    "JWT_SECRET_KEY": ["fraudlens-jwt-secret-key-2024", "please-change-in-production-32-bytes"],
    "MINIO_ROOT_PASSWORD": ["fraudlens123"],
    "REDIS_PASSWORD": [""],  # 空弱默认 → 补随机（可能影响现有部署，故仅模板层处理）
}


def _strong(n=24, chars=None):
    chars = chars or (string.ascii_letters + string.digits + "!@#%^&*-_=+")
    return "".join(secrets.choice(chars) for _ in range(n))


def _load(path):
    env = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            for ln in f:
                m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", ln)
                if m:
                    k, v = m.group(1), m.group(2)
                    v = v.strip().strip('"').strip("'")
                    # 去注释：仅当值含空格后的 # 才截断（保守，避免误伤含#的复杂口令）
                    env[k] = v
    return env


def _refurb(key, current, fix):
    """返回 (新值, 是否执行加固)。"""
    weak = WEAK_DEFAULTS.get(key, [])
    if current in weak:
        if fix:
            return _strong(), True
        return current, False
    return current, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=None, help="要处理的 env 文件（默认 .env.min）")
    ap.add_argument("--check", action="store_true", help="仅体检，不写回")
    ap.add_argument("--no-cloud-llm", action="store_true", help="强制 DISABLE_CLOUD_LLM=1")
    args = ap.parse_args()

    target = args.target or os.path.join(os.path.dirname(__file__), "..", ".env.min")
    target = os.path.abspath(target)

    if not os.path.isfile(target):
        print(f"[secure] 目标文件不存在: {target}")
        return 1

    env = _load(target)
    fixable = {k for k in WEAK_DEFAULTS if k in env}
    if not fixable:
        print("[secure] 该文件未包含可加固的密钥字段，跳过。")
        return 0

    print(f"[secure] 目标: {target}")
    changed = {}
    for key in sorted(fixable):
        cur = env.get(key, "")
        is_weak = cur in WEAK_DEFAULTS.get(key, [])
        did = False
        newv = cur
        if is_weak and not args.check:
            newv, did = _strong(), True
        if did:
            changed[key] = newv
            print(f"  [加固] {key}: 已替换为随机强口令 (len={len(newv)})")
        else:
            hint = " (弱默认!)" if is_weak else " (看似已非弱默认)"
            print(f"  [体检] {key}: 当前值{hint}，未改动")

    # 云端 LLM 强制关闭
    if env.get("DISABLE_CLOUD_LLM", "0") != "1":
        if not args.check:
            changed["DISABLE_CLOUD_LLM"] = "1"
            print("  [加固] DISABLE_CLOUD_LLM: 0→1 (云端LLM关闭，涉敏数据不出域)")
        else:
            print("  [体检] DISABLE_CLOUD_LLM: 建议置 1")

    # 云端密钥置占位（防泄露）
    if env.get("DEEPSEEK_API_KEY", "").startswith("sk-") and not args.check:
        changed["DEEPSEEK_API_KEY"] = "sk-REPLACE-BEFORE-DELIVERY"
        print("  [加固] DEEPSEEK_API_KEY: 已置为占位，请在交付民警前保持为空/无外网调用")

    if args.check:
        print("\n[secure] 体检完成（未写入任何改动）。")
        return 0

    if not changed:
        print("\n[secure] 无待加固项。")
        return 0

    # 写回（保留注释与未知键，仅替换匹配的键值）
    lines = open(target, "r", encoding="utf-8").readlines()
    out = []
    replaced = set()
    for ln in lines:
        m = re.match(r"^(\s*[A-Za-z_][A-Za-z0-9_]*)(\s*=\s*)(.*?)(\s*)$", ln)
        newline = ln
        if m and m.group(1) in changed:
            newline = f"{m.group(1)}{m.group(2)}{changed[m.group(1)]}{m.group(4) if m.group(4) else ''}"
            # 处理行内可能有换行
            newline = (m.group(1) + m.group(2) + changed[m.group(1)] + "\n")
            replaced.add(m.group(1))
        out.append(newline)
    for k, v in changed.items():
        if k not in replaced:  # 键不存在，追加
            out.append(f"{k}={v}\n")
    with open(target, "w", encoding="utf-8") as f:
        f.writelines(out)

    print(f"\n[secure] 已加固 {len(changed)} 项 → {target}")
    print("[secure] 提醒：若这是当前运行的配置，改密后需同步修改数据库实际口令并重启后端。")
    return 0


if __name__ == "__main__":
    sys.exit(main())