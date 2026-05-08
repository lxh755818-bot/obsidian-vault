"""
Reporter 模块 — 生成飞书日报

输出格式：
- CLI 友好（终端直接看）
- JSON（供外部调用）
- 飞书卡片消息（可选推送）

调用方式：
  python reporter.py [--format cli|json|feishu] [--output <path>]
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

HERMES = Path.home() / ".hermes"
LOG_BASE = HERMES / "evolution_logs" / "skill_optimizer"
TRENDS = LOG_BASE / "trends.json"
PLAN = LOG_BASE / "improvement_plan.json"
FIXES_PENDING = LOG_BASE / "fixes_pending"
REPORTS_DIR = LOG_BASE / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

WINDOW_HOURS = 48


def load_trends_summary():
    """从 trends.json 汇总近期表现"""
    if not TRENDS.exists():
        return {}

    cutoff = datetime.now() - timedelta(hours=WINDOW_HOURS)
    try:
        data = json.loads(TRENDS.read_text())
    except Exception:
        return {}

    records = data.get("records", [])
    recent = [r for r in records if r.get("timestamp", "") >= cutoff.isoformat()]

    # 正确分类：区分"测试无法运行"vs"测试失败"vs"预期环境失败"
    EXPECTED_ERROR_PATTERNS = ("not configured", "not installed", "not set", "not found", "missing", "unavailable")

    def classify_run(r):
        """返回: pass | expected_fail | unexpected_fail | not_run"""
        success = r.get("success")
        status = r.get("status", "")
        error = str(r.get("error", "") or "").lower()

        # case 1: 明确成功
        if success is True:
            return "pass"

        # case 2: 旧 schema 兼容（无 success 字段但 status=healthy/pass）
        if success is None and status in ("healthy", "pass", "warning"):
            return "pass"

        # case 3: 明确失败
        if success is False:
            # 检查是否为预期环境失败
            if any(p in error for p in EXPECTED_ERROR_PATTERNS):
                return "expected_fail"
            return "unexpected_fail"

        # case 4: success=None 且无明确 status → 无法运行
        return "not_run"

    classified = [classify_run(r) for r in recent]
    total = len(classified)
    passed = classified.count("pass")
    expected_fail = classified.count("expected_fail")
    unexpected_fail = classified.count("unexpected_fail")
    not_run = classified.count("not_run")
    # degraded: 任何含 dep_available=fail 或 status=degraded 的记录
    degraded = sum(1 for r in recent if r.get("status") == "degraded" or r.get("audit", {}).get("dep_available") == "fail")

    # 按技能聚合（使用 classify_run 逻辑）
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

    by_skill = {}
    for r in recent:
        s = r["skill"]
        if s not in by_skill:
            by_skill[s] = {"total": 0, "passed": 0, "expected_fail": 0, "unexpected_fail": 0, "degraded": 0, "latencies": []}
        by_skill[s]["total"] += 1
        cls = classify_run(r)
        if cls == "pass":
            by_skill[s]["passed"] += 1
        elif cls == "expected_fail":
            by_skill[s]["expected_fail"] += 1
        elif cls == "unexpected_fail":
            by_skill[s]["unexpected_fail"] += 1
        if r.get("status") == "degraded" or r.get("audit", {}).get("dep_available") == "fail":
            by_skill[s]["degraded"] += 1
        lat = r.get("latency_ms", 0)
        if lat:
            by_skill[s]["latencies"].append(lat)

    # 计算健康度（基于真实通过率，排除预期环境失败）
    health_by_skill = {}
    for s, d in by_skill.items():
        # 真实通过率：仅基于unexpected_fail计算
        real_total = d["passed"] + d["unexpected_fail"]
        rate = d["unexpected_fail"] / real_total if real_total > 0 else 0
        health = "healthy" if rate == 0 else ("degraded" if rate < 0.5 else "critical")
        health_by_skill[s] = {
            "health": health,
            "pass_rate": round((1 - rate) * 100, 1),
            "avg_latency_ms": round(sum(d["latencies"]) / len(d["latencies"]), 1) if d["latencies"] else 0,
            "passed": d["passed"],
            "expected_fail": d["expected_fail"],
            "unexpected_fail": d["unexpected_fail"],
        }

    return {
        "window_hours": WINDOW_HOURS,
        "total_runs": total,
        "passed": passed,
        "failed": unexpected_fail,
        "expected_fail": expected_fail,
        "unexpected_fail": unexpected_fail,
        "not_run": not_run,
        "degraded": degraded,
        "pass_rate_pct": round(passed / total * 100, 1) if total > 0 else 0,
        "by_skill": health_by_skill,
    }


def load_plan_summary():
    """从 improvement_plan.json 汇总改进决策"""
    if not PLAN.exists():
        return {}
    try:
        plan = json.loads(PLAN.read_text())
    except Exception:
        return {}

    scored = plan.get("plan", [])
    summary = plan.get("summary", {})

    return {
        "total_signals": summary.get("total_signals", 0),
        "deep_review": summary.get("deep_review_count", 0),
        "new_skill": summary.get("new_skill_count", 0),
        "add_rule": summary.get("add_rule_count", 0),
        "archive": summary.get("archive_count", 0),
        "top_priority": summary.get("top_priority"),
        "all_decisions": [
            {"skill": s["skill"], "decision": s["decision"], "score": s["score"]}
            for s in scored
        ],
    }


def load_fixes_pending():
    """检查 fixes_pending 目录"""
    if not FIXES_PENDING.exists():
        return []
    files = list(FIXES_PENDING.glob("*.json"))
    # 排除汇总文件
    files = [f for f in files if not f.name.startswith("_")]
    return [f.name for f in files]


def format_cli_report():
    """生成 CLI 友好的报告"""
    trends = load_trends_summary()
    plan = load_plan_summary()
    fixes = load_fixes_pending()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 健康度图标
    def health_icon(rate):
        if rate >= 90:
            return "🟢"
        elif rate >= 70:
            return "🟡"
        else:
            return "🔴"

    # ── Header ────────────────────────────────────────────────
    lines = [
        f"{'═'*55}",
        f"  🏋️  HERMES DOJO 日报 — {now}",
        f"{'═'*55}",
    ]

    # ── 整体健康度 ───────────────────────────────────────────
    t = trends
    if t:
        pr = t.get("pass_rate_pct", 0)
        lines += [
            "",
            f"  📊 整体健康度（过去{t.get('window_hours', 48)}小时）",
            f"  {health_icon(pr)} 通过率: {pr}%  |  "
            f"✅ 通过: {t.get('passed', 0)}  |  "
            f"❌ 非预期失败: {t.get('unexpected_fail', 0)}  |  "
            f"⚠️ 预期环境失败: {t.get('expected_fail', 0)}  |  "
            f"🔶退化: {t.get('degraded', 0)}",
        ]

        # 技能明细
        by_skill = t.get("by_skill", {})
        if by_skill:
            lines.append(""),
            lines.append("  技能明细:")
            for s, h in sorted(by_skill.items(), key=lambda x: x[1]["pass_rate"]):
                icon = health_icon(h["pass_rate"])
                lat = h.get("avg_latency_ms", 0)
                # Show breakdown
                p = h.get("passed", 0)
                ef = h.get("expected_fail", 0)
                uf = h.get("unexpected_fail", 0)
                breakdown = ""
                if ef > 0:
                    breakdown += f" ⚠️{ef}"
                if uf > 0:
                    breakdown += f" ❌{uf}"
                lines.append(f"  {icon} {s}: {h['pass_rate']}%{breakdown} | avg {lat}ms")
    else:
        lines += ["", "  ⚠️  无近期数据"]

    # ── 改进决策 ──────────────────────────────────────────────
    p = plan
    if p and p.get("total_signals", 0) > 0:
        lines += [
            "",
            f"{'─'*55}",
            f"  🔧 改进决策（过去{WINDOW_HOURS}小时信号）",
            f"  待处理信号: {p.get('total_signals', 0)}",
        ]

        top = p.get("top_priority")
        if top:
            lines.append(f"  🚨 最高优先级: [{top.get('score')}] {top.get('skill')}")
            lines.append(f"     动作: {top.get('decision_label')} → {top.get('decision')}")
            ft = top.get("failure_types", {})
            if ft:
                lines.append(f"     失败类型: {', '.join(ft.keys())}")

        # 所有决策
        all_dec = p.get("all_decisions", [])
        if all_dec:
            lines.append(""),
            lines.append("  全部决策:")
            for d in all_dec:
                lines.append(f"    [{d['score']}] {d['skill']}: {d['decision']}")

    # ── 待处理修复 ───────────────────────────────────────────
    if fixes:
        lines += [
            "",
            f"{'─'*55}",
            f"  📋 待审批修复方案: {len(fixes)} 个",
        ]
        for f in fixes:
            lines.append(f"    → {f}")

    lines.append(f"{'═'*55}")
    return "\n".join(lines)


def format_feishu_card():
    """生成飞书消息卡片格式"""
    trends = load_trends_summary()
    plan = load_plan_summary()
    fixes = load_fixes_pending()

    # 健康度颜色
    def health_color(rate):
        if rate >= 90:
            return "green"
        elif rate >= 70:
            return "yellow"
        else:
            return "red"

    t = trends
    p = plan
    now = datetime.now().strftime("%m-%d %H:%M")

    elements = []

    # Header
    elements.append({
        "tag": "markdown",
        "content": f"**🏋️ HERMES DOJO 日报** `{now}`"
    })
    elements.append({"tag": "hr"})

    # 健康度
    if t:
        pr = t.get("pass_rate_pct", 0)
        color = health_color(pr)
        elements.append({
            "tag": "markdown",
            "content": (
                f"**整体健康度** | 🟢{pr}% 通过 | "
                f"✅ {t.get('passed',0)} | "
                f"❌ {t.get('failed',0)} | "
                f"⚠️ {t.get('degraded',0)}"
            )
        })

        by_skill = t.get("by_skill", {})
        if by_skill:
            skill_lines = []
            for s, h in sorted(by_skill.items(), key=lambda x: x[1]["pass_rate"]):
                icon = "🟢" if h["pass_rate"] >= 90 else ("🟡" if h["pass_rate"] >= 70 else "🔴")
                skill_lines.append(f"{icon} {s}: {h['pass_rate']}%")
            elements.append({
                "tag": "markdown",
                "content": "\n".join(skill_lines)
            })

    # 改进决策
    if p and p.get("total_signals", 0) > 0:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "markdown",
            "content": f"**🔧 改进决策** | 信号: {p.get('total_signals',0)}"
        })
        top = p.get("top_priority")
        if top:
            elements.append({
                "tag": "markdown",
                "content": f"🚨 **[{top.get('score')}] {top.get('skill')}**\n→ {top.get('decision_label')}"
            })
        for d in p.get("all_decisions", []):
            elements.append({
                "tag": "markdown",
                "content": f"[{d['score']}] {d['skill']}: `{d['decision']}`"
            })

    # 待处理修复
    if fixes:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "markdown",
            "content": f"**📋 待审批修复**: {len(fixes)} 个\n" + "\n".join(f"→ `{f}`" for f in fixes)
        })

    return {"msg_type": "post", "content": {"post": {"zh_cn": {"title": "HERMES DOJO 日报", "content": [[e] for e in elements]}}}}


def save_report(format_type: str = "cli"):
    """保存报告到文件"""
    if format_type == "cli":
        content = format_cli_report()
        path = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path.write_text(content)
        return path, content

    elif format_type == "json":
        data = {
            "generated_at": datetime.now().isoformat(),
            "trends": load_trends_summary(),
            "plan": load_plan_summary(),
            "fixes_pending": load_fixes_pending(),
        }
        path = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return path, data

    elif format_type == "feishu":
        card = format_feishu_card()
        path = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_feishu.json"
        path.write_text(json.dumps(card, indent=2, ensure_ascii=False))
        return path, card

    return None, ""


def run():
    fmt = "cli"
    for arg in sys.argv[1:]:
        if arg in ("--format", "-f") and arg in sys.argv:
            idx = sys.argv.index(arg)
            fmt = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "cli"
        elif arg.startswith("--format="):
            fmt = arg.split("=", 1)[1]

    path, content = save_report(fmt)

    if fmt == "cli":
        print(content)
        print(f"\n📄 报告已保存: {path}")
    elif fmt == "json":
        print(json.dumps(content, indent=2, ensure_ascii=False))
        print(f"\n📄 JSON 报告已保存: {path}")
    elif fmt == "feishu":
        print(json.dumps(content, indent=2, ensure_ascii=False))
        print(f"\n📄 飞书卡片已保存: {path}")

    return path


if __name__ == "__main__":
    run()
