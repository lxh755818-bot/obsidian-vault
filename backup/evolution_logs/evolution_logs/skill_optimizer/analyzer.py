"""
Analyzer 模块 v2 — 基于动态数据的改进决策

改进点（v2）：
- SKILL_FREQ / SKILL_IMPACT / AUTO_FIX 全部从 trends.json 动态计算
- 不再依赖静态配置
- 引入 failure_rate 作为 frequency 的代理变量
- 引入 audit_fail_type 区分 impact（doc_fail vs dep_missing vs runtime_error）
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

HERMES = Path.home() / ".hermes"
LOG_BASE = HERMES / "evolution_logs" / "skill_optimizer"
TRENDS = LOG_BASE / "trends.json"
SIGNALS_IN = LOG_BASE / "failure_signals.json"
PLAN_OUT = LOG_BASE / "improvement_plan.json"

WINDOW_HOURS = 48  # 和 Monitor 保持一致


def load_trends_dynamic():
    """从 trends.json 动态计算每个技能的特征"""
    if not TRENDS.exists():
        return {}

    cutoff = datetime.now() - timedelta(hours=WINDOW_HOURS)
    data = json.loads(TRENDS.read_text())
    records = data.get("records", [])

    stats = defaultdict(lambda: {
        "total": 0,
        "failed": 0,
        "degraded": 0,
        "last_seen": None,
        "failure_types": defaultdict(int),  # doc_fail | dep_missing | runtime_error | timeout
        "avg_latency_ms": 0,
        "latencies": [],
    })

    for r in records:
        ts_str = r.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str)
        except Exception:
            continue
        if ts < cutoff:
            continue

        s = r["skill"]
        stats[s]["total"] += 1
        if not r.get("success"):
            stats[s]["failed"] += 1
        if r.get("status") == "degraded":
            stats[s]["degraded"] += 1

        # 失败类型分类
        audit = r.get("audit", {})
        dep_avail = audit.get("dep_available", "")
        if audit.get("doc_complete") == "fail":
            stats[s]["failure_types"]["doc_fail"] += 1
        elif dep_avail == "fail":
            # 通用api key缺失 → dep_missing（需手动配置）
            stats[s]["failure_types"]["dep_missing"] += 1
        elif dep_avail == "expected_fail":
            # 预期失败（如NOTION_API_KEY未配、arxiv仅需curl）→ 不计入失败信号
            pass
        elif r.get("status") == "degraded":
            stats[s]["failure_types"]["runtime_error"] += 1

        lat = r.get("latency_ms", 0)
        if lat:
            stats[s]["latencies"].append(lat)

        if ts_str and (stats[s]["last_seen"] is None or ts_str > stats[s]["last_seen"]):
            stats[s]["last_seen"] = ts_str

    # 计算平均值
    for s, d in stats.items():
        latencies = d.get("latencies", [])
        if latencies:
            d["avg_latency_ms"] = sum(latencies) / len(latencies)

    return dict(stats)


def compute_frequency(stats_entry: dict) -> float:
    """frequency: 1-5，基于信号次数（测试失败 + error_ledger 记录）"""
    total = stats_entry.get("total", 0)
    failed = stats_entry.get("failed", 0)
    # 如果 failure_types 有记录但 failed=0，也算作一次失败信号
    failure_types = stats_entry.get("failure_types", {})
    has_ft = any((failure_types.get(k) or 0) > 0 for k in failure_types)
    effective_failed = max(failed, 1 if has_ft else 0)
    effective_total = max(total, 1)
    failure_rate = effective_failed / effective_total

    # 测试次数打分（上线5次满分）
    if total >= 5:
        freq_by_count = 5
    elif total >= 3:
        freq_by_count = 4
    elif total >= 2:
        freq_by_count = 3
    elif total == 1:
        freq_by_count = 2
    else:
        freq_by_count = 1

    # 失败率放大系数：失败次数越多，frequency 越高
    if failure_rate >= 0.8:
        freq_multiplier = 1.5
    elif failure_rate >= 0.5:
        freq_multiplier = 1.2
    else:
        freq_multiplier = 1.0

    return min(freq_by_count * freq_multiplier, 5.0)


def _ft_get(d: dict, key: str) -> int:
    """ defaultdict.get() 不返回默认值，必须用 || 代替 """
    return d.get(key) or 0


def compute_impact(stats_entry: dict, skill_name: str) -> float:
    """impact: 1-5，基于失败类型和是否是核心技能"""
    failure_types = stats_entry.get("failure_types", {})

    # 核心技能列表（影响范围大）
    CORE_SKILLS = {
        "skill-cycle-optimizer", "log-error-correction", "evolution-system",
        "self-evolution-system", "deep-research", "intelligence-action-loop",
    }

    # 失败类型严重程度
    rt = _ft_get(failure_types, "runtime_error")
    dm = _ft_get(failure_types, "dep_missing")
    df = _ft_get(failure_types, "doc_fail")

    if rt > 0:
        type_impact = 5  # 运行时错误，影响最大
    elif dm > 0:
        type_impact = 4  # 依赖缺失
    elif df > 0:
        type_impact = 3  # 文档问题
    else:
        type_impact = 3  # 未知类型，默认中等

    # 核心技能加权
    if skill_name in CORE_SKILLS:
        return min(type_impact + 1, 5)
    return type_impact


def compute_auto_fix(failure_types: dict, skill_name: str) -> float:
    """auto_fix_potential: 0.5-2.0，越容易自动修复的值越高"""
    rt = _ft_get(failure_types, "runtime_error")
    dm = _ft_get(failure_types, "dep_missing")
    df = _ft_get(failure_types, "doc_fail")

    # doc_fail → 最容易自动修复（文档模板化）
    if df > 0 and rt == 0:
        return 1.8
    # dep_missing → 需要手动配置
    elif dm > 0:
        return 0.8
    # runtime_error → 最难自动修复
    elif rt > 0:
        return 0.5
    return 1.0


def decide_action(score: float, failure_types: dict) -> tuple:
    """根据评分和失败类型决定行动"""
    rt = _ft_get(failure_types, "runtime_error")
    dm = _ft_get(failure_types, "dep_missing")
    df = _ft_get(failure_types, "doc_fail")

    if score > 8:
        # 100%失败率 + 核心技能 → 需要深度检修
        if rt > 0:
            return "deep_review", "深度检修"
        return "new_skill", "生成新技能"
    elif score >= 4:
        return "add_rule", "加入规则集"
    else:
        return "archive", "归档监控"


def run():
    print("📊 Analyzer v2: 基于动态数据的改进决策...")

    if not SIGNALS_IN.exists():
        print("⚠️  无 failure_signals.json，先运行 monitor.py")
        return

    # 读取 Monitor 信号
    signals_data = json.loads(SIGNALS_IN.read_text())
    signals = signals_data.get("signals", [])

    if not signals:
        print("✅ Monitor 未检测到失败信号，退出")
        PLAN_OUT.write_text(json.dumps({
            "version": "v2",
            "scanned_at": datetime.now().isoformat(),
            "plan": [],
            "summary": "no_signals"
        }, indent=2))
        return

    # 读取动态特征
    dynamic_stats = load_trends_dynamic()

    scored = []
    for s in signals:
        skill = s["skill"]
        signal_count = s["count"]
        severity = s.get("severity", "low")
        dyn = dynamic_stats.get(skill, {})

        freq = compute_frequency(dyn)
        impact = compute_impact(dyn, skill)
        failure_types = dyn.get("failure_types", {})
        auto_fix = compute_auto_fix(failure_types, skill)

        score = freq * impact * auto_fix
        decision, decision_label = decide_action(score, failure_types)

        scored.append({
            "skill": skill,
            "score": round(score, 1),
            "frequency": round(freq, 2),
            "impact": impact,
            "auto_fix_potential": auto_fix,
            "decision": decision,
            "decision_label": decision_label,
            "signal_count": signal_count,
            "total_tests": dyn.get("total", 0),
            "failed_tests": dyn.get("failed", 0),
            "failure_rate": round(dyn.get("failed", 0) / dyn.get("total", 1) * 100, 1) if dyn.get("total", 0) > 0 else 0,
            "failure_types": dict(failure_types),
            "last_seen": dyn.get("last_seen") or s.get("last_seen"),
            "severity": severity,
            "avg_latency_ms": dyn.get("avg_latency_ms", 0),
        })

    # 按 score 降序
    scored.sort(key=lambda x: x["score"], reverse=True)

    plan_new = [r for r in scored if r["decision"] == "new_skill"]
    plan_deep = [r for r in scored if r["decision"] == "deep_review"]
    plan_rule = [r for r in scored if r["decision"] == "add_rule"]
    plan_archive = [r for r in scored if r["decision"] == "archive"]

    plan = {
        "version": "v2",
        "scanned_at": datetime.now().isoformat(),
        "window_hours": WINDOW_HOURS,
        "total_signals": len(signals),
        "plan": scored,
        "summary": {
            "deep_review_count": len(plan_deep),
            "new_skill_count": len(plan_new),
            "add_rule_count": len(plan_rule),
            "archive_count": len(plan_archive),
            "top_priority": plan_deep[0] if plan_deep else (plan_new[0] if plan_new else None),
        },
    }

    PLAN_OUT.write_text(json.dumps(plan, indent=2, ensure_ascii=False))

    print(f"✅ 改进计划已保存: {PLAN_OUT}")
    print(f"\n📋 决策汇总（v2 动态评分）:")
    print(f"   深度检修: {len(plan_deep)}")
    print(f"   生成新技能: {len(plan_new)}")
    print(f"   加入规则集: {len(plan_rule)}")
    print(f"   归档监控:   {len(plan_archive)}")

    if plan_deep:
        print(f"\n🚨 最高优先级 — 深度检修（运行时错误）:")
        for r in plan_deep:
            print(f"   [{r['score']}] {r['skill']}")
            print(f"      失败率: {r['failure_rate']}% | 失败次数: {r['failed_tests']}/{r['total_tests']} | avg延迟: {r['avg_latency_ms']:.0f}ms")

    if plan_new:
        print(f"\n🚨 高优先级 — 生成新技能:")
        for r in plan_new[:5]:
            print(f"   [{r['score']}] {r['skill']} | 失败率: {r['failure_rate']}% | 失败类型: {list(r['failure_types'].keys())}")

    if plan_rule:
        print(f"\n⚠️  次优先级 — 加入规则集:")
        for r in plan_rule[:5]:
            print(f"   [{r['score']}] {r['skill']}")

    return plan


if __name__ == "__main__":
    run()
