# Kanban DB Schema Diagnostic

**Date:** 2026-05-08

## Quick Check

```bash
cd /data/data/com.termux/files/home/hermes-agent && venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('/data/data/com.termux/files/home/.hermes/kanban.db')
cur = conn.cursor()
cur.execute('PRAGMA table_info(tasks)')
cols = {r[1] for r in cur.fetchall()}
print('consecutive_failures:', 'consecutive_failures' in cols)
print('max_retries:', 'max_retries' in cols)
print('spawn_failures:', 'spawn_failures' in cols)
print('total tasks:', cur.execute('SELECT COUNT(*) FROM tasks').fetchone()[0])
"
```

Expected output after migration is complete:
```
consecutive_failures: True
max_retries: True
spawn_failures: False
total tasks: 0  (or actual count)
```

## Kanban DB Location

- Primary: `/data/data/com.termux/files/home/.hermes/kanban.db`
- Old snapshots: `/data/data/com.termux/files/home/.hermes/state-snapshots/*/state.db`
- Boards subdirectory: `/data/data/com.termux/files/home/.hermes/kanban/` (not present in this setup)

## Schema Init: Two-Phase Pattern

Kanban DB init uses two phases:

1. **`SCHEMA_SQL`** — runs `CREATE TABLE IF NOT EXISTS tasks (...)` which includes ALL current columns including optional ones like `max_retries`, `consecutive_failures`, `skills`, etc.
2. **`_migrate_add_optional_columns()`** — tries to `ALTER TABLE tasks ADD COLUMN` for each optional column. On a freshly-created DB (where SCHEMA_SQL already created the table with all columns), every ADD fails with `sqlite3.OperationalError: duplicate column name`.

The `add_col()` helper makes phase 2 idempotent — it catches "duplicate column name" and ignores it.

## `spawn_failures` → `consecutive_failures` Migration (Legacy)

Old DBs may have `spawn_failures` which was renamed to `consecutive_failures`. The migration uses ADD-first-then-copy (not RENAME) to avoid parsing issues with very old schema:

```python
if "consecutive_failures" not in cols:
    add_col("ALTER TABLE tasks ADD COLUMN consecutive_failures INTEGER NOT NULL DEFAULT 0")
    if "spawn_failures" in cols:
        conn.execute("UPDATE tasks SET consecutive_failures = COALESCE(spawn_failures, 0)")
```

## `duplicate column name: max_retries` — The Real Error

The actual startup error seen is:

```
sqlite3.OperationalError: duplicate column name: max_retries
```

**Root cause:** `SCHEMA_SQL` includes `max_retries` in its `CREATE TABLE IF NOT EXISTS`. On an upgraded DB, SCHEMA_SQL creates the full table with all columns. Then `_migrate_add_optional_columns` tries to `ADD COLUMN max_retries` — but it already exists, so it throws.

**Fix applied:** Each `ALTER TABLE ADD COLUMN` in `hermes_cli/kanban_db.py` now uses `add_col()` which catches and ignores `duplicate column name`. This makes migration fully idempotent regardless of which phase created the column.

**Verify fix is applied:**
```bash
grep -n "def add_col" /data/data/com.termux/files/home/hermes-agent/hermes_cli/kanban_db.py
# Should show the helper function definition
```

## Dispatcher Tick Is Silent When Idle

A healthy kanban tick produces **no log entry** when there are no tasks to spawn. The dispatcher loop only logs when:
- `tick failed` → error occurred
- Something was actually spawned/reclaimed/crashed

Absence of "tick failed" = dispatcher is working correctly. Do NOT look for a "tick succeeded" message.

## Single vs Recurring Errors

A single `tick failed` at gateway startup = benign (DB already migrated, migration code ran and failed the ADD but was caught, dispatcher recovered). The fix is to make the migration idempotent.

Recurring errors on every tick = investigate with the quick check above and verify `add_col()` is present in `kanban_db.py`.
