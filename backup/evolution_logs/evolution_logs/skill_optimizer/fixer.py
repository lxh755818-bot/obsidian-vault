"""
Fixer 模块 v2 — 执行修复动作

改进点（v2）：
- audit_skill: 区分"文件已更新（无需修复）"和"真正通过"
- check_deps_availability: 检查实际 Python 库依赖，不只是环境变量
- add_fix_summary: 把诊断结论写成人类可读的修复说明

调用方式：
  python fixer.py [--dry-run] [--skill <name>]
"""

import json
import re
import sys
import yaml
import subprocess
from pathlib import Path
from datetime import datetime

HERMES = Path.home() / ".hermes"
LOG_BASE = HERMES / "evolution_logs" / "skill_optimizer"
PLAN_IN = LOG_BASE / "improvement_plan.json"
TRENDS = LOG_BASE / "trends.json"
HEARTBEAT = HERMES / "evolution_logs" / "HEARTBEAT.md"
FIXES_OUT = LOG_BASE / "fixes_pending"


# ─── 工具函数 ────────────────────────────────────────────────

def parse_frontmatter(md_path: Path):
    try:
        content = md_path.read_text(errors="replace")
    except Exception:
        return None, None, None
    if not content.startswith("---"):
        return None, None, content
    end_idx = content.find("\n---\n", 3)
    if end_idx == -1:
        end_idx = content.find("\n---", 3)
        if end_idx == -1:
            return None, None, content
    yaml_text = content[3:end_idx].strip()
    body = content[end_idx + 4:]
    try:
        fm = yaml.safe_load(yaml_text)
    except Exception:
        fm = None
    return fm, body, content


def get_audit_from_trends(skill_name: str) -> dict:
    """从 trends.json 读取该技能最近的 audit 结果"""
    if not TRENDS.exists():
        return {}
    try:
        data = json.loads(TRENDS.read_text())
    except Exception:
        return {}
    for r in data.get("records", []):
        if r.get("skill") == skill_name:
            return r.get("audit", {})
    return {}


def check_python_deps(skill_name: str, skill_path: Path) -> dict:
    """检查技能实际需要的 Python 库依赖"""
    fm, body, content = parse_frontmatter(skill_path)
    if fm is None:
        return {"status": "unknown", "missing": [], "checked": []}

    deps = fm.get("dependencies", [])
    if isinstance(deps, str):
        deps = [d.strip() for d in deps.split(",") if d.strip()]
    elif not isinstance(deps, list):
        deps = []

    # 如果 frontmatter 没有 deps，从 body 里扫描 import 语句
    if not deps and body:
        imports = re.findall(r"(?:import|from)\s+(\w+)", body)
        common_mods = {"json", "re", "pathlib", "datetime", "subprocess",
                       "yaml", "collections", "typing", "os", "sys"}
        deps = sorted(set(i for i in imports if i not in common_mods and i.isascii()))

    # 过滤掉非英文/数字的依赖名（如中文注释残渣）
    deps = [d for d in deps if d and d.replace("_", "").replace("-", "").replace(".", "").isalnum() and d.isascii()]

    checked = []
    missing = []

    for dep in deps:
        # 跳过内部模块（不是 pip 包）
        internal_mods = {
            "GapAnalyzer", "SkillTree", "CostAwareRouter", "hermes_tools",
            "skill_view", "Path", "datetime", "json", "re", "yaml",
            "subprocess", "collections", "typing", "os", "sys",
        }
        if dep in internal_mods:
            checked.append(f"{dep}: internal_module (skip)")
            continue

        # 跳过版本号形式的依赖（dep>=1.0）
        if ">=" in dep or "<=" in dep or "==" in dep:
            base_dep = re.split(r"[><=!]", dep)[0].strip()
            if not base_dep:
                checked.append(f"{dep}: version_spec (skip)")
                continue
            dep_to_check = base_dep
        else:
            dep_to_check = dep

        result = subprocess.run(
            [sys.executable, "-c", f"import {dep_to_check}; print({dep_to_check}.__version__ if hasattr({dep_to_check}, '__version__') else 'ok')"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            checked.append(f"{dep}: {version}")
        else:
            # 尝试 pip show
            r2 = subprocess.run(["pip", "show", dep_to_check], capture_output=True, text=True, timeout=5)
            if r2.returncode == 0:
                checked.append(f"{dep}: installed")
            else:
                missing.append(dep)

    return {
        "status": "ok" if not missing else "missing_deps",
        "checked": checked,
        "missing": missing,
        "deps_found": deps,
    }


def check_cli_deps(skill_name: str) -> dict:
    """检查 CLI 工具是否可用"""
    import shutil
    common_cli = ["git", "pip", "python", "curl", "wget", "ssh", "rsync"]
    found = []
    missing = []

    for cmd in common_cli:
        if shutil.which(cmd):
            found.append(cmd)
        else:
            missing.append(cmd)

    return {"found": found, "missing": missing}


def audit_skill(skill_path: Path) -> dict:
    """完整审核一个 SKILL.md 文件"""
    fm, body, content = parse_frontmatter(skill_path)

    issues = []
    suggestions = []

    if fm is None:
        issues.append("YAML frontmatter 解析失败")
        suggestions.append("确保文件以 --- 开头，第二个 --- 标记 YAML 结束")
        return {
            "doc_complete": False,
            "issues": issues,
            "suggestions": suggestions,
            "fm": None,
            "audit_source": "file",
            "note": "文件解析失败",
        }

    name = fm.get("name", "")
    desc = fm.get("description", "")

    if not name or not str(name).strip():
        issues.append("name 字段为空或缺失")
        suggestions.append(f'添加 name: "{skill_path.stem}"')
    if not desc or len(str(desc).strip()) < 10:
        issues.append("description 字段缺失或太短（<10字符）")
        suggestions.append("添加 description 描述技能功能（>10字符）")

    if len(body.strip()) < 50:
        issues.append(f"body 内容不足（{len(body.strip())} 字符 < 50）")
        suggestions.append("body 需要有实质性内容，至少50字符")

    # YAML 格式检查
    try:
        yaml_text = content[3:]
        end_idx = content.find("\n---\n", 3)
        if end_idx == -1:
            end_idx = content.find("\n---", 3)
        if end_idx != -1:
            yaml_text = content[3:end_idx].strip()
        yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        issues.append(f"YAML 语法错误: {str(e)[:80]}")
        suggestions.append("修复 YAML 格式")

    return {
        "doc_complete": len(issues) == 0,
        "issues": issues,
        "suggestions": suggestions,
        "fm": fm,
        "name": name,
        "description": desc[:80] if desc else "",
        "body_chars": len(body.strip()),
        "audit_source": "file",
    }


def fix_doc_fail(skill_path: Path, skill_name: str) -> dict:
    """修复文档问题（doc_fail）"""
    # 先查 trends 里历史 audit 结果
    trend_audit = get_audit_from_trends(skill_name)

    # 再审核当前文件
    audit = audit_skill(skill_path)

    if audit["doc_complete"]:
        # 文件已修复，但 trends 里记录的是旧版本
        return {
            "action": "noop_file_updated",
            "reason": "当前文件已完整，可能是测试期间被修复过",
            "trend_audit": trend_audit,
            "file_audit": {k: v for k, v in audit.items() if k != "fm"},
            "note": "建议：重新运行 skill-cycle-optimizer 测试该技能，验证是否真正通过",
        }

    # 生成修复方案
    fixes = []

    if not audit.get("name"):
        fixes.append({
            "type": "add_field",
            "field": "name",
            "location": "frontmatter",
            "value": skill_path.stem,
            "patch": f'name: "{skill_path.stem}"',
        })

    if not audit.get("description") or len(audit.get("description", "")) < 10:
        fixes.append({
            "type": "add_field",
            "field": "description",
            "location": "frontmatter",
            "value": "请补充描述...",
            "patch": 'description: "技能功能描述"',
        })

    if audit.get("body_chars", 0) < 50:
        fixes.append({
            "type": "expand_body",
            "current_chars": audit.get("body_chars", 0),
            "suggestion": f"body 当前 {audit.get('body_chars', 0)} 字符，需要补充实质内容到50字符以上",
        })

    return {
        "action": "generate_fix",
        "skill": skill_name,
        "skill_path": str(skill_path),
        "file_issues": audit.get("issues", []),
        "file_suggestions": audit.get("suggestions", []),
        "fixes_proposed": fixes,
        "trend_audit": trend_audit,
        "auto_fixable": len(fixes) > 0,
        "approval_required": True,
    }


def diagnose_runtime_error(skill_path: Path, skill_name: str) -> dict:
    """诊断运行时错误"""
    # 1. 检查 Python 库依赖
    py_deps = check_python_deps(skill_name, skill_path)

    # 2. 检查 CLI 工具
    cli_deps = check_cli_deps(skill_name)

    # 3. 读取 trend 历史
    history = []
    if TRENDS.exists():
        try:
            data = json.loads(TRENDS.read_text())
            for r in data.get("records", []):
                if r.get("skill") == skill_name:
                    history.append(r)
        except Exception:
            pass

    recent = sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)[:5]
    latest_audit = recent[0].get("audit", {}) if recent else {}

    # 4. 分析错误模式
    diagnosis = []
    recommendations = []

    if latest_audit.get("error_rate_pct", 0) > 0:
        diagnosis.append(f"错误率: {latest_audit['error_rate_pct']}%")
        recommendations.append("检查 skill body 中是否有错误的工具调用或参数传递")

    if latest_audit.get("load_time_ms", 0) > 2000:
        diagnosis.append(f"加载时间过长: {latest_audit['load_time_ms']}ms")
        recommendations.append("检查是否有大量模块导入，考虑懒加载")

    if py_deps.get("status") == "missing_deps":
        diagnosis.append(f"缺失Python库: {py_deps['missing']}")
        recommendations.append(f"pip install {' '.join(py_deps['missing'])}")

    if cli_deps.get("missing"):
        missing_cli = [c for c in cli_deps["missing"] if c in ["git", "pip", "python"]]
        if missing_cli:
            diagnosis.append(f"缺失CLI工具: {missing_cli}")
            recommendations.append(f"安装缺失工具: {', '.join(missing_cli)}")

    return {
        "skill": skill_name,
        "skill_path": str(skill_path),
        "dep_check": {
            "python": py_deps,
            "cli": cli_deps,
        },
        "recent_runs_summary": {
            "count": len(history),
            "last_run": recent[0].get("timestamp") if recent else None,
            "last_status": recent[0].get("status") if recent else None,
            "last_error_rate": latest_audit.get("error_rate_pct"),
        },
        "latest_audit": latest_audit,
        "diagnosis": diagnosis,
        "recommendations": recommendations,
    }


def add_heartbeat_rule(skill_name: str, score: float, reason: str):
    HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    entry = f"""

## [{datetime.now().strftime("%Y-%m-%d")}] {skill_name} — score={score}

**触发原因**: {reason}

**规则**:
- 执行前检查 dep_available 状态
- 如果失败，查看 `trends.json` 最近记录

---
"""
    HEARTBEAT.write_text(HEARTBEAT.read_text() + entry if HEARTBEAT.exists() else entry)
    return entry


def run(dry_run: bool = True, target_skill: str = None):
    print(f"{'🔍 [DRY RUN] ' if dry_run else '🔧 ' }Fixer v2: 执行修复决策...")

    if not PLAN_IN.exists():
        print("⚠️  无 improvement_plan.json，先运行 monitor.py + analyzer.py")
        return

    plan = json.loads(PLAN_IN.read_text())
    scored = plan.get("plan", [])

    if not scored:
        print("✅ 无待处理决策")
        return

    FIXES_OUT.mkdir(parents=True, exist_ok=True)
    fixes_log = []
    applied_log = []

    for entry in scored:
        skill = entry["skill"]
        if target_skill and skill != target_skill:
            continue

        decision = entry.get("decision")
        score = entry.get("score", 0)
        failure_types = entry.get("failure_types", {})

        # 找 SKILL.md 路径
        skills_dir = HERMES / "skills"
        skill_path = None
        for md in skills_dir.rglob("SKILL.md"):
            fm, _, _ = parse_frontmatter(md)
            if fm and fm.get("name") == skill:
                skill_path = md
                break
        if not skill_path:
            for md in skills_dir.rglob("SKILL.md"):
                if skill in str(md):
                    skill_path = md
                    break

        print(f"\n{'─'*50}")
        print(f"📌 {skill} [{decision}] score={score}")

        if decision == "deep_review":
            if not skill_path:
                print(f"   ⚠️  找不到 SKILL.md，跳过")
                continue

            diag = diagnose_runtime_error(skill_path, skill)
            diag["decision"] = "deep_review"
            diag["score"] = score
            diag["skill"] = skill
            diag["timestamp"] = datetime.now().isoformat()

            # 输出关键信息
            py = diag["dep_check"]["python"]
            print(f"   Python库: {py.get('status', 'unknown')}")
            if py.get("checked"):
                print(f"   ✅ 可用: {py['checked']}")
            if py.get("missing"):
                print(f"   ❌ 缺失: {py['missing']}")

            cli = diag["dep_check"]["cli"]
            if cli.get("missing"):
                critical = [c for c in cli["missing"] if c in ["git", "pip", "python"]]
                if critical:
                    print(f"   ❌ 缺失CLI: {critical}")

            err_rate = diag["recent_runs_summary"].get("last_error_rate")
            if err_rate and err_rate > 0:
                print(f"   ⚠️  错误率: {err_rate}%")

            if diag["diagnosis"]:
                print(f"   诊断结论:")
                for d in diag["diagnosis"]:
                    print(f"      - {d}")
            if diag["recommendations"]:
                print(f"   修复建议:")
                for r in diag["recommendations"]:
                    print(f"      → {r}")

            # 保存
            diag_file = FIXES_OUT / f"{skill.replace('/', '_')}_diag_v2.json"
            diag_file.write_text(json.dumps(diag, indent=2, ensure_ascii=False))
            print(f"   📄 诊断报告: {diag_file.name}")
            fixes_log.append(diag)

        elif decision == "new_skill":
            if not skill_path:
                print(f"   ⚠️  找不到 SKILL.md，跳过")
                continue

            fix_result = fix_doc_fail(skill_path, skill)
            fix_result["decision"] = "new_skill"
            fix_result["score"] = score
            fix_result["skill"] = skill
            fix_result["timestamp"] = datetime.now().isoformat()

            action = fix_result.get("action")
            print(f"   动作: {action}")

            if action == "noop_file_updated":
                print(f"   原因: {fix_result['reason']}")
                trend_a = fix_result.get("trend_audit", {})
                if trend_a:
                    print(f"   trends记录: doc_complete={trend_a.get('doc_complete')}, "
                          f"dep_available={trend_a.get('dep_available')}")
                print(f"   建议: 重新运行 skill-cycle-optimizer 测试该技能")
            else:
                for issue in fix_result.get("file_issues", []):
                    print(f"   ❌ {issue}")
                for fix in fix_result.get("fixes_proposed", []):
                    print(f"   💡 {fix.get('suggestion')}")

            fix_file = FIXES_OUT / f"{skill.replace('/', '_')}_fix_v2.json"
            fix_file.write_text(json.dumps(fix_result, indent=2, ensure_ascii=False))
            auto = fix_result.get("auto_fixable")
            print(f"   📄 修复方案: {fix_file.name}{' [auto-fixable]' if auto else ''}")
            fixes_log.append(fix_result)

        elif decision == "add_rule":
            reason = f"failure_types={list(failure_types.keys())}, score={score}"
            print(f"   添加规则到 HEARTBEAT.md")
            add_heartbeat_rule(skill, score, reason)
            print(f"   ✅ 已添加")
            applied_log.append({"skill": skill, "action": "add_rule"})

    # 汇总
    summary = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "total_processed": len(fixes_log) + len(applied_log),
        "deep_review": len([f for f in fixes_log if f.get("decision") == "deep_review"]),
        "new_skill": len([f for f in fixes_log if f.get("decision") == "new_skill"]),
        "add_rule_applied": len(applied_log),
        "fixes_pending_dir": str(FIXES_OUT),
    }

    print(f"\n{'═'*50}")
    print(f"📊 Fixer v2 执行完毕:")
    print(f"   深度检修: {summary['deep_review']}")
    print(f"   修复方案: {summary['new_skill']}")
    print(f"   规则已添加: {summary['add_rule_applied']}")
    print(f"   修复文件目录: {FIXES_OUT}")

    summary_file = FIXES_OUT / "_fixer_summary_v2.json"
    summary_file.write_text(json.dumps(summary, indent=2))
    print(f"   📄 汇总: {summary_file.name}")

    return summary


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv or "-n" in sys.argv
    target = None
    for arg in sys.argv[1:]:
        if arg.startswith("--skill="):
            target = arg.split("=", 1)[1]
    run(dry_run=dry, target_skill=target)
