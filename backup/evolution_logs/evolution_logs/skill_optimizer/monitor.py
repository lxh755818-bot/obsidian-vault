"""
Monitor 模块 — 从现有数据源采集失败信号

数据源：
1. skill-cycle-optimizer 的 trends.json（技能测试结果）
2. error_ledger.md（错误记录）

输出：
  ~/.hermes/evolution_logs/skill_optimizer/failure_signals.json

  {
    "scanned_at": "ISO",
    "window_hours": 48,
    "signals": [
      {
        "skill": "mcp-image-understanding",
        "signal_type": "test_failure | error_log | user_correction",
        "count": 3,
        "last_seen": "ISO",
        "examples": ["..."],
        "severity": "high | medium | low"
      }
    ],
    "per_skill": {
      "skill_name": {
        "test_failures": N,
        "error_log_entries": N,
        "total_signals": N,
        "severity": "high"
      }
    }
  }

调用方式：
  python monitor.py
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

HERMES = Path.home() / ".hermes"
LOG_BASE = HERMES / "evolution_logs" / "skill_optimizer"
ERROR_LEDGER = HERMES / "evolution_logs" / "error_ledger.md"
TRENDS = LOG_BASE / "trends.json"
SIGNALS_OUT = LOG_BASE / "failure_signals.json"

WINDOW_HOURS = 48


def parse_frontmatter(content: str):
    """从 SKILL.md 内容提取 YAML frontmatter"""
    if not content.startswith("---"):
        return None, content
    end_idx = content.find("\n---\n", 3)
    if end_idx == -1:
        end_idx = content.find("\n---", 3)
        if end_idx == -1:
            return None, content
    yaml_text = content[3:end_idx].strip()
    body = content[end_idx + 4 :]
    import yaml

    try:
        frontmatter = yaml.safe_load(yaml_text)
    except Exception:
        frontmatter = None
    return frontmatter, body


def get_all_skills():
    """扫描所有技能，返回 {skill_name: category}"""
    skills_dir = HERMES / "skills"
    skills = {}
    for md_path in skills_dir.rglob("SKILL.md"):
        rel = md_path.relative_to(skills_dir)
        category = str(rel.parent)
        # 尝试从 frontmatter 读取 name
        try:
            fm, _ = parse_frontmatter(md_path.read_text(errors="replace"))
            if fm and fm.get("name"):
                name = fm["name"]
            else:
                name = rel.stem
        except Exception:
            name = rel.stem
        skills[name] = category
    return skills


def scan_trends():
    """从 trends.json 提取测试失败信号"""
    if not TRENDS.exists():
        return {}

    cutoff = datetime.now() - timedelta(hours=WINDOW_HOURS)
    signals = defaultdict(lambda: {"test_failures": 0, "last_seen": None, "examples": []})

    try:
        data = json.loads(TRENDS.read_text())
    except Exception:
        return {}

    for record in data.get("records", []):
        ts_str = record.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str)
        except Exception:
            continue
        if ts < cutoff:
            continue

        skill = record.get("skill", "unknown")
        status = record.get("status", "")
        # 跳过预期失败（环境依赖未配置等）
        audit = record.get("audit", {})
        if audit.get("dep_available") == "expected_fail":
            continue
        # 判断是否失败
        if status in ("degraded", "fail") or record.get("metrics", {}).get("success") is False:
            signals[skill]["test_failures"] += 1
            signals[skill]["examples"].append(
                f"test_failure: status={status}, latency={record.get('metrics', {}).get('latency_ms')}ms"
            )
            last = record.get("timestamp")
            if last and (signals[skill]["last_seen"] is None or last > signals[skill]["last_seen"]):
                signals[skill]["last_seen"] = last

    return dict(signals)


def scan_error_ledger():
    """从 error_ledger.md 提取错误日志信号"""
    if not ERROR_LEDGER.exists():
        return {}

    cutoff = datetime.now() - timedelta(hours=WINDOW_HOURS)
    signals = defaultdict(lambda: {"error_log_entries": 0, "last_seen": None, "examples": []})

    try:
        content = ERROR_LEDGER.read_text(errors="replace")
    except Exception:
        return {}

    # 按 ## [TIMESTAMP] 分隔条目
    entries = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    for entry in entries:
        if not entry.strip():
            continue
        # 提取时间戳
        ts_match = re.match(r"## \[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", entry)
        if not ts_match:
            continue
        try:
            ts = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M")
        except Exception:
            continue
        if ts < cutoff:
            continue

        # 提取相关技能（从标签或正文）
        skill_tags = re.findall(r"`([^`]+)`", entry)
        skill_in_content = re.search(r"技能.*?[\*_]([\w-]+)[\*_]", entry)
        skill_name = skill_tags[0] if skill_tags else (skill_in_content.group(1) if skill_in_content else None)

        if not skill_name:
            continue

        signals[skill_name]["error_log_entries"] += 1
        signals[skill_name]["examples"].append(entry[:200].replace("\n", " "))
        last = ts_match.group(1)
        if signals[skill_name]["last_seen"] is None or last > signals[skill_name]["last_seen"]:
            signals[skill_name]["last_seen"] = last

    return dict(signals)


def compute_severity(count: int, has_test_failure: bool, has_error_log: bool) -> str:
    """计算严重程度"""
    total = count
    if total >= 3 or (has_test_failure and has_error_log):
        return "high"
    elif total >= 2 or has_test_failure or has_error_log:
        return "medium"
    else:
        return "low"


def run():
    """主函数"""
    print(f"🔍 Monitor: 扫描过去{WINDOW_HOURS}小时的失败信号...")

    # 采集
    trend_signals = scan_trends()
    ledger_signals = scan_error_ledger()

    # 合并
    all_skills = set(trend_signals.keys()) | set(ledger_signals.keys())
    per_skill = {}
    all_signals = []

    for skill in all_skills:
        t = trend_signals.get(skill, {})
        l = ledger_signals.get(skill, {})
        test_failures = t.get("test_failures", 0)
        error_entries = l.get("error_log_entries", 0)
        total = test_failures + error_entries
        last_seen = max(
            filter(None, [t.get("last_seen"), l.get("last_seen")]),
            default=None,
        )
        examples = (t.get("examples", []) + l.get("examples", []))[:5]

        severity = compute_severity(total, test_failures > 0, error_entries > 0)

        per_skill[skill] = {
            "test_failures": test_failures,
            "error_log_entries": error_entries,
            "total_signals": total,
            "last_seen": last_seen,
            "severity": severity,
        }

        if total > 0:
            signal_type = []
            if test_failures > 0:
                signal_type.append("test_failure")
            if error_entries > 0:
                signal_type.append("error_log")

            all_signals.append(
                {
                    "skill": skill,
                    "signal_type": "|".join(signal_type),
                    "count": total,
                    "last_seen": last_seen,
                    "examples": examples,
                    "severity": severity,
                }
            )

    # 按 count 降序排列
    all_signals.sort(key=lambda x: x["count"], reverse=True)

    result = {
        "scanned_at": datetime.now().isoformat(),
        "window_hours": WINDOW_HOURS,
        "total_skills_with_signals": len(all_signals),
        "signals": all_signals,
        "per_skill": per_skill,
        "summary": {
            "high_severity": len([s for s in all_signals if s["severity"] == "high"]),
            "medium_severity": len([s for s in all_signals if s["severity"] == "medium"]),
            "low_severity": len([s for s in all_signals if s["severity"] == "low"]),
        },
    }

    # 保存
    SIGNALS_OUT.parent.mkdir(parents=True, exist_ok=True)
    SIGNALS_OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"✅ 失败信号已保存: {SIGNALS_OUT}")
    print(
        f"   高危: {result['summary']['high_severity']} | "
        f"中危: {result['summary']['medium_severity']} | "
        f"低危: {result['summary']['low_severity']}"
    )

    if all_signals:
        print("\n📋 Top 失败技能:")
        for s in all_signals[:5]:
            print(f"   [{s['severity'].upper()}] {s['skill']}: {s['count']}次 ({s['signal_type']})")

    return result


if __name__ == "__main__":
    run()
