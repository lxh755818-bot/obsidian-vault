#!/usr/bin/env python3
"""
L3 记忆守护进程 — TTL/P0/P1/P2 自动清理 + Ebbinghaus 遗忘曲线
基于 hierarchical-memory-tree 技能规范

功能:
  1. P1(90天)/P2(30天) TTL 到期自动移入 archive/
  2. Ebbinghaus 遗忘：30天未访问的记忆 access_count -= 1
  3. MEMORY.md 行数检查（硬上限 150 行 / 5KB）
  4. semantic.db 低价值记忆清理（access_count < -3）
  5. archive/ 过期文件清理（可选）

用法:
  python memory_janitor.py run [--dry-run] [--verbose]
  python memory_janitor.py check-memory-md
  python memory_janitor.py archive-stats
"""

import os
import sys
import json
import sqlite3
import re
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

# ── 配置 ──────────────────────────────────────────────
HERMES_DIR = Path.home() / ".hermes"
MEMORY_DIR = HERMES_DIR / "memory"
ARCHIVE_DIR = MEMORY_DIR / "archive"
SEMANTIC_DB = MEMORY_DIR / "semantic.db"
MEMORY_MD = HERMES_DIR / "MEMORY.md"

P1_TTL_DAYS = 90   # P1: 90天未访问 → 移入 archive
P2_TTL_DAYS = 30   # P2: 30天未访问 → 移入 archive
EBBINGHAUS_DAYS = 30  # 30天未访问 → access_count -= 1
MIN_ACCESS_COUNT = -3  # access_count < -3 → 标记可删除

PRIVACY_PATTERNS = [
    (r'MINIMAX[_-]API[_-]KEY\s*=\s*["\']?[^\"\'\s]+', 'MINIMAX_API_KEY=***'),
    (r'API[_-]KEY\s*=\s*["\']?sk-[^\"\'\s]+', 'API_KEY=***'),
    (r'ghp_[a-zA-Z0-9]{36}', 'ghp_***'),
    (r'xox[baprs]-[a-zA-Z0-9]{10,}', 'xoxb_***'),
    (r'bearer [a-zA-Z0-9_\-\.]+', 'bearer ***', re.IGNORECASE),
    (r'token["\']?\s*:\s*["\']?[a-zA-Z0-9_\-\.]+', 'token: ***'),
    (r'835538524[^"\'\s]*', '835538524***'),
]


# ── 隐私过滤 ──────────────────────────────────────────
def privacy_filter(text: str) -> str:
    for pattern, replacement in PRIVACY_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


# ── 数据库操作 ─────────────────────────────────────────
def init_db():
    """确保 semantic.db 有 access_count 和 priority 字段"""
    conn = sqlite3.connect(SEMANTIC_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    
    # 检查现有列
    cols = [r[1] for r in conn.execute("PRAGMA table_info(memories)")]
    
    if 'access_count' not in cols:
        conn.execute("ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0")
        print("  + 添加 access_count 字段")
    
    if 'priority' not in cols:
        conn.execute("ALTER TABLE memories ADD COLUMN priority TEXT DEFAULT 'P2'")
        print("  + 添加 priority 字段")
    
    if 'last_accessed' not in cols:
        conn.execute("ALTER TABLE memories ADD COLUMN last_accessed TEXT DEFAULT ''")
        print("  + 添加 last_accessed 字段")
        # 初始化现有记录的 last_accessed 为创建时间
        conn.execute("UPDATE memories SET last_accessed = created_at WHERE last_accessed = ''")
    
    if 'ttl_days' not in cols:
        conn.execute("ALTER TABLE memories ADD COLUMN ttl_days INTEGER DEFAULT 30")
        print("  + 添加 ttl_days 字段")
    
    conn.commit()
    return conn


def update_access_on_hit(memory_id: int):
    """搜索命中时调用：access_count += 1, 更新 last_accessed"""
    conn = sqlite3.connect(SEMANTIC_DB)
    conn.execute(
        "UPDATE memories SET access_count = access_count + 1, "
        "last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
        (memory_id,)
    )
    conn.commit()
    conn.close()


def apply_ebbinghaus_decay():
    """
    Ebbinghaus 遗忘曲线：
    30天未访问的记忆 access_count -= 1
    （每次遗忘检查，降低该记忆的重要性评分）
    """
    conn = init_db()
    cutoff = (datetime.now() - timedelta(days=EBBINGHAUS_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    
    result = conn.execute("""
        UPDATE memories 
        SET access_count = access_count - 1,
            priority = CASE 
                WHEN priority = 'P0' AND access_count - 1 < -3 THEN 'P1'
                ELSE priority
            END
        WHERE last_accessed < ? AND access_count > -10
    """, (cutoff,)).rowcount
    
    conn.commit()
    conn.close()
    return result


def get_low_value_memories():
    """获取 access_count < -3 的低价值记忆"""
    conn = init_db()
    rows = conn.execute("""
        SELECT id, text, category, access_count, priority,
               last_accessed, created_at
        FROM memories
        WHERE access_count < ?
        ORDER BY access_count ASC
    """, (MIN_ACCESS_COUNT,)).fetchall()
    conn.close()
    return rows


def delete_memories(ids: list[int]):
    """删除指定 id 的记忆"""
    if not ids:
        return 0
    conn = init_db()
    placeholders = ','.join('?' * len(ids))
    count = conn.execute(f"DELETE FROM memories WHERE id IN ({placeholders})", ids).rowcount
    conn.commit()
    conn.close()
    return count


def apply_ttl_cleanup():
    """
    P1: 90天未访问 → 移入 archive/
    P2: 30天未访问 → 移入 archive/
    P0: 永不过期
    """
    conn = init_db()
    cutoff_p1 = (datetime.now() - timedelta(days=P1_TTL_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    cutoff_p2 = (datetime.now() - timedelta(days=P2_TTL_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    
    # P1 超期 → 移到 archive
    p1_rows = conn.execute("""
        SELECT id, text, category, created_at FROM memories
        WHERE priority = 'P1' AND last_accessed < ?
    """, (cutoff_p1,)).fetchall()
    
    # P2 超期 → 移到 archive
    p2_rows = conn.execute("""
        SELECT id, text, category, created_at FROM memories
        WHERE priority = 'P2' AND last_accessed < ?
    """, (cutoff_p2,)).fetchall()
    
    conn.close()
    
    archived_count = 0
    for priority, rows in [('P1', p1_rows), ('P2', p2_rows)]:
        for mid, text, cat, created in rows:
            # 写入 archive 文件
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            archive_file = ARCHIVE_DIR / f"{cat}_{mid}.json"
            entry = {
                "id": mid, "text": text, "category": cat,
                "original_priority": priority,
                "archived_at": datetime.now().isoformat(),
                "created_at": created
            }
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
            archived_count += 1
    
    # 从数据库删除已归档的
    all_ids = [r[0] for r in p1_rows + p2_rows]
    deleted = delete_memories(all_ids)
    
    return {"archived": archived_count, "deleted_from_db": deleted,
            "p1_count": len(p1_rows), "p2_count": len(p2_rows)}


# ── MEMORY.md 检查 ────────────────────────────────────
def check_memory_md():
    """检查 MEMORY.md 是否超过硬上限（150行 / 5KB）"""
    if not MEMORY_MD.exists():
        return {"status": "missing", "lines": 0, "bytes": 0}
    
    content = MEMORY_MD.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    issues = []
    if len(lines) > 150:
        issues.append(f"行数超限: {len(lines)} > 150")
    if len(content.encode('utf-8')) > 5120:
        issues.append(f"大小超限: {len(content)} bytes > 5120")
    
    return {
        "status": "ok" if not issues else "warning",
        "issues": issues,
        "lines": len(lines),
        "bytes": len(content.encode('utf-8'))
    }


# ── 归档统计 ──────────────────────────────────────────
def archive_stats():
    """统计 archive/ 目录"""
    if not ARCHIVE_DIR.exists():
        return {"count": 0, "oldest": None, "newest": None}
    
    files = list(ARCHIVE_DIR.glob("*.json"))
    if not files:
        return {"count": 0, "oldest": None, "newest": None}
    
    dates = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            dates.append(data.get('archived_at', ''))
        except:
            pass
    
    return {
        "count": len(files),
        "oldest": min(dates) if dates else None,
        "newest": max(dates) if dates else None,
        "size_mb": round(sum(f.stat().st_size for f in files) / 1024, 1)
    }


# ── 主流程 ─────────────────────────────────────────────
def run(dry_run: bool = False, verbose: bool = False):
    """执行完整清理流程"""
    print(f"\n🧹 Memory Janitor 运行中... {'[DRY RUN]' if dry_run else ''}")
    print(f"   时间: {datetime.now().isoformat()}")
    
    # 1. Ebbinghaus 遗忘
    print("\n📉 Ebbinghaus 遗忘检查...")
    decayed = apply_ebbinghaus_decay()
    print(f"   影响 {decayed} 条记忆（access_count -= 1）")
    
    # 2. TTL 归档
    print("\n📦 TTL 归档检查...")
    ttl_result = apply_ttl_cleanup()
    print(f"   P1 超期: {ttl_result['p1_count']} 条 → archive/")
    print(f"   P2 超期: {ttl_result['p2_count']} 条 → archive/")
    if ttl_result['archived'] > 0 and dry_run:
        print(f"   [DRY RUN] 跳过实际归档操作")
    elif ttl_result['deleted_from_db'] > 0:
        print(f"   已从数据库删除 {ttl_result['deleted_from_db']} 条")
    
    # 3. 低价值记忆清理
    print("\n🗑️  低价值记忆清理...")
    low_value = get_low_value_memories()
    print(f"   低价值记忆（access_count < {MIN_ACCESS_COUNT}）: {len(low_value)} 条")
    for mid, text, cat, ac, pri, last, created in low_value[:5]:
        print(f"   #{mid} [{pri} ac={ac}] {text[:60]}...")
    if low_value and not dry_run:
        deleted = delete_memories([r[0] for r in low_value])
        print(f"   已删除 {deleted} 条低价值记忆")
    elif low_value and dry_run:
        print(f"   [DRY RUN] 跳过删除")
    
    # 4. MEMORY.md 检查
    print("\n📄 MEMORY.md 健康检查...")
    md_check = check_memory_md()
    if md_check['status'] == 'ok':
        print(f"   ✅ 正常（{md_check['lines']} 行, {md_check['bytes']} bytes）")
    else:
        print(f"   ⚠️  问题: {', '.join(md_check['issues'])}")
        print(f"      {md_check['lines']} 行, {md_check['bytes']} bytes")
    
    # 5. archive 统计
    print("\n📊 Archive 统计...")
    arch = archive_stats()
    print(f"   归档文件: {arch['count']} 个, {arch.get('size_mb', 0)} KB")
    if arch['oldest']:
        print(f"   最旧: {arch['oldest']}")
    if arch['newest']:
        print(f"   最新: {arch['newest']}")
    
    # 6. semantic.db 统计
    print("\n💾 Semantic DB 状态...")
    conn = init_db()
    total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    p0 = conn.execute("SELECT COUNT(*) FROM memories WHERE priority='P0'").fetchone()[0]
    p1 = conn.execute("SELECT COUNT(*) FROM memories WHERE priority='P1'").fetchone()[0]
    p2 = conn.execute("SELECT COUNT(*) FROM memories WHERE priority='P2'").fetchone()[0]
    conn.close()
    print(f"   总记忆: {total} 条 (P0={p0}, P1={p1}, P2={p2})")
    
    print("\n✅ Memory Janitor 完成!\n")
    return {
        "decayed": decayed,
        "ttl": ttl_result,
        "low_value_deleted": len(low_value) if not dry_run else 0,
        "memory_md": md_check,
        "archive": arch
    }


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv
    
    if len(sys.argv) < 2 or sys.argv[1] == "run":
        run(dry_run=dry_run, verbose=verbose)
    elif sys.argv[1] == "check-memory-md":
        result = check_memory_md()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif sys.argv[1] == "archive-stats":
        result = archive_stats()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"未知命令: {sys.argv[1]}")
        print("用法: run|check-memory-md|archive-stats [--dry-run] [--verbose]")
