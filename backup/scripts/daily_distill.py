#!/usr/bin/env python3
"""
每日蒸馏 — sessions → daily distillate

从过去24小时的会话中提取关键信息，写入 daily_distill/。
每天只跑一次，避免重复蒸馏。

用法：
  python daily_distill.py           # 蒸馏今天
  python daily_distill.py --dry-run # 预览不写入
  python daily_distill.py --day 2026-04-25  # 指定日期
"""

import json
import sqlite3
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta, date

HERMES = Path.home()
SESSION_DB = HERMES / ".hermes" / "state.db"
DISTILL_DIR = HERMES / ".hermes" / "memory" / "daily_distill"
DISTILL_DIR.mkdir(parents=True, exist_ok=True)

# ─── 提取规则 ───────────────────────────────────────────────

# 记忆关键词 → 标记为高价值
MEMORY_WORTHY = [
    "skill", "crontab", "cron job", "api", "token", "key",
    "error", "bug", "fix", "修复", "记住", "配置",
    "path", "路径", "安装", "setup", "deploy",
    "飞书", "feishu", "gateway", "选股", "stock",
]

# 跳过词（纯闲聊，无信息量）
SKIP_PATTERNS = [
    r"^(你好|谢谢|好的|收到|明白|ok|好嘞|好哒)",
    r"^[，。、！？\s]+$",
    r"^(哈哈|嘿嘿|嗯嗯|对对|是的是的)",
    r"^\[SYSTEM:",
    r"^你是.*定时任务",
    r"^DELIVERY:",
    r"^Cron job.*completed",
    r"^EvoMap heartbeat OK",
    r"^HERMES DOJO 日报",
    r"^🏋️ HERMES DOJO",
    r"^🎲 记忆宫殿",
    r"^📊",
    r"^\s*$",
]


def is_memory_worthy(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in MEMORY_WORTHY)


def is_skippable(text: str) -> bool:
    t = text.strip()
    for pat in SKIP_PATTERNS:
        if re.match(pat, t):
            return True
    if len(t) < 10:
        return True
    return False


def extract_key_messages(messages: list) -> list:
    """从消息中提取关键内容"""
    results = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            )
        if not content or not isinstance(content, str):
            continue
        if role not in ("user", "assistant"):
            continue
        if is_skippable(content):
            continue
        if is_memory_worthy(content) or role == "assistant":
            results.append({
                "role": role,
                "content": content[:500],  # 截断超长消息
                "msg_id": msg.get("id", ""),
            })
    return results


def build_distillate(date_str: str, messages: list) -> str:
    """生成蒸馏文本"""
    keys = extract_key_messages(messages)

    lines = [
        f"# 每日蒸馏 — {date_str}",
        f"生成时间: {datetime.now().isoformat()}",
        f"消息总数: {len(messages)}",
        f"关键消息: {len(keys)}",
        "",
        "## 关键交互",
        "",
    ]

    for i, msg in enumerate(keys[:20], 1):  # 最多20条
        role_icon = "👤" if msg["role"] == "user" else "🤖"
        content = msg["content"].replace("\n", " ")[:200]
        lines.append(f"{i}. {role_icon} {content}...")

    lines.extend(["", "## 决策记录", ""])

    # 找决策类消息
    decision_keywords = ["决定", "采用", "选择", "确认", "已修复", "已配置", "已安装", "已创建"]
    for i, msg in enumerate(keys, 1):
        content = msg["content"]
        if any(kw in content for kw in decision_keywords):
            lines.append(f"- {content[:150]}")

    lines.extend(["", "## 技术笔记", ""])

    # 找技术内容
    for i, msg in enumerate(keys, 1):
        content = msg["content"]
        if any(kw in content.lower() for kw in ["python", "api", "skill", "cron", "path", "import"]):
            if len(content) > 30:
                lines.append(f"- {content[:150]}")

    return "\n".join(lines)


def save_distillate(date_str: str, content: str) -> Path:
    path = DISTILL_DIR / f"{date_str}.md"
    path.write_text(content, encoding="utf-8")
    return path


def load_recent_messages(hours: int = 24) -> list:
    """从 state.db 加载最近N小时的会话消息"""
    if not SESSION_DB.exists():
        return []

    # timestamp 是 Unix float，需要用 datetime 转换
    cutoff_ts = datetime.now().timestamp() - hours * 3600

    conn = sqlite3.connect(str(SESSION_DB))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 找最近活跃的 sessions
    sessions = cur.execute("""
        SELECT DISTINCT session_id FROM messages
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
    """, (cutoff_ts,)).fetchall()

    session_ids = [s["session_id"] for s in sessions[:50]]

    if not session_ids:
        conn.close()
        return []

    placeholders = ",".join(["?"] * len(session_ids))
    messages = cur.execute(f"""
        SELECT id, session_id, role, content, timestamp
        FROM messages
        WHERE session_id IN ({placeholders})
        AND timestamp >= ?
        ORDER BY timestamp ASC
    """, (*session_ids, cutoff_ts)).fetchall()

    conn.close()

    result = []
    for msg in messages:
        d = dict(msg)
        d["created_at"] = datetime.fromtimestamp(d["timestamp"]).isoformat()
        if isinstance(d.get("content"), str):
            try:
                d["content"] = json.loads(d["content"])
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(d)

    return result


def main():
    dry_run = "--dry-run" in sys.argv
    target_date = None

    for arg in sys.argv:
        if arg.startswith("--day="):
            target_date = arg.split("=", 1)[1]

    today = target_date or date.today().isoformat()
    distill_path = DISTILL_DIR / f"{today}.md"

    # 已蒸馏则跳过
    if distill_path.exists() and not dry_run:
        print(f"ℹ️  今日已蒸馏: {distill_path.name}")
        print(f"   大小: {distill_path.stat().st_size} 字节")
        return

    print(f"📦 加载最近24小时会话...")
    messages = load_recent_messages(hours=24)
    print(f"   获取消息: {len(messages)} 条")

    if not messages:
        print("⚠️  无消息，跳过")
        return

    print(f"🔍 提取关键内容...")
    distillate = build_distillate(today, messages)
    lines = distillate.split("\n")
    print(f"   蒸馏后: {len(lines)} 行")

    if dry_run:
        print("\n📋 预览（前50行）:")
        for line in lines[:50]:
            print(f"  {line}")
        return

    path = save_distillate(today, distillate)
    print(f"\n✅ 蒸馏完成: {path}")
    print(f"   大小: {path.stat().st_size} 字节")


if __name__ == "__main__":
    main()
