#!/usr/bin/env python3
"""
Hermes Memory Supervisor
分层记忆系统的管理模块

职责:
- 管理 dirty queue (.dirty/ 目录)
- 触发压缩代理
- 维护 index.json 索引
- 处理容量检查和淘汰
- 定期重建索引

使用方式:
  python memory_supervisor.py [action]

Actions:
  check     - 检查状态，不执行任何操作
  process   - 处理 dirty queue 中的所有待整理记忆
  rebuild   - 重建整个 index（扫描所有文件）
  status    - 输出记忆系统状态摘要
"""

import json
import os
import sys
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ============ 配置 ============
HERMES_MEMORIES = Path.home() / ".hermes" / "memories"
INDEX_FILE = HERMES_MEMORIES / "index.json"
L0_MAX_KB = 5  # MEMORY.md 硬上限 KB
L1_MAX_KB = 50  # L1 域硬上限 KB
L2_MAX_KB = 20  # L2 文件硬上限 KB

# 淘汰规则
LRU_DAYS_MIN = 90
LRU_DAYS_MAX = 120
MAX_REFRESH_COUNT = 3  # 同一记忆最多刷新次数

# ============ 工具函数 ============

def load_index() -> dict:
    """加载 index.json"""
    if not INDEX_FILE.exists():
        return _create_default_index()
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_index(index: dict) -> None:
    """保存 index.json（先写备份）"""
    # 备份当前版本
    if INDEX_FILE.exists():
        backup = INDEX_FILE.with_suffix(".json.bak")
        shutil.copy(INDEX_FILE, backup)
    
    index["last_updated"] = datetime.utcnow().isoformat() + "Z"
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

def _create_default_index() -> dict:
    """创建默认 index"""
    return {
        "version": "1.0.0",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "last_rebuild": datetime.utcnow().isoformat() + "Z",
        "nodes": {},
        "dirty": [],
        "archived": [],
        "stats": {
            "total_nodes": 0,
            "total_size_kb": 0,
            "total_files": 0,
            "pending_compression": 0,
            "last_compact": None
        }
    }

def get_dirty_files() -> list:
    """获取 .dirty/ 目录下所有待处理文件"""
    dirty_dir = HERMES_MEMORIES / ".dirty"
    if not dirty_dir.exists():
        return []
    return [f for f in dirty_dir.iterdir() if f.suffix == ".md"]

def get_dir_size_kb(domain_path: Path) -> float:
    """计算目录下所有 md 文件的总大小 KB"""
    if not domain_path.exists():
        return 0.0
    total = sum(f.stat().st_size for f in domain_path.rglob("*.md") if f.is_file())
    return round(total / 1024, 2)

def scan_l1_domains() -> list:
    """扫描 L1 域"""
    domains = []
    for item in HERMES_MEMORIES.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            size_kb = get_dir_size_kb(item)
            domains.append({
                "name": item.name,
                "path": str(item.relative_to(HERMES_MEMORIES)),
                "size_kb": size_kb,
                "file_count": len(list(item.rglob("*.md")))
            })
    return domains

def get_file_age_days(file_path: Path) -> int:
    """获取文件年龄（天）"""
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
    return (datetime.now() - mtime).days

def check_lru_eligible(file_path: Path, index_entry: dict) -> bool:
    """检查文件是否符合 LRU 淘汰条件"""
    age_days = get_file_age_days(file_path)
    if age_days < LRU_DAYS_MIN:
        return False
    
    # 检查刷新次数
    refresh_count = index_entry.get("refresh_count", 0)
    if refresh_count >= MAX_REFRESH_COUNT:
        return True  # 达到刷新上限，必须淘汰
    
    if age_days > LRU_DAYS_MAX:
        return True  # 超过最大天数，必须淘汰
    
    return False  # 在 90-120 天内，且刷新次数未达上限，暂不淘汰

# ============ Actions ============

def action_check():
    """检查状态"""
    print("=== Memory Supervisor Check ===")
    index = load_index()
    dirty = get_dirty_files()
    
    print(f"\nIndex 状态:")
    print(f"  版本: {index.get('version')}")
    print(f"  最后更新: {index.get('last_updated')}")
    print(f"  最后重建: {index.get('last_rebuild')}")
    print(f"  最后压缩: {index.get('stats', {}).get('last_compact')}")
    
    print(f"\n统计:")
    stats = index.get("stats", {})
    print(f"  总节点数: {stats.get('total_nodes', 0)}")
    print(f"  总大小: {stats.get('total_size_kb', 0)} KB")
    print(f"  总文件数: {stats.get('total_files', 0)}")
    print(f"  待压缩: {len(dirty)}")
    
    print(f"\nDirty Queue:")
    if not dirty:
        print("  (空)")
    else:
        for f in dirty:
            print(f"  - {f.name}")
    
    print(f"\nL1 域状态:")
    domains = scan_l1_domains()
    for d in domains:
        status = "⚠️ 超限" if d["size_kb"] > L1_MAX_KB else "✅"
        print(f"  {status} {d['name']}/: {d['size_kb']} KB ({d['file_count']} 文件)")


def action_status():
    """输出记忆系统状态摘要（供 cron 报告用）"""
    index = load_index()
    dirty = get_dirty_files()
    domains = scan_l1_domains()
    
    over_limit = [d for d in domains if d["size_kb"] > L1_MAX_KB]
    
    print("┌─────────────────────────────────────┐")
    print("│  Hermes 记忆系统状态                  │")
    print("├─────────────────────────────────────┤")
    print(f"│  索引版本: v{index.get('version')}                       │")
    print(f"│  待整理: {len(dirty)} 条                         │")
    print(f"│  总文件: {sum(d['file_count'] for d in domains)} 个                         │")
    if over_limit:
        print(f"│  ⚠️ 超限域: {len(over_limit)} 个                    │")
    else:
        print(f"│  ✅ 所有域正常                       │")
    print("└─────────────────────────────────────┘")


def action_rebuild():
    """重建索引：扫描所有文件，重新生成 index"""
    print("=== Memory Supervisor: Rebuild ===")
    
    index = _create_default_index()
    domains = scan_l1_domains()
    
    for d in domains:
        domain_path = HERMES_MEMORIES / d["name"]
        index["nodes"][d["name"]] = {
            "path": d["path"],
            "size_kb": d["size_kb"],
            "last_access": datetime.utcnow().isoformat() + "Z",
            "access_count": 0,
            "status": "active",
            "file_count": d["file_count"],
            "refresh_count": 0
        }
        
        # 扫描 L2 文件
        for f in domain_path.rglob("*.md"):
            age = get_file_age_days(f)
            index["nodes"][d["name"]].setdefault("files", []).append({
                "name": f.name,
                "size_kb": round(f.stat().st_size / 1024, 2),
                "last_modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "age_days": age
            })
    
    total_files = sum(d["file_count"] for d in domains)
    total_size = sum(d["size_kb"] for d in domains)
    
    index["nodes"]["skills"] = index["nodes"].get("skills") or {
        "path": "skills/", "size_kb": 0, "status": "active"
    }
    index["nodes"]["user"] = index["nodes"].get("user") or {
        "path": "user/", "size_kb": 0, "status": "active"
    }
    index["nodes"]["projects"] = index["nodes"].get("projects") or {
        "path": "projects/", "size_kb": 0, "status": "active"
    }
    index["nodes"]["topics"] = index["nodes"].get("topics") or {
        "path": "topics/", "size_kb": 0, "status": "active"
    }
    index["nodes"]["preferences"] = index["nodes"].get("preferences") or {
        "path": "preferences/", "size_kb": 0, "status": "active"
    }
    index["nodes"]["errors"] = index["nodes"].get("errors") or {
        "path": "errors/", "size_kb": 0, "status": "active"
    }
    index["nodes"]["workflows"] = index["nodes"].get("workflows") or {
        "path": "workflows/", "size_kb": 0, "status": "active"
    }
    
    index["stats"] = {
        "total_nodes": len(domains),
        "total_size_kb": total_size,
        "total_files": total_files,
        "pending_compression": len(get_dirty_files()),
        "last_compact": None
    }
    index["last_rebuild"] = datetime.utcnow().isoformat() + "Z"
    
    save_index(index)
    print(f"✅ 索引重建完成: {len(domains)} 域, {total_files} 文件, {total_size} KB")


def action_process():
    """处理 dirty queue 中的所有待整理记忆"""
    print("=== Memory Supervisor: Process ===")
    dirty = get_dirty_files()
    
    if not dirty:
        print("Dirty queue 为空，无需处理")
        return
    
    print(f"发现 {len(dirty)} 条待整理记忆")
    
    # 这里会调用 Compression Agent
    # 暂时标记为待处理，打印报告
    for f in dirty:
        print(f"  📝 {f.name}")
        # TODO: 调用 compression_agent.compress(f)
    
    print("\n⚠️ Compression Agent 尚未集成，dirty 文件暂保留在 .dirty/ 目录")


# ============ 主入口 ============

if __name__ == "__main__":
    if len(sys.argv) < 2:
        action_check()
        sys.exit(0)
    
    action = sys.argv[1]
    
    if action == "check":
        action_check()
    elif action == "status":
        action_status()
    elif action == "rebuild":
        action_rebuild()
    elif action == "process":
        action_process()
    else:
        print(f"未知 action: {action}")
        print("可用: check, status, rebuild, process")
        sys.exit(1)
