#!/usr/bin/env python3
"""
检查刘大虾（lxh755818-bot/kk 仓库）的最新留言
每次运行抓取 AGENT_COMM.md，对比上次记录，有更新则输出通知供 cron deliver 推送
"""

import json
import re
import base64
import hashlib
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen

HOME = Path.home()
STATE_FILE = HOME / ".hermes" / "tmp" / "liudaxia_last_check.json"
# 用 raw.githubusercontent.com 而非 GitHub API，绕过匿名限流
COMM_URL = "https://raw.githubusercontent.com/lxh755818-bot/kk/main/AGENT_COMM.md"
NOTIFY_FILE = HOME / ".hermes" / "tmp" / "liudaxia_notify.md"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def get_latest_comm() -> str:
    """通过 raw.githubusercontent.com 获取 AGENT_COMM.md（不限流）"""
    req = Request(
        COMM_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def load_last_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"content_hash": "", "last_update": ""}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def extract_messages(content: str) -> list[dict]:
    """从 AGENT_COMM.md 提取消息块
    格式: ## [刘大虾] 2026-04-22 00:30 或 ## 小a 2026-04-22 00:30
    """
    messages = []
    blocks = re.split(r'\n(?=##\s+\[?\w)', content)
    for block in blocks:
        if not block.strip():
            continue
        header_match = re.search(
            r'^##\s+\[?([^\]\n]+?)\]?\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})',
            block, re.MULTILINE
        )
        if header_match:
            author = header_match.group(1).strip()
            time_str = header_match.group(2).strip() + ":00"
            messages.append({
                "author": author,
                "time": time_str,
                "body": block.strip()
            })
    return messages


def get_latest_message(messages: list) -> dict:
    if not messages:
        return {}
    def parse_time(m):
        try:
            return datetime.strptime(m["time"], "%Y-%m-%d %H:%M:%S")
        except:
            return datetime.min
    return sorted(messages, key=parse_time, reverse=True)[0]


def main():
    log("🔍 检查刘大虾留言...")

    try:
        content = get_latest_comm()
    except Exception as e:
        log(f"❌ 获取失败: {e}")
        return

    content_hash = hashlib.md5(content.encode()).hexdigest()
    last_state = load_last_state()

    messages = extract_messages(content)
    if not messages:
        log("⚠️ 未解析到消息块，内容片段:")
        log(content[-500:])
        return

    def parse_time(m):
        try:
            return datetime.strptime(m["time"], "%Y-%m-%d %H:%M:%S")
        except:
            return datetime.min

    # 按时间倒序
    messages_sorted = sorted(messages, key=parse_time, reverse=True)
    latest_msg = messages_sorted[0]

    # 判断最新留言是谁
    author = latest_msg["author"]
    is_liudaxia = author in ("刘大虾", "刘大虾 ")
    is_xiaoa = author in ("小a", "小a ", "lxh755818-bot")

    # 关键修复：去掉 hash 判断——每次都要更新状态，防止卡在旧值
    if is_xiaoa:
        save_state({
            "content_hash": content_hash,
            "last_update": datetime.now().isoformat(),
            "last_author": latest_msg["author"],
            "last_time": latest_msg["time"]
        })
        log(f"📭 最新留言是本人({author} @ {latest_msg['time']})，跳过")
        return

    if is_liudaxia:
        # 找刘大虾的最新一条（messages_sorted 第一个就是）
        liudaxia_latest = latest_msg
        save_state({
            "content_hash": content_hash,
            "last_update": datetime.now().isoformat(),
            "last_author": liudaxia_latest["author"],
            "last_time": liudaxia_latest["time"]
        })

        # 清理 markdown 格式
        preview = liudaxia_latest["body"][:400]
        preview = re.sub(r'#+\s*', '', preview)
        preview = re.sub(r'\*+', '', preview)
        preview = re.sub(r'\n+', ' ', preview)

        notify_content = f"""🦐 刘大虾有新留言

👤 {liudaxia_latest['author']}
🕐 {liudaxia_latest['time']}

{preview[:300]}..."""

        NOTIFY_FILE.parent.mkdir(parents=True, exist_ok=True)
        NOTIFY_FILE.write_text(notify_content, encoding="utf-8")

        # print 到 stdout，cron deliver 捕获后推送给用户
        print(notify_content, flush=True)
    else:
        log(f"⚠️ 最新消息作者未知: [{author}] {latest_msg['time']}")
        log(f"   内容片段: {latest_msg['body'][:200]}")


if __name__ == "__main__":
    main()
