#!/usr/bin/env python3
"""
HERMES DOJO — 自我进化完整闭环

执行流程：
  Monitor → Analyzer → Fixer → Reporter → Learning Curve
                                                       ↓
                                               飞书推送日报

每天 09:00 定时运行（通过 cron job），也可手动触发。

用法：
  python dojo.py [--dry-run] [--no-feishu]
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERMES = Path.home()
LOG_BASE = HERMES / ".hermes/evolution_logs/skill_optimizer"
MONITOR      = LOG_BASE / "monitor.py"
ANALYZER     = LOG_BASE / "analyzer.py"
FIXER        = LOG_BASE / "fixer.py"
REPORTER     = LOG_BASE / "reporter.py"
LEARNING_CURVE = LOG_BASE / "learning_curve.py"
APPLY_FIXES  = LOG_BASE / "apply_fixes.py"
PLAN         = LOG_BASE / "improvement_plan.json"
PALACE_PY    = HERMES / ".hermes" / "memory_palace" / "memory_palace.py"
SEM_DB       = HERMES / ".hermes" / "memory" / "semantic.db"


def run_step(name, script, extra_args=None):
    """执行单个模块，返回 (成功, 输出)"""
    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")
    args = [sys.executable, str(script)]
    if extra_args:
        args.extend(extra_args)
    r = subprocess.run(args, capture_output=True, text=True, timeout=120)
    print(r.stdout)
    if r.stderr:
        err = r.stderr.strip()
        if err and "Error:" not in err and "Traceback" not in err:
            print(f"  [stderr] {err[:200]}")
    return r.returncode == 0


def load_plan():
    if not PLAN.exists():
        return None
    try:
        return json.loads(PLAN.read_text())
    except Exception:
        return None


def generate_feishu_text(plan):
    """生成飞书纯文本消息"""
    now = datetime.now().strftime("%m-%d %H:%M")
    lines = [f"🏋️ HERMES DOJO 日报 — {now}\n"]

    if plan and isinstance(plan, dict):
        summary = plan.get("summary", {})
        if isinstance(summary, dict):
            total = summary.get("total_signals", 0)
        else:
            total = 0
        scored = plan.get("plan", []) or []

        if scored:
            lines.append(f"⚠️ 待处理技能: {total} 个\n")
            for s in scored[:5]:
                icon = "🚨" if s.get("score", 0) > 8 else "⚠️"
                lines.append(
                    f"{icon} [{s.get('score')}] {s.get('skill')}: "
                    f"{s.get('decision_label')}"
                )

        fixes_dir = LOG_BASE / "fixes_pending"
        pending = [
            f.name for f in fixes_dir.glob("*_v2.json")
            if not f.name.startswith("_")
        ] if fixes_dir.exists() else []
        if pending:
            lines.append(f"\n📋 待审批修复: {len(pending)} 个")

        if total == 0:
            lines.append("\n✅ 无待处理信号，系统运行正常")
    else:
        lines.append("\n⚠️ 无数据，请先运行 monitor + analyzer")

    return "".join(lines)


def distill_findings_to_memory():
    """
    Dojo闭环产出 → 自动沉淀为记忆 + 绑定到宫殿桩位

    从 analyzer 报告和 fixer 修复中提取关键发现，
    写入 semantic.db（add_memory），并绑定到档案室/工坊桩位。
    """
    import sqlite3
    from datetime import datetime

    if not PLAN.exists():
        return None

    plan = load_plan()
    if not plan:
        return None

    scored = plan.get("plan", [])
    if not scored:
        return None

    # 连接 semantic.db 添加记忆
    conn = sqlite3.connect(str(SEM_DB))
    cur = conn.cursor()

    results = []

    for s in scored[:5]:  # 最多处理5个
        skill = s.get("skill", "")
        decision = s.get("decision_label", "")
        score = s.get("score", 0)
        if score < 4:
            continue

        # 生成记忆文本
        if decision in ("深度检修", "deep_review"):
            text = f"技能 {skill} 需深度检修，决策={decision}，评分={score}"
            cat = "skill"
        elif decision in ("生成新技能", "new_skill"):
            text = f"建议为 {skill} 生成新技能，决策={decision}，评分={score}"
            cat = "skill"
        elif decision in ("加入规则集", "add_rule"):
            text = f"技能 {skill} 需加入规则集，决策={decision}，评分={score}"
            cat = "workflow"
        else:
            continue

        # 插入记忆
        cur.execute(
            "INSERT INTO memories (text,category,tokens,priority,access_count,created_at,last_accessed,ttl_days) "
            "VALUES (?,?,?,?,0,?,?,90)",
            (text, cat, str(len(text)), "P1", datetime.now().isoformat(), datetime.now().isoformat())
        )
        mem_id = str(cur.lastrowid)

        # 自动绑定到宫殿
        if PALACE_PY.exists():
            import subprocess as sp
            bind_result = sp.run(
                [sys.executable, str(PALACE_PY), "bind", mem_id, "archive:2"],
                capture_output=True, text=True, timeout=10
            )
            if bind_result.returncode == 0:
                results.append({"mem_id": mem_id, "skill": skill, "decision": decision, "bound": True})
            else:
                results.append({"mem_id": mem_id, "skill": skill, "decision": decision, "bound": False})
        else:
            results.append({"mem_id": mem_id, "skill": skill, "decision": decision, "bound": False})

    conn.commit()
    conn.close()
    return results


def send_feishu(message: str):
    """飞书推送（直接调用飞书开放API，cron环境可用）"""
    import os, json, requests

    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    home = os.getenv("FEISHU_HOME_CHANNEL", "oc_2e5cc02fdda5aef65a7f9ca03127eda5")

    if not app_id or not app_secret:
        print("  ⚠️ 飞书发送失败: 未配置 FEISHU_APP_ID/APP_SECRET")
        return False

    try:
        # 1. 获取 tenant access token
        r = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=15
        )
        token_data = r.json()
        if token_data.get("code") != 0:
            print(f"  ⚠️ 飞书token失败: {token_data.get('msg')}")
            return False
        token = token_data.get("tenant_access_token", "")

        # 2. 发送文本消息到 home channel
        r2 = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/messages",
            params={"receive_id_type": "chat_id"},
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            json={
                "receive_id": home,
                "msg_type": "text",
                "content": json.dumps({"text": message})
            },
            timeout=15
        )
        resp = r2.json()
        if resp.get("code") == 0:
            print(f"  📱 飞书发送: 成功")
            return True
        else:
            print(f"  ⚠️ 飞书发送失败: {resp.get('msg')}")
            return False
    except Exception as e:
        print(f"  ⚠️ 飞书发送异常: {e}")
        return False


def main():
    dry_run = "--dry-run" in sys.argv
    no_feishu = "--no-feishu" in sys.argv

    print(f"\n{'#'*55}")
    print(f"#  HERMES DOJO — 自我进化完整闭环")
    print(f"#  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"#  模式: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'#'*55}")

    # Step 1: Monitor
    run_step("Step 1: Monitor（采集失败信号）", MONITOR)

    # Step 2: Analyzer
    run_step("Step 2: Analyzer v2（动态评分）", ANALYZER)

    # Step 3: Fixer（dry-run）
    if dry_run:
        print(f"\n{'='*50}")
        print(f"  Step 3: Fixer（dry-run 模式）")
        print(f"{'='*50}")
        r = subprocess.run(
            [sys.executable, str(FIXER), "--dry-run"],
            capture_output=True, text=True, timeout=60
        )
        print(r.stdout)
    else:
        run_step("Step 3: Fixer v2（执行修复）", FIXER, ["--dry-run"])

    # Step 4: Reporter
    run_step("Step 4: Reporter（生成报告）", REPORTER)

    # Step 5: Learning Curve
    run_step("Step 5: Learning Curve（学习曲线）", LEARNING_CURVE)

    # Step 6: Auto-Fixer（dry-run）
    print(f"\n{'='*50}")
    print(f"  Step 6: Auto-Fixer（dry-run，检查可自动修复的内容）")
    print(f"{'='*50}")
    r = subprocess.run(
        [sys.executable, str(APPLY_FIXES), "--dry-run"],
        capture_output=True, text=True, timeout=30
    )
    print(r.stdout)

    # Step 7: 记忆沉淀（分析报告 → 写入 semantic.db → 绑定宫殿桩位）
    print(f"\n{'='*50}")
    print(f"  Step 7: 记忆沉淀")
    print(f"{'='*50}")
    distill_results = distill_findings_to_memory()
    if distill_results:
        print(f"  沉淀 {len(distill_results)} 条发现到记忆系统:")
        for r2 in distill_results:
            bound_str = "✅ 绑定桩位" if r2["bound"] else "⚠️ 未绑定"
            print(f"    记忆{r2['mem_id']} {r2['skill']} {bound_str}")
    else:
        print("  无需沉淀（分析报告为空或评分均<4）")

    # Step 8: 飞书推送
    if not no_feishu:
        print(f"\n{'='*50}")
        print(f"  Step 7: 飞书推送")
        print(f"{'='*50}")
        plan = load_plan()
        msg = generate_feishu_text(plan)
        print(f"  消息预览:\n{msg[:400]}")
        send_feishu(msg)

    print(f"\n{'#'*55}")
    print(f"#  ✅ DOJO 执行完毕")
    print(f"#  报告目录: {LOG_BASE}/reports/")
    print(f"#  修复目录: {LOG_BASE}/fixes_pending/")
    print(f"#  历史快照: {LOG_BASE}/skill_history.json")
    print(f"#  如需执行自动修复: python apply_fixes.py --approve")
    print(f"{'#'*55}")


if __name__ == "__main__":
    main()
