"""
Learning Curve — 长期技能表现追踪

目标：
- 每天记录一个快照（pass_rate, failed_count, avg_latency_ms）
- 生成文本格式的 sparkline 趋势图
- 对比近期 vs 上期的变化（证明 dojo 有效）

数据存储：
  skill_history.json — 每日快照的时间序列

调用方式：
  python learning_curve.py [--days 30] [--show-sparkline]
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home()
LOG_BASE = HERMES / ".hermes/evolution_logs" / "skill_optimizer"
TRENDS = LOG_BASE / "trends.json"
HISTORY_DB = LOG_BASE / "skill_history.json"
REPORTS_DIR = LOG_BASE / "reports"


def load_trends(days: int = 30):
    """从 trends.json 加载指定天数的数据"""
    if not TRENDS.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    try:
        data = json.loads(TRENDS.read_text())
    except Exception:
        return []

    records = data.get("records", [])
    return [
        r for r in records
        if r.get("timestamp", "") >= cutoff.isoformat()
    ]


def compute_daily_snapshots(records: list, days: int = 30) -> list:
    """按天聚合，计算每日指标"""
    daily = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "expected_fail": 0,
                                 "latencies": [], "skills": set(), "failed_skills": set(), "expected_fail_skills": set()})

    # 正确分类函数（与 reporter.py 一致）
    EXPECTED_ERROR_PATTERNS = ("not configured", "not installed", "not set", "not found", "missing", "unavailable")

    def classify_run(r):
        success = r.get("success")
        status = r.get("status", "")
        error = str(r.get("error", "") or "").lower()
        if success is True:
            return "pass"
        if success is None and status in ("healthy", "pass", "warning"):
            return "pass"
        if success is False:
            if any(p in error for p in EXPECTED_ERROR_PATTERNS):
                return "expected_fail"
            return "unexpected_fail"
        return "not_run"

    for r in records:
        ts_str = r.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str)
        except Exception:
            continue
        day = ts.strftime("%Y-%m-%d")

        daily[day]["total"] += 1
        lat = r.get("latency_ms", 0)
        if lat:
            daily[day]["latencies"].append(lat)

        skill = r.get("skill", "unknown")
        daily[day]["skills"].add(skill)

        cls = classify_run(r)
        if cls == "pass":
            daily[day]["passed"] += 1
        elif cls == "expected_fail":
            daily[day]["expected_fail"] += 1
            daily[day]["expected_fail_skills"].add(skill)
        else:  # unexpected_fail or not_run
            daily[day]["failed"] += 1
            daily[day]["failed_skills"].add(skill)

    # 补全缺失的日期
    result = []
    today = datetime.now()
    for i in range(days):
        day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        d = daily.get(day, {"total": 0, "passed": 0, "failed": 0, "expected_fail": 0,
                              "latencies": [], "skills": set(), "failed_skills": set(), "expected_fail_skills": set()})
        latencies = d.get("latencies", [])
        avg_lat = round(sum(latencies) / len(latencies), 1) if latencies else 0
        # 真实通过率：仅基于 unexpected_fail 计算
        real_total = d["passed"] + d["failed"]
        pass_rate = round(d["passed"] / real_total * 100, 1) if real_total > 0 else None

        result.append({
            "date": day,
            "total": d["total"],
            "passed": d["passed"],
            "failed": d["failed"],
            "expected_fail": d.get("expected_fail", 0),
            "pass_rate": pass_rate,
            "avg_latency_ms": avg_lat,
            "skills_tested": len(d["skills"]),
            "failed_skills": sorted(d["failed_skills"]),
            "expected_fail_skills": sorted(d.get("expected_fail_skills", [])),
        })

    result.reverse()  # oldest first
    return result


def save_snapshots(snapshots: list):
    """保存到 skill_history.json（追加/更新）"""
    HISTORY_DB.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if HISTORY_DB.exists():
        try:
            existing = json.loads(HISTORY_DB.read_text())
        except Exception:
            existing = {}

    # 追加或更新
    for snap in snapshots:
        existing[snap["date"]] = snap

    # 只保留最近 90 天
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    existing = {k: v for k, v in existing.items() if k >= cutoff}

    HISTORY_DB.write_text(json.dumps(existing, indent=2, ensure_ascii=False))


def compute_sparkline(values: list, width: int = 20) -> str:
    """生成文本 sparkline"""
    valid = [v for v in values if v is not None]
    if not valid:
        return "░" * width

    v_min = min(valid)
    v_max = max(valid)
    v_range = v_max - v_min if v_max != v_min else 1

    chars = "░▁▂▃▄▅▆▇█"
    line = []
    for v in values:
        if v is None:
            line.append(" ")
        else:
            # 0-8 映射
            idx = int((v - v_min) / v_range * 8)
            idx = max(0, min(8, idx))
            line.append(chars[idx])
    return "".join(line)


def format_learning_curve(snapshots: list, days: int = 30) -> str:
    """格式化学习曲线（文本）"""
    if not snapshots:
        return "⚠️  无历史数据"

    # 最近 7 天 vs 之前 7 天对比
    recent_7 = snapshots[-7:] if len(snapshots) >= 7 else snapshots
    older_7 = snapshots[-14:-7] if len(snapshots) >= 14 else []

    recent_pass_rates = [s["pass_rate"] for s in recent_7]
    older_pass_rates = [s["pass_rate"] for s in older_7] if older_7 else [None] * 7

    recent_avg_lat = [s["avg_latency_ms"] for s in recent_7]
    older_avg_lat = [s["avg_latency_ms"] for s in older_7] if older_7 else [0] * 7

    # 通过率 sparkline
    recent_pr_spark = compute_sparkline(recent_pass_rates, width=15)

    # 计算趋势
    recent_valid = [v for v in recent_pass_rates if v is not None]
    older_valid = [v for v in older_pass_rates if v is not None]

    recent_avg = sum(recent_valid) / len(recent_valid) if recent_valid else 0
    older_avg = sum(older_valid) / len(older_valid) if older_valid else 0

    delta_pr = recent_avg - older_avg
    delta_sign = "+" if delta_pr > 0 else ""

    # 累计修复数
    all_snapshots = snapshots
    total_runs = sum(s["total"] for s in all_snapshots if s["total"])
    total_failed = sum(s["failed"] for s in all_snapshots if s["failed"])
    total_expected = sum(s.get("expected_fail", 0) for s in all_snapshots)

    lines = [
        f"{'─'*55}",
        f"  📈 学习曲线（最近{min(days, 90)}天）",
        f"{'─'*55}",
        "",
        f"  通过率趋势（最近7天）: {recent_pr_spark}  {recent_avg:.1f}%",
        f"  上期平均: {older_avg:.1f}%  |  变化: {delta_sign}{delta_pr:.1f}%",
        "",
        f"  累计运行: {total_runs} 次  |  非预期失败: {total_failed} 次  |  预期环境失败: {total_expected} 次",
    ]

    # 按天明细（只显示有数据的）
    data_days = [s for s in snapshots if s["total"] > 0]
    if data_days:
        lines.append(""),
        lines.append("  每日明细（只显示有测试的天）:")
        for s in data_days[-14:]:  # 最近14天有数据的
            pr = f"{s['pass_rate']:.0f}%" if s["pass_rate"] is not None else "N/A"
            lat = f"{s['avg_latency_ms']:.0f}ms"
            icon = "🟢" if (s["pass_rate"] or 0) >= 80 else ("🟡" if (s["pass_rate"] or 0) >= 50 else "🔴")
            ef = s.get("expected_fail", 0)
            uf = s.get("failed", 0)
            breakdown = ""
            if ef > 0:
                breakdown += f" ⚠️{ef}"
            if uf > 0:
                breakdown += f" ❌{uf}"
            lines.append(f"  {icon} {s['date'][-5:]}: 通过率 {pr}{breakdown} | {lat} | {s['skills_tested']}个技能")

    # 常见失败技能（非预期）
    all_failed_skills = defaultdict(int)
    for s in snapshots:
        for skill in s.get("failed_skills", []):
            all_failed_skills[skill] += 1

    if all_failed_skills:
        top_failed = sorted(all_failed_skills.items(), key=lambda x: x[1], reverse=True)[:5]
        lines.append(""),
        lines.append("  🔴 频繁非预期失败技能（累计）:")
        for skill, count in top_failed:
            lines.append(f"     {skill}: {count}次")

    # 预期环境失败（不计入通过率）
    all_expected_skills = defaultdict(int)
    for s in snapshots:
        for skill in s.get("expected_fail_skills", []):
            all_expected_skills[skill] += 1
    if all_expected_skills:
        top_expected = sorted(all_expected_skills.items(), key=lambda x: x[1], reverse=True)[:5]
        lines.append(""),
        lines.append("  ⚠️  预期环境失败（正常，排除在通过率外）:")
        for skill, count in top_expected:
            lines.append(f"     {skill}: {count}次")

    return "\n".join(lines)


def compute_improvement_evidence(snapshots: list) -> dict:
    """计算改进证据：对比 week-over-week"""
    if len(snapshots) < 14:
        return {"enough_data": False}

    week1 = snapshots[-7:]
    week2 = snapshots[-14:-7]

    def avg_pr(days):
        valid = [s["pass_rate"] for s in days if s["pass_rate"] is not None]
        return sum(valid) / len(valid) if valid else 0

    def avg_lat(days):
        valid = [s["avg_latency_ms"] for s in days if s["avg_latency_ms"] > 0]
        return sum(valid) / len(valid) if valid else 0

    pr1, pr2 = avg_pr(week1), avg_pr(week2)
    lat1, lat2 = avg_lat(week1), avg_lat(week2)

    return {
        "enough_data": True,
        "week1_pass_rate": round(pr1, 1),
        "week2_pass_rate": round(pr2, 1),
        "week1_avg_latency_ms": round(lat1, 1),
        "week2_avg_latency_ms": round(lat2, 1),
        "pass_rate_delta": round(pr1 - pr2, 1),
        "latency_delta": round(lat1 - lat2, 1),
        "improving": pr1 > pr2,
    }


def run():
    days = 30
    show_sparkline = "--show-sparkline" in sys.argv or "-s" in sys.argv

    for arg in sys.argv[1:]:
        if arg.startswith("--days="):
            days = int(arg.split("=", 1)[1])

    # 加载并计算快照
    records = load_trends(days=90)  # 最多90天
    snapshots = compute_daily_snapshots(records, days=days)

    # 保存
    save_snapshots(snapshots)

    # 输出
    curve = format_learning_curve(snapshots, days=days)
    print(curve)

    # 改进证据
    evidence = compute_improvement_evidence(snapshots)
    if evidence.get("enough_data"):
        print(f"\n{'─'*55}")
        print(f"  📊 Week-over-Week 改进证据:")
        print(f"     上周通过率: {evidence['week2_pass_rate']}%")
        print(f"     本周通过率: {evidence['week1_pass_rate']}%")
        print(f"     变化: {'📈+' if evidence['improving'] else '📉'}{evidence['pass_rate_delta']}%")
        print(f"     延迟变化: {evidence['latency_delta']:+.1f}ms")
    else:
        days_of_data = sum(1 for s in snapshots if s["total"] > 0)
        print(f"\n  ℹ️  需要至少14天数据才能计算 WoW 对比，当前有 {days_of_data} 天")

    print(f"\n  📄 历史数据已保存: {HISTORY_DB}")
    return snapshots


if __name__ == "__main__":
    run()
