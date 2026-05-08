#!/usr/bin/env python3
"""
L3 语义记忆层 — 基于 MiniMax Embedding API + SQLite
小a 的 Layer 3 语义搜索，补充刘大虾的 MemPalace ChromaDB 功能

用法:
  python memory_l3_semantic.py add "记忆内容" [category]
  python memory_l3_semantic.py search "查询内容" [top_k]
  python memory_l3_semantic.py stats
"""

import os
import sys
import json
import sqlite3
import math
import base64
import urllib.request
from pathlib import Path

DB_PATH = Path.home() / ".hermes" / "memory" / "semantic.db"
CONFIG_PATH = Path.home() / ".hermes" / ".env"

# MiniMax Embedding API
EMBED_URL = "https://api.minimaxi.com/v1/embeddings"
MODEL_NAME = "emb-01"

def get_api_key():
    """从 .env 读取 MINIMAX_CN_API_KEY"""
    with open(CONFIG_PATH) as f:
        for line in f:
            if line.startswith("MINIMAX_CN_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise ValueError("MINIMAX_CN_API_KEY not found in ~/.hermes/.env")

def get_embedding(text: str, api_key: str) -> list[float]:
    """调用 MiniMax Embedding API 获取文本向量"""
    payload = json.dumps({"model": MODEL_NAME, "text": text[:8192]}).encode()
    req = urllib.request.Request(
        EMBED_URL,
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        # 提取 embedding 向量
        return result["data"]["vectors"]

def cosine_sim(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def init_db():
    """初始化 SQLite 数据库"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            embedding BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON memories(category)")
    conn.commit()
    return conn

def add_memory(text: str, category: str = "general", api_key: str = None):
    """添加记忆 + 自动计算 embedding"""
    if api_key is None:
        api_key = get_api_key()
    
    embedding = get_embedding(text, api_key)
    # 存入 SQLite（embedding 转 base64 字符串）
    emb_b64 = base64.b64encode(json.dumps(embedding).encode()).decode()
    
    conn = init_db()
    cursor = conn.execute(
        "INSERT INTO memories (text, category, embedding) VALUES (?, ?, ?)",
        (text, category, emb_b64)
    )
    conn.commit()
    mid = cursor.lastrowid
    conn.close()
    return mid

def search_memories(query: str, top_k: int = 5, api_key: str = None):
    """语义搜索记忆"""
    if api_key is None:
        api_key = get_api_key()
    
    query_emb = get_embedding(query, api_key)
    
    conn = init_db()
    rows = conn.execute("SELECT id, text, category, embedding FROM memories").fetchall()
    conn.close()
    
    results = []
    for mid, text, category, emb_b64 in rows:
        emb = json.loads(base64.b64decode(emb_b64).decode())
        score = cosine_sim(query_emb, emb)
        results.append((score, mid, text, category))
    
    results.sort(reverse=True)
    return results[:top_k]

def stats():
    """查看统计"""
    conn = init_db()
    row = conn.execute("SELECT COUNT(*), COUNT(DISTINCT category) FROM memories").fetchone()
    conn.close()
    return {"total": row[0], "categories": row[1]}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    
    if cmd == "add":
        text = sys.argv[2]
        category = sys.argv[3] if len(sys.argv) > 3 else "general"
        mid = add_memory(text, category)
        print(f"✅ 记忆已存入 (id={mid}, category={category})")
    
    elif cmd == "search":
        query = sys.argv[2]
        top_k = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        results = search_memories(query, top_k)
        print(f"🔍 搜索结果 (top {len(results)}):")
        for score, mid, text, category in results:
            print(f"  [{score:.3f}] [{category}] #{mid}: {text[:80]}...")
    
    elif cmd == "stats":
        s = stats()
        print(f"📊 语义记忆库: {s['total']} 条记忆, {s['categories']} 个分类")
    
    else:
        print(f"未知命令: {cmd}")
        print("用法: add|search|stats")
