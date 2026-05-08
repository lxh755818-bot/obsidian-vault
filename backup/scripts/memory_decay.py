#!/usr/bin/env python3
"""
semantic_memory_decay.py
置信度衰减脚本 — Cass 规则学习机制在 semantic.db 的实现

运行方式:
  python3 ~/.hermes/scripts/memory_decay.py

建议 Cron: 每日 22:00 执行
  hermes cron create "0 22 * * *" \
    --prompt "执行记忆衰减: python3 ~/.hermes/scripts/memory_decay.py" \
    --name "memory-decay" \
    --deliver local
"""

import sqlite3
import sys
from datetime import datetime, timezone

DB = '/data/data/com.termux/files/home/.hermes/memory/semantic.db'

def get_confidence(id_, access_count, priority, last_accessed_str):
    """计算单条记忆的置信度得分"""
    days_old = (datetime.now() - datetime.fromisoformat(last_accessed_str)).days
    
    # 访问频率因子（访问越多越稳定，上限2x）
    freq_factor = min(access_count / 5.0, 2.0)
    
    # 时间衰减（P0慢衰减，P2快衰减）
    if priority == 'P0':
        decay = max(0.5, 1.0 - days_old * 0.01)
    elif priority == 'P1':
        decay = max(0.3, 1.0 - days_old * 0.03)
    else:
        decay = max(0.1, 1.0 - days_old * 0.05)
    
    return round(freq_factor * decay, 3)


def run_decay(verbose=True):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM memories ORDER BY priority, id")
    rows = cur.fetchall()
    
    if not rows:
        if verbose:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] semantic.db 为空，跳过")
        return
    
    acted = 0
    for row in rows:
        id_, text, category, tokens, created, access, priority, last_acc, ttl = row
        days_ago = (datetime.now() - datetime.fromisoformat(last_acc)).days
        conf = get_confidence(id_, access, priority, last_acc)
        
        action = None
        
        # P0 降 P1: 14天未访问
        if priority == 'P0' and days_ago > 14:
            cur.execute("UPDATE memories SET priority='P1' WHERE id=?", (id_,))
            action = f"P0→P1 (已{days_ago}天未访问)"
        
        # P1 降 P2: 30天未访问
        elif priority == 'P1' and days_ago > 30:
            cur.execute("UPDATE memories SET priority='P2' WHERE id=?", (id_,))
            action = f"P1→P2 (已{days_ago}天未访问)"
        
        # P2 归档: 60天未访问
        elif priority == 'P2' and days_ago > 60:
            cur.execute("""
                INSERT INTO memories_archive(id, text, category, tokens, created_at)
                VALUES(?,?,?,?,?)
            """, (id_, text, category, tokens, created))
            cur.execute("DELETE FROM memories WHERE id=?", (id_,))
            action = f"归档至archive (已{days_ago}天)"
        
        # 新记忆首次访问: access_count=0 → 设为1（避免0置信度）
        elif access == 0 and days_ago > 3:
            cur.execute(
                "UPDATE memories SET access_count=1, last_accessed=datetime('now') WHERE id=?",
                (id_,)
            )
            action = "首次激活 (access_count: 0→1)"
        
        if verbose:
            snippet = text[:35].replace('\n', ' ') if text else '(empty)'
            print(f"  [id={id_:2d}] {priority} acc={access} {days_ago:2d}d conf={conf:.3f} | {action or '保持'} | {snippet}...")
        
        if action:
            acted += 1
    
    conn.commit()
    
    cur.execute("SELECT COUNT(*) FROM memories")
    active = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM memories_archive")
    archived = cur.fetchone()[0]
    
    if verbose:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 完成 | 活跃 {active} | 已归档 {archived} | 本次动作 {acted}")
    
    conn.close()
    return acted


if __name__ == '__main__':
    verbose = '-q' not in sys.argv and '--quiet' not in sys.argv
    run_decay(verbose=verbose)
