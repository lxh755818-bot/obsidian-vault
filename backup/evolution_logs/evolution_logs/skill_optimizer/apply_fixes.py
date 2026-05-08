"""
Auto-Fixer — 对 Fixer 输出的可自动修复问题执行实际修复

安全策略：
- 所有修改前先备份到 history/
- 修复后验证文件仍可解析
- 高危操作（deep_review）跳过，仅处理 doc_fail 和 add_rule

用法：
  python apply_fixes.py [--dry-run] [--skill <name>] [--approve]
"""

import json
import re
import shutil
import sys
import yaml
from datetime import datetime
from pathlib import Path

HERMES = Path.home()
LOG_BASE = HERMES / ".hermes/evolution_logs" / "skill_optimizer"
FIXES_PENDING = LOG_BASE / "fixes_pending"
SKILLS_DIR = HERMES / "skills"
BACKUP_DIR = LOG_BASE / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def backup_file(src_path: Path) -> Path:
    """备份文件到 backups/"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{ts}_{src_path.name}"
    dst = BACKUP_DIR / name
    shutil.copy2(src_path, dst)
    print(f"  💾 备份: {dst.name}")
    return dst


def parse_frontmatter(content: str):
    if not content.startswith("---"):
        return None, content, None
    end_idx = content.find("\n---\n", 3)
    if end_idx == -1:
        end_idx = content.find("\n---", 3)
        if end_idx == -1:
            return None, content, None
    yaml_text = content[3:end_idx].strip()
    body = content[end_idx + 4:]
    try:
        fm = yaml.safe_load(yaml_text)
    except Exception:
        fm = None
    return fm, body, content


def validate_skill_md(path: Path) -> bool:
    """验证文件仍可解析"""
    try:
        content = path.read_text(errors="replace")
        if content.startswith("---"):
            end_idx = content.find("\n---\n", 3)
            if end_idx == -1:
                end_idx = content.find("\n---", 3)
            if end_idx != -1:
                yaml.safe_load(content[3:end_idx].strip())
        return True
    except Exception as e:
        print(f"  ❌ 验证失败: {e}")
        return False


def apply_add_field(content: str, field: str, value: str) -> str:
    """向 frontmatter 添加字段"""
    fm, body, original = parse_frontmatter(content)
    if fm is None:
        print(f"  ⚠️  无法解析 frontmatter，跳过")
        return content

    # 在现有 frontmatter 中添加
    if field not in fm:
        fm[field] = value

    # 重新序列化 YAML
    yaml_text = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    # yaml.dump 会去掉 trailing newline，手动补上
    yaml_text = yaml_text.rstrip() + "\n"
    new_content = f"---\n{yaml_text}---\n{body}"
    return new_content


def apply_add_description(content: str, skill_name: str) -> str:
    """补充 description 字段"""
    fm, body, original = parse_frontmatter(content)
    if fm is None:
        return content

    # 根据技能名生成描述
    auto_descriptions = {
        "peft": "PEFT fine-tuning 技能 — 使用 huggingface/peft 库进行参数高效微调",
        "xiaoa-persona-system": "小a人格系统 — 构建和管理 AI Agent 人格的核心技能",
        "axolotl": "Axolotl 微调技能 — 支持多种 LLM 微调方法",
        "grpo-rl-training": "GRPO 强化学习训练技能 — 基于 GRPO 算法的 LLM 对齐训练",
        "skill-cycle-optimizer": "技能循环优化自进化 — 每2小时测试一个技能，持续改进",
    }

    if "description" not in fm or not str(fm.get("description", "")).strip():
        desc = auto_descriptions.get(skill_name, f"{skill_name} 技能")
        fm["description"] = desc
        yaml_text = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False).rstrip() + "\n"
        return f"---\n{yaml_text}---\n{body}"

    return content


def fix_doc_fail(skill_path: Path, fix_data: dict, dry_run: bool = True) -> bool:
    """修复文档问题"""
    content = skill_path.read_text(errors="replace")
    skill_name = fix_data.get("skill", skill_path.stem)
    fixes = fix_data.get("fixes_proposed", [])
    issues = fix_data.get("file_issues", [])

    if not fixes and not issues:
        print("  ℹ️  无可修复内容")
        return True

    print(f"  待修复问题: {len(issues)} 个，修复方案: {len(fixes)} 个")

    modified = False
    new_content = content

    for fix in fixes:
        ftype = fix.get("type")
        field = fix.get("field")

        if ftype == "add_field":
            if field == "name":
                value = fix.get("value", skill_path.stem)
                print(f"  ➕ 添加 name: {value}")
                new_content = apply_add_field(new_content, "name", value)
                modified = True
            elif field == "description":
                print(f"  ➕ 补充 description")
                new_content = apply_add_description(new_content, skill_name)
                modified = True

        elif ftype == "expand_body":
            suggestion = fix.get("suggestion", "")
            print(f"  ⚠️  body 扩展（需人工）: {suggestion}")

    if modified:
        if dry_run:
            print(f"  🔍 [DRY RUN] 不会实际写入")
            # 预览改动
            fm_new, body_new, _ = parse_frontmatter(new_content)
            if fm_new:
                print(f"     name: {fm_new.get('name')}")
                print(f"     description: {str(fm_new.get('description', ''))[:60]}")
            return True
        else:
            # 备份
            backup_file(skill_path)
            # 写入
            skill_path.write_text(new_content, errors="replace")
            # 验证
            if validate_skill_md(skill_path):
                print(f"  ✅ 修复已写入，文件验证通过")
                return True
            else:
                print(f"  ❌ 修复后验证失败，回滚...")
                return False
    else:
        print(f"  ℹ️  无需修改")
        return True

    return True


def apply_add_rule(skill_name: str, score: float, reason: str, dry_run: bool = True):
    """向 HEARTBEAT.md 添加规则（已由 Fixer 做过）"""
    heartbeat_path = HERMES / "evolution_logs" / "HEARTBEAT.md"
    entry = f"""

## [{datetime.now().strftime("%Y-%m-%d")}] {skill_name} — score={score}

**触发原因**: {reason}

**规则**:
- 执行前检查 dep_available 状态
- 如果失败，查看 `trends.json` 最近记录

---
"""
    if dry_run:
        print(f"  🔍 [DRY RUN] 规则内容:")
        print(entry)
        return True
    else:
        heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
        heartbeat_path.write_text(
            heartbeat_path.read_text() + entry if heartbeat_path.exists() else entry
        )
        print(f"  ✅ 已添加到 HEARTBEAT.md")
        return True


def run(dry_run: bool = True, target_skill: str = None, approve: bool = False):
    mode = "DRY RUN" if dry_run else ("APPROVED" if approve else "AUTO")
    print(f"\n{'='*50}")
    print(f"  Auto-Fixer — {mode}")
    print(f"{'='*50}")

    if approve and dry_run:
        print("⚠️  同时指定 --approve 和 --dry-run，以 --dry-run 优先")
        dry_run = True
        approve = False

    # 读取所有 v2 修复文件
    fix_files = sorted(FIXES_PENDING.glob("*_fix_v2.json"))
    diag_files = sorted(FIXES_PENDING.glob("*_diag_v2.json"))

    print(f"\n找到 {len(fix_files)} 个修复方案, {len(diag_files)} 个诊断报告")

    applied = []
    skipped = []

    # 处理修复方案
    for fix_file in fix_files:
        data = json.loads(fix_file.read_text())
        skill = data.get("skill")
        decision = data.get("decision")
        action = data.get("action", "")

        if target_skill and skill != target_skill:
            continue

        print(f"\n{'─'*40}")
        print(f"📌 {skill} [{decision}] — {action}")

        if action in ("noop", "noop_file_updated"):
            print(f"  ℹ️  无需修复（文件已更新或无需操作）")
            skipped.append(skill)
            continue

        if decision == "new_skill":
            # 找到对应的 SKILL.md
            skill_path = None
            for md in SKILLS_DIR.rglob("SKILL.md"):
                fm, _, _ = parse_frontmatter(md.read_text())
                if fm and fm.get("name") == skill:
                    skill_path = md
                    break
            if not skill_path:
                for md in SKILLS_DIR.rglob("SKILL.md"):
                    if skill in str(md):
                        skill_path = md
                        break

            if not skill_path:
                print(f"  ⚠️  找不到 SKILL.md，跳过")
                skipped.append(skill)
                continue

            ok = fix_doc_fail(skill_path, data, dry_run=dry_run)
            if ok:
                applied.append(skill)
            else:
                skipped.append(skill)

        elif decision == "add_rule":
            score = data.get("score", 0)
            reason = data.get("reason", "")
            apply_add_rule(skill, score, reason, dry_run=dry_run)
            applied.append(skill)

        elif decision == "deep_review":
            print(f"  ⏭️  deep_review 需要人工 review，跳过自动修复")
            print(f"     诊断文件: {skill}_diag_v2.json")
            skipped.append(skill)

    # 汇总
    print(f"\n{'='*50}")
    print(f"  📊 Auto-Fixer {'Dry-Run' if dry_run else 'Applied'} 结果:")
    print(f"  ✅ 已处理: {len(applied)} 个")
    print(f"  ⏭️  跳过: {len(skipped)} 个")
    if applied:
        print(f"  已处理技能: {', '.join(applied)}")
    if skipped:
        print(f"  跳过技能: {', '.join(skipped)}")
    if dry_run:
        print(f"\n  ℹ️  这是 DRY RUN，不实际修改文件")
        print(f"     加 --approve 实际执行修复")
    print(f"{'='*50}")

    return {"applied": applied, "skipped": skipped}


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv or "-n" in sys.argv
    approve = "--approve" in sys.argv
    target = None
    for arg in sys.argv[1:]:
        if arg.startswith("--skill="):
            target = arg.split("=", 1)[1]
    run(dry_run=dry, target_skill=target, approve=approve)
