---
name: data-pipelines
description: 数据处理与分析技能 — SQL 建表改表、CSV 数据分析、数据库迁移脚本、数据导入导出、个人知识数据查询。用标准库完成，不依赖外部 heavy 库。
version: 1.0.0
author: Hermes Agent
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [data, database, sql, csv, migration, analysis]
    related_skills: [knowledge-graph, memory-store]
    cron_schedule: "0 */2 * * *"
---

# Data Pipelines Skill

## 核心能力

用纯 Python stdlib（sqlite3 / csv / json / pathlib）处理所有数据任务，无需额外安装任何包。

---

## 场景一：SQLite 操作

### 创建表

```python
import sqlite3, sys

conn = sqlite3.connect("mydata.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    email       TEXT    UNIQUE,
    created_at  TEXT    DEFAULT (date('now')),
    notes       TEXT
)
""")
conn.commit()
conn.close()
```

### 查询数据

```python
import sqlite3

conn = sqlite3.connect("mydata.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
SELECT id, name, email, date(created_at) as dt, notes
FROM users
WHERE name LIKE ?
ORDER BY created_at DESC
LIMIT 20
""", (f"%{keyword}%",))

for row in cur.fetchall():
    print(dict(row))
```

### 改表结构（migration）

```python
def migrate_add_column(db_path, table, column, dtype="TEXT"):
    """生成安全的 ALTER TABLE 迁移（SQLite 限制：只能 ADD COLUMN）"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {dtype}")
        conn.commit()
        print(f"✅ Added {column} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print(f"⚠️  Column {column} already exists")
        else:
            raise
    finally:
        conn.close()

# 回滚（SQLite 不支持 DROP COLUMN，标记为 deprecated 即可）
def deprecate_column(db_path, table, column):
    """通过重命名表 + 重建来安全删除列（数据会丢失，慎用）"""
    pass  # 不推荐在 SQLite 中删除列，记录到 migration_log 表即可
```

### 事务管理

```python
def safe_update(conn, sql, params):
    """带回滚的更新操作"""
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")  # 获取写锁
    try:
        cur.execute(sql, params)
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
```

---

## 场景二：Hermes 内部数据查询

Hermes 的数据都在 SQLite 里，可以直接查：

```python
import sqlite3
from pathlib import Path

HERMES = Path.home() / ".hermes"

# 查询记忆数据
def query_memory(keyword, limit=10):
    conn = sqlite3.connect(HERMES / "memory/memory.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT block_id, session_id, summary, compression_ratio
        FROM memory_blocks
        WHERE summary LIKE ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (f"%{keyword}%", limit))
    return cur.fetchall()

# 查询 SkillTree 健康度
def query_skill_health():
    conn = sqlite3.connect(HERMES / "evolution_logs/skill_tree/skill_tree.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT skill_name, invocation_count, success_rate, avg_latency_ms
        FROM skill_health
        ORDER BY invocation_count DESC
        LIMIT 20
    """)
    return cur.fetchall()

# 查询 KnowledgeGraph 实体
def query_entities(entity_type=None, limit=20):
    kb_path = HERMES / "knowledge/knowledge.db"
    if not kb_path.exists():
        return []
    conn = sqlite3.connect(kb_path)
    cur = conn.cursor()
    if entity_type:
        cur.execute("""
            SELECT entity_name, entity_type, properties
            FROM entities
            WHERE entity_type = ?
            LIMIT ?
        """, (entity_type, limit))
    else:
        cur.execute("SELECT entity_name, entity_type FROM entities LIMIT ?", (limit,))
    return cur.fetchall()
```

---

## 场景三：CSV 数据分析

### 基础分析

```python
import csv
from collections import Counter

def analyze_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            return {"error": "empty file"}

        headers = rows[0].keys()
        col_stats = {}
        for col in headers:
            values = [r[col] for r in rows if r[col]]
            col_stats[col] = {
                "count": len(values),
                "unique": len(set(values)),
                "sample": values[:3],
            }

        return {
            "rows": len(rows),
            "columns": len(headers),
            "col_stats": col_stats,
        }
```

### 导出为 SQL 表

```python
import csv, sqlite3, uuid

def csv_to_sqlite(csv_path, db_path, table_name):
    """把 CSV 文件导入到 SQLite"""
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 推断列类型（只支持 TEXT / INTEGER / REAL）
    sample = rows[0] if rows else {}
    col_defs = []
    for col, val in sample.items():
        safe_col = col.replace(" ", "_").replace("-", "_")
        if val.isdigit():
            col_defs.append(f'"{safe_col}" INTEGER')
        elif val.replace(".", "").replace("-", "").isdigit():
            col_defs.append(f'"{safe_col}" REAL')
        else:
            col_defs.append(f'"{safe_col}" TEXT')

    cur.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(col_defs)})')

    for row in rows:
        placeholders = ", ".join(["?"] * len(row))
        cur.execute(f'INSERT INTO "{table_name}" VALUES ({placeholders})', list(row.values()))

    conn.commit()
    conn.close()
    return len(rows)
```

---

## 场景四：数据迁移脚本模板

```python
"""
Migration: add_project_tracker
用途：给 knowledge 表添加项目追踪字段
日期：2026-04-19
回滚：删除字段（数据丢失）
"""
import sqlite3
from pathlib import Path

HERMES = Path.home() / ".hermes"
DB = HERMES / "knowledge/knowledge.db"

def up():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        ALTER TABLE entities
        ADD COLUMN project_status TEXT DEFAULT 'exploring'
    """)
    cur.execute("""
        ALTER TABLE entities
        ADD COLUMN last_researched TEXT
    """)
    conn.commit()
    conn.close()
    print("✅ Migration up: added project tracker columns")

def down():
    # SQLite 不支持 DROP COLUMN，标记即可
    print("⚠️  SQLite 不支持 DROP COLUMN，建议记录并重建表")
    print("✅ Migration down: no-op (data preserved)")

if __name__ == "__main__":
    import sys
    up() if "up" in sys.argv else down()
```

---

## 场景五：数据备份

```python
import sqlite3, shutil, json
from pathlib import Path
from datetime import datetime

HERMES = Path.home() / ".hermes"
BACKUP = HERMES / "backups"

def backup_knowledge():
    src = HERMES / "knowledge/knowledge.db"
    if not src.exists():
        return None
    BACKUP.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP / f"knowledge_{ts}.db"
    shutil.copy2(src, dst)

    # 同时导出 schema
    conn = sqlite3.connect(src)
    cur = conn.cursor()
    schema = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table'"
    ).fetchall()
    (BACKUP / f"schema_{ts}.sql").write_text(
        "\n".join(s for s, in schema if s)
    )
    conn.close()
    return dst

def list_backups():
    if not BACKUP.exists():
        return []
    return sorted(BACKUP.glob("knowledge_*.db"), reverse=True)
```

---

## 验证命令

```bash
# 检查 sqlite3 可用
python3 -c "import sqlite3; print('sqlite3 OK')"

# 测试 Hermes 内部查询
python3 -c "
import sqlite3
from pathlib import Path
db = Path.home() / '.hermes/memory/memory.db'
if db.exists():
    conn = sqlite3.connect(db)
    count = conn.execute('SELECT COUNT(*) FROM memory_blocks').fetchone()[0]
    print(f'Memory blocks: {count}')
    conn.close()
else:
    print('No memory db yet')
"
```

---

## 注意事项

- **SQLite 限制**：不支持 DROP COLUMN、ALTER TABLE ADD CONSTRAINT，只能 ADD COLUMN
- **编码**：所有文件读写默认用 `utf-8`
- **Hermes 数据**：KnowledgeGraph 和 MemoryStore 都在 `~/.hermes/` 下，直接连 SQLite 查即可
- **迁移原则**：所有表结构变更都要记录 migration 文件，附回滚方案（哪怕是 no-op）
- **不要装 pandas**：用标准库完成所有操作，Termux 上装 pandas 费时且容易失败
