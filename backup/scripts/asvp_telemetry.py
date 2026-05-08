#!/usr/bin/env python3
"""
ASVP Telemetry Cron — 每2小时从 state.db 聚合 sessions 数据，
上报 Clawvard Uplink Report，然后检查 heartbeat，有内容时推送飞书。
"""

import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────────────────────────
HERMES_HOME = Path.home() / ".hermes"
STATE_DB = HERMES_HOME / "state.db"
WINDOW_FILE = HERMES_HOME / "service_vitals" / "last_window.json"
TELEMETRY_DIR = HERMES_HOME / "service_vitals"

TOKEN = (
    "eyJhbGciOiJIUzI1NiJ9.eyJleGFtSWQiOiJleGFtLWNmYmQzNGY1IiwicmVwb3J0SWQiOiJldmFsLWNmYmQzNGY1IiwiYWdlbnROYW1l"
    "Ijoi5bCPYSIsImVtYWlsIjoibHhoNzU1ODE4QG91dGxvb2suY29tIiwiaWF0IjoxNzc3NDcyOTMxLCJleHAiOjIwOTI4MzI5MzEs"
    "ImlzcyI6ImNsYXd2YXJkIn0.0qAAV4eByFU4t6IhL44FMH_I8-HezUB5copsXx9Kt1I"
)

HEARTBEAT_URL = "https://clawvard.school/api/agent/heartbeat"
REPORT_URL = "https://clawvard.school/api/agent/report"

WINDOW_HOURS = 2  # 每2小时运行一次
FEISHU_HOME = "oc_2e5cc02fdda5aef65a7f9ca03127eda5"  # 小a DM


# ── 会话聚合 ───────────────────────────────────────────────────────────────

def load_last_window() -> dict | None:
    """返回上次上报的 window_end 时间戳（UTC），用于增量查询。"""
    if WINDOW_FILE.exists():
        try:
            return json.loads(WINDOW_FILE.read_text())
        except Exception:
            pass
    return None


def save_last_window(window_end: float) -> None:
    """保存本次 window_end，避免下次重复上报。"""
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
    WINDOW_FILE.write_text(
        json.dumps({"window_end": window_end, "reported_at": time.time()})
    )


def query_sessions(since_ts: float | None) -> list[dict]:
    """从 state.db 读取上次之后结束的所有 session。"""
    if not STATE_DB.exists():
        return []

    conn = sqlite3.connect(str(STATE_DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if since_ts is None:
        # 首次运行：取最近 24h（兜底）
        since_ts = (datetime.now() - timedelta(hours=24)).timestamp()

    c.execute(
        """
        SELECT id, source, message_count, tool_call_count,
               input_tokens, output_tokens, api_call_count,
               started_at, ended_at, end_reason
        FROM sessions
        WHERE ended_at IS NOT NULL
          AND ended_at > ?
        ORDER BY ended_at DESC
        """,
        (since_ts,),
    )
    rows = c.fetchall()
    conn.close()

    sessions = []
    for r in rows:
        sessions.append({
            "id": r["id"],
            "source": r["source"],
            "message_count": r["message_count"] or 0,
            "tool_call_count": r["tool_call_count"] or 0,
            "input_tokens": r["input_tokens"] or 0,
            "output_tokens": r["output_tokens"] or 0,
            "api_call_count": r["api_call_count"] or 0,
            "started_at": r["started_at"],
            "ended_at": r["ended_at"],
            "end_reason": r["end_reason"],
            "wall_time_s": max(0, (r["ended_at"] or 0) - (r["started_at"] or 0)),
        })
    return sessions


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    sorted_vals = sorted(values)
    idx = (len(sorted_vals) - 1) * p / 100
    lo = int(idx)
    hi = lo + 1
    if hi >= len(sorted_vals):
        return sorted_vals[-1]
    return sorted_vals[lo] + (idx - lo) * (sorted_vals[hi] - sorted_vals[lo])


def infer_task_category(sessions: list[dict]) -> dict[str, int]:
    """根据 session 数量和来源推断 task_categories。"""
    counts = {}
    for s in sessions:
        src = s["source"]
        if src == "cron":
            key = "plan"
        elif s["message_count"] > 50:
            key = "research"
        elif s["message_count"] > 10:
            key = "debug" if s["tool_call_count"] > 5 else "explain"
        else:
            key = "chat_casual"
        counts[key] = counts.get(key, 0) + 1
    return counts


def aggregate(sessions: list[dict]) -> dict:
    """把 session 列表聚合成 ASVP service_telemetry 格式。"""
    if not sessions:
        return {}

    tokens_per_s = [s["input_tokens"] + s["output_tokens"] for s in sessions]
    tools_per_s = [s["tool_call_count"] for s in sessions]
    wall_times = [s["wall_time_s"] for s in sessions if s["wall_time_s"] > 0]

    session_count = len(sessions)
    total_in_tok = sum(s["input_tokens"] for s in sessions)
    total_out_tok = sum(s["output_tokens"] for s in sessions)
    total_tools = sum(s["tool_call_count"] for s in sessions)

    # window 时间
    earliest = min(s["started_at"] for s in sessions)
    latest = max(s["ended_at"] for s in sessions)
    # 避免未来时间
    now_ts = time.time()
    latest = min(latest, now_ts)

    window_start = datetime.fromtimestamp(earliest, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    window_end = datetime.fromtimestamp(latest, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 估算 cost（MiniMax M2.7 high-speed 近似）
    # input: $0.0008/1K tokens, output: $0.002/1K tokens
    cost_usd = (total_in_tok / 1000 * 0.0008) + (total_out_tok / 1000 * 0.002)

    return {
        "service_telemetry": {
            "window_start": window_start,
            "window_end": window_end,
            "session_count": session_count,
            "aggregates_overall": {
                # 无用户反馈信号时保守填 neutral
                "abandonment_rate": 0.0,
                "gratitude_rate": 0.0,
                "frustration_rate": 0.0,
                "follow_up_48h_rate": 0.0,
            },
            "aggregates_operational": {
                "tokens_per_session": {
                    "median": _percentile(tokens_per_s, 50),
                    "p90": _percentile(tokens_per_s, 90),
                },
                "cost_per_session_usd": {
                    "median": round(cost_usd / session_count, 4) if session_count else 0,
                    "p90": round(cost_usd * 1.5 / session_count, 4) if session_count else 0,
                },
                "total_wall_time_s": {
                    "median": _percentile(wall_times, 50),
                    "p90": _percentile(wall_times, 90),
                },
                "tool_calls_per_session": {
                    "median": _percentile(tools_per_s, 50),
                    "p90": _percentile(tools_per_s, 90),
                },
            },
            "task_categories": infer_task_category(sessions),
        }
    }


# ── HTTP 客户端 ───────────────────────────────────────────────────────────

def _api_request(url: str, payload: dict | None, token: str) -> tuple[int, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


# ── 技能清单 ──────────────────────────────────────────────────────────────

def get_skills_installed() -> list[dict]:
    """读取 ~/.hermes/skills/ 目录，收集所有技能的 short id。"""
    skills_dir = HERMES_HOME / "skills"
    if not skills_dir.exists():
        return []

    installed = []
    private_count = 0
    for category_dir in skills_dir.iterdir():
        if not category_dir.is_dir():
            continue
        for skill_dir in category_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            skill_id = skill_dir.name
            # 标记私有（项目级）技能
            if skill_id.startswith("_") or skill_id in ("private",):
                private_count += 1
                continue
            version = ""
            if skill_file.exists():
                for line in skill_file.read_text("utf-8", errors="replace").splitlines()[:10]:
                    if line.startswith("version:"):
                        version = line.split(":", 1)[1].strip().strip('"').strip("'")
                        break
            installed.append({"id": skill_id, "version": version})

    if private_count > 0:
        installed.append({"id": "private", "version": ""})

    # dedupe
    seen = set()
    deduped = []
    for item in installed:
        key = item["id"]
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:100]  # cap 100


# ── 飞书推送 ──────────────────────────────────────────────────────────────

def send_feishu(text: str, chat_id: str = FEISHU_HOME) -> bool:
    """用 Hermes CLI 发飞书消息。"""
    import subprocess

    # 构造卡片消息（飞书支持 markdown）
    payload = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}),
    }
    try:
        result = subprocess.run(
            ["hermes", "send", "--platform", "feishu", "--target", chat_id, "--stdin"],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=15,
        )
        return result.returncode == 0
    except Exception:
        return False


# ── 主流程 ───────────────────────────────────────────────────────────────

def main():
    print(f"[ASVP Telemetry] 开始执行 {datetime.now():%Y-%m-%d %H:%M:%S}")

    # 1. 加载上次 window
    last_window = load_last_window()
    since_ts = last_window["window_end"] if last_window else None
    print(f"[ASVP Telemetry] 查询起始: {'上次之后' if since_ts else '最近24h'}")

    # 2. 查询 sessions
    sessions = query_sessions(since_ts)
    print(f"[ASVP Telemetry] 采集到 {len(sessions)} 个 session")

    if not sessions:
        print("[ASVP Telemetry] 无新 session，尝试 heartbeat")
        status, body = _api_request(HEARTBEAT_URL, None, TOKEN)
        print(f"[ASVP Telemetry] Heartbeat → {status}")
        if status == 200 and body and body != "HEARTBEAT_OK":
            send_feishu(f"**Clawvard 心跳检查**\n\n{body[:1000]}")
        return

    # 3. 聚合
    telemetry = aggregate(sessions)
    latest_end = max(s["ended_at"] for s in sessions)

    # 4. 构建上报 payload
    skills = get_skills_installed()

    report_payload = {
        **telemetry,
        "skills_installed": skills,
        "reporting_window_hours": WINDOW_HOURS,
    }

    # 5. 发 Uplink Report
    print("[ASVP Telemetry] 上报 Uplink Report...")
    status, body = _api_request(REPORT_URL, report_payload, TOKEN)
    print(f"[ASVP Telemetry] Uplink → {status}: {body[:200] if body else '(empty)'}")

    uplink_ok = status == 200

    # 6. 发 heartbeat
    print("[ASVP Telemetry] 检查 heartbeat...")
    hb_status, hb_body = _api_request(HEARTBEAT_URL, None, TOKEN)
    print(f"[ASVP Telemetry] Heartbeat → {hb_status}")

    # 7. 保存 window_end
    save_last_window(latest_end)

    # 8. 构建飞书摘要
    tt = telemetry.get("service_telemetry", {})
    agg_op = tt.get("aggregates_operational", {})
    tcat = tt.get("task_categories", {})

    tokens_median = agg_op.get("tokens_per_session", {}).get("median") or 0
    tools_p90 = agg_op.get("tool_calls_per_session", {}).get("p90") or 0
    session_count = tt.get("session_count", 0)
    task_str = ", ".join(f"{k}:{v}" for k, v in sorted(tcat.items()))

    summary = (
        f"**ASVP Telemetry 上报完成**\n\n"
        f"⏱ Window: 最近 {WINDOW_HOURS}h\n"
        f"📊 Sessions: **{session_count}** 个\n"
        f"💬 平均tokens/session: **{int(tokens_median):,}**\n"
        f"🔧 工具调用p90: **{int(tools_p90)}** 次\n"
        f"📂 任务分布: `{task_str}`\n"
        f"✅ Uplink上报: {'成功' if uplink_ok else '失败(' + str(status) + ')'}"
    )

    # Heartbeat 有内容时才附加
    if hb_status == 200 and hb_body and hb_body != "HEARTBEAT_OK":
        summary += f"\n\n---\n**Clawvard 回复:**\n{hb_body[:800]}"

    send_feishu(summary)
    print(f"[ASVP Telemetry] 飞书推送完成")


if __name__ == "__main__":
    main()
