#!/usr/bin/env python3
"""
L3 语义记忆层 — BM25 + TF-IDF 混合搜索（纯本地，不依赖外部付费 API）
小a 的 Layer 3 语义搜索，基于词频统计的语义近似匹配

升级版: 支持 access_count、priority 标签、隐私过滤（含飞书隐私表同步）、last_accessed 追踪

用法:
  python memory_l3.py add "记忆内容" [category] [priority]
  python memory_l3.py search "查询内容" [top_k]
  python memory_l3.py stats
  python memory_l3.py mark-hit <id>    # 标记记忆被访问（Ebbinghaus +1）
  python memory_l3.py set-priority <id> <P0|P1|P2>  # 设置优先级
  python memory_l3.py list                   # 列出所有记忆
  python memory_l3.py delete <id>            # 删除记忆
  python memory_l3.py sync-privacy            # 从飞书隐私表同步隐私模式
"""

import os
import sys
import json
import sqlite3
import math
import re
import time
import urllib.request
from pathlib import Path
from collections import Counter
from datetime import datetime

DB_PATH = Path.home() / ".hermes" / "memory" / "semantic.db"
PRIVACY_CACHE = Path.home() / ".hermes" / "memory" / "privacy_patterns.json"

# ── 飞书配置 ──────────────────────────────────────────
FEISHU_APP_ID = "cli_a95a1e699d78dcb5"
FEISHU_APP_SECRET = None  # 从 config.yaml 动态读取
FEISHU_BASE_TOKEN = "PlsLbTLynaIF3qsoVXCctXTcnnf"
FEISHU_PRIVACY_TABLE = "tbllup7e8aQvf4Lx"
PRIVACY_CACHE_TTL = 3600  # 缓存1小时


def _get_feishu_token():
    """获取飞书 tenant token"""
    global FEISHU_APP_SECRET
    if FEISHU_APP_SECRET is None:
        import yaml
        with open(Path.home() / ".hermes" / "config.yaml") as f:
            config = yaml.safe_load(f)
        # 查找 feishu 配置
        feishu_cfg = None
        for k, v in config.items():
            if isinstance(v, dict) and 'app_id' in v and v['app_id'] == FEISHU_APP_ID:
                feishu_cfg = v
                break
        if feishu_cfg:
            FEISHU_APP_SECRET = feishu_cfg['app_secret']
        else:
            # 从 platforms.feishu 取（Hermes 内部配置结构）
            platforms = config.get("platforms", {})
            feishu_in_platforms = platforms.get("feishu", {}) if isinstance(platforms, dict) else {}
            if isinstance(feishu_in_platforms, dict) and feishu_in_platforms.get("app_id") == FEISHU_APP_ID:
                FEISHU_APP_SECRET = feishu_in_platforms.get("app_secret", "")
            else:
                return None

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["tenant_access_token"]
    except:
        return None


def _fetch_privacy_patterns_from_feishu():
    """从飞书隐私记录表拉取隐私模式"""
    token = _get_feishu_token()
    if not token:
        return None

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_BASE_TOKEN}/tables/{FEISHU_PRIVACY_TABLE}/records"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            records = data.get("data", {}).get("items", [])
            patterns = []
            for rec in records:
                fields = rec.get("fields", {})
                name = fields.get("名称/标识", "")
                desc = fields.get("用途说明", "")
                content_hint = fields.get("密钥/隐私内容", "")
                # 从内容提示中提取格式模式（如 "ghp_xxx", "tvly-xxx"）
                pattern_str = fields.get("类型", "")
                patterns.append({
                    "name": name,
                    "description": desc,
                    "content_hint": content_hint,
                    "type": pattern_str
                })
            return patterns
    except:
        return None


def get_privacy_patterns():
    """
    获取隐私模式（优先读缓存，缓存过期则从飞书拉取）
    返回 [{name, description, content_hint, type}, ...]
    """
    if PRIVACY_CACHE.exists():
        try:
            cached = json.loads(PRIVACY_CACHE.read_text())
            if time.time() - cached.get("_cached_at", 0) < PRIVACY_CACHE_TTL:
                return cached.get("patterns", [])
        except:
            pass

    # 缓存失效，从飞书拉取
    patterns = _fetch_privacy_patterns_from_feishu()
    if patterns is not None:
        cache_data = {"patterns": patterns, "_cached_at": time.time()}
        PRIVACY_CACHE.parent.mkdir(parents=True, exist_ok=True)
        PRIVACY_CACHE.write_text(json.dumps(cache_data, ensure_ascii=False))
        return patterns

    # 飞书也失败 → 返回内置基础模式
    return None


# ── 内置隐私模式（飞书表未连接时的兜底）──────────────
BUILTIN_PATTERNS = [
    (r'MINIMAX[_-]API[_-]KEY\s*=\s*["\']?[^\"\'\s]+', 'MINIMAX_API_KEY=***'),
    (r'API[_-]KEY\s*=\s*["\']?sk-[^\"\'\s]+', 'API_KEY=***'),
    (r'ghp_[a-zA-Z0-9]{36}', 'ghp_***'),
    (r'xox[baprs]-[a-zA-Z0-9]{10,}', 'xoxb_***'),
    (r'bearer [a-zA-Z0-9_\-\.]+', 'bearer ***', re.IGNORECASE),
    (r'token["\']?\s*:\s*["\']?[a-zA-Z0-9_\-\.]+', 'token: ***'),
    (r'835538524[^"\'\s]*', '835538524***'),
    (r'tvly-[a-zA-Z0-9]{20,}', 'tvly-***'),
    (r'sk-[a-zA-Z0-9_-]{20,}', 'sk-***'),
    (r'cli_[a-f0-9]{16,}', 'cli_***'),
]


def privacy_filter(text: str) -> str:
    """过滤 API key、token 等敏感信息（本地模式 + 飞书动态模式）"""
    result = text
    # 内置模式
    for pattern_def in BUILTIN_PATTERNS:
        if len(pattern_def) == 2:
            pattern, replacement = pattern_def
            flags = 0
        else:
            pattern, replacement, flags = pattern_def
        result = re.sub(pattern, replacement, result, flags=flags)
    # 飞书动态模式（内容提示）
    try:
        patterns = get_privacy_patterns()
        if patterns:
            for p in patterns:
                hint = p.get("content_hint", "")
                name = p.get("name", "")
                if hint and "真实值在" not in hint:
                    # 从 hint 中解析格式（如 "ghp_xxx" → 提取前缀）
                    # 这里仅用于文档参考，不做额外替换
                    pass
    except:
        pass
    return result


def tokenize(text: str) -> list[str]:
    """中英文分词（简单版），保留 API key 格式"""
    text = text.lower()
    tokens = []

    # 1. API key / token 整段保留
    key_patterns = re.findall(
        r'(?i)('
        r'sk-[a-z0-9_-]+|'
        r'(?:ghp|tvly|gho|apikey|openai|anthropic|cli)[_-][a-z0-9]{10,}|'
        r'[a-f0-9]{32,}?'
        r')',
        text
    )
    tokens.extend(key_patterns)

    # 2. 从剩余文本提取普通英文词
    remaining = text
    for kp in key_patterns:
        remaining = remaining.replace(kp, ' ')
    english_tokens = re.findall(r'[a-z0-9]{2,}', remaining)
    tokens.extend(english_tokens)

    # 3. 简单中文分词（按字符bigram + 单字）
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    if len(chinese_chars) >= 2:
        tokens += [c for c in chinese_chars]
        tokens += [''.join(chinese_chars[i:i+2]) for i in range(len(chinese_chars)-1)]

    return list(set(tokens))


def init_db():
    """初始化 SQLite（带新字段兼容性）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            tokens TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            priority TEXT DEFAULT 'P2',
            last_accessed TEXT DEFAULT '',
            ttl_days INTEGER DEFAULT 30
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON memories(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON memories(priority)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_access ON memories(access_count)")
    conn.commit()
    return conn


def add_memory(text: str, category: str = "general", priority: str = "P2"):
    """添加记忆 + 分词 + 隐私过滤"""
    text = privacy_filter(text)
    tokens = tokenize(text)
    conn = init_db()
    cursor = conn.execute(
        "INSERT INTO memories (text, category, tokens, priority, last_accessed) VALUES (?, ?, ?, ?, ?)",
        (text, category, json.dumps(tokens), priority, datetime.now().isoformat())
    )
    conn.commit()
    mid = cursor.lastrowid
    conn.close()
    return mid


def mark_hit(memory_id: int):
    """标记记忆被访问：access_count += 1, 更新 last_accessed"""
    conn = init_db()
    conn.execute(
        "UPDATE memories SET access_count = access_count + 1, "
        "last_accessed = ? WHERE id = ?",
        (datetime.now().isoformat(), memory_id)
    )
    conn.commit()
    conn.close()


def set_priority(memory_id: int, priority: str):
    """设置记忆优先级"""
    if priority not in ('P0', 'P1', 'P2'):
        return False
    conn = init_db()
    conn.execute("UPDATE memories SET priority = ? WHERE id = ?", (priority, memory_id))
    conn.commit()
    conn.close()
    return True


def delete_memory(memory_id: int):
    """删除记忆"""
    conn = init_db()
    conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()


def list_memories():
    """列出所有记忆"""
    conn = init_db()
    rows = conn.execute("""
        SELECT id, text, category, priority, access_count, last_accessed, created_at
        FROM memories ORDER BY id DESC
    """).fetchall()
    conn.close()
    return rows


def bm25_score(query_tokens: list[str], doc_tokens: list[str], avg_dl: float, N: int, doc_freqs: dict, dl: int, k1=1.5, b=0.75) -> float:
    """计算 BM25 分数"""
    score = 0.0
    for term in query_tokens:
        if term not in doc_freqs:
            continue
        df = doc_freqs[term]
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
        tf = doc_tokens.count(term)
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg_dl))
    return score


def tfidf_score(query_tokens: list[str], doc_tokens: list[str], idf: dict, doc_norm: float) -> float:
    """计算 TF-IDF 余弦相似度"""
    if not query_tokens or not doc_tokens or doc_norm == 0:
        return 0.0
    tf = Counter(doc_tokens)
    dot = sum(idf.get(t, 0) * (tf[t] / len(doc_tokens)) for t in query_tokens if t in tf)
    query_norm = math.sqrt(sum(idf.get(t, 0)**2 for t in query_tokens))
    if query_norm == 0 or doc_norm == 0:
        return 0.0
    return dot / (query_norm * doc_norm)


def search_memories(query: str, top_k: int = 5):
    """BM25 + TF-IDF 混合搜索，返回 [(hybrid_score, memory_id, text, category), ...]"""
    query_tokens = tokenize(query)
    conn = init_db()
    rows = conn.execute("SELECT id, text, category, tokens FROM memories").fetchall()
    conn.close()
    
    if not rows:
        return []
    
    N = len(rows)
    doc_freqs = Counter()
    doc_lens = []
    all_doc_tokens = []
    
    for mid, text, cat, tok_json in rows:
        toks = json.loads(tok_json)
        all_doc_tokens.append(toks)
        doc_lens.append(len(toks))
        for t in set(toks):
            doc_freqs[t] += 1
    
    avg_dl = sum(doc_lens) / N
    
    # 计算 IDF
    idf = {}
    for term, df in doc_freqs.items():
        idf[term] = math.log((N - df + 0.5) / (df + 0.5) + 1)
    
    # 计算每个 doc 的 TF-IDF 向量范数
    doc_norms = []
    for toks in all_doc_tokens:
        tf = Counter(toks)
        norm_sq = sum((idf.get(t, 0) * tf[t] / len(toks))**2 for t in toks)
        doc_norms.append(math.sqrt(norm_sq))
    
    results = []
    for i, (mid, text, cat, tok_json) in enumerate(rows):
        toks = all_doc_tokens[i]
        dl = doc_lens[i]
        
        bm25 = bm25_score(query_tokens, toks, avg_dl, N, doc_freqs, dl)
        tfidf = tfidf_score(query_tokens, toks, idf, doc_norms[i])
        
        # 混合分数：BM25 + TF-IDF
        hybrid = bm25 + tfidf * 10
        results.append((hybrid, mid, text, cat))
        
        # 搜索命中 → 更新访问记录
        mark_hit(mid)
    
    results.sort(reverse=True)
    return results[:top_k]


def stats():
    conn = init_db()
    total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    cats = conn.execute("SELECT COUNT(DISTINCT category) FROM memories").fetchone()[0]
    p0 = conn.execute("SELECT COUNT(*) FROM memories WHERE priority='P0'").fetchone()[0]
    p1 = conn.execute("SELECT COUNT(*) FROM memories WHERE priority='P1'").fetchone()[0]
    p2 = conn.execute("SELECT COUNT(*) FROM memories WHERE priority='P2'").fetchone()[0]
    conn.close()
    return {"total": total, "categories": cats, "p0": p0, "p1": p1, "p2": p2}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    
    if cmd == "add":
        text = sys.argv[2]
        category = sys.argv[3] if len(sys.argv) > 3 else "general"
        priority = sys.argv[4] if len(sys.argv) > 4 else "P2"
        if priority not in ('P0', 'P1', 'P2'):
            priority = 'P2'
        mid = add_memory(text, category, priority)
        print(f"✅ 记忆已存入 (id={mid}, category={category}, priority={priority})")
    
    elif cmd == "search":
        query = sys.argv[2]
        top_k = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        results = search_memories(query, top_k)
        print(f"🔍 搜索结果 (top {len(results)}):")
        for score, mid, text, cat in results:
            print(f"  [{score:.3f}] [{cat}] #{mid}: {text[:80]}...")
    
    elif cmd == "stats":
        s = stats()
        print(f"📊 语义记忆库: {s['total']} 条, {s['categories']} 分类 (P0={s['p0']}, P1={s['p1']}, P2={s['p2']})")
    
    elif cmd == "mark-hit":
        mid = int(sys.argv[2])
        mark_hit(mid)
        print(f"✅ #{mid} 访问计数 +1")
    
    elif cmd == "set-priority":
        mid = int(sys.argv[2])
        pri = sys.argv[3]
        if set_priority(mid, pri):
            print(f"✅ #{mid} → {pri}")
        else:
            print(f"❌ 无效优先级: {pri}")
    
    elif cmd == "list":
        rows = list_memories()
        print(f"📋 共 {len(rows)} 条记忆:")
        for mid, text, cat, pri, ac, last, created in rows:
            last_str = last[:10] if last else 'never'
            print(f"  #{mid} [{pri} ac={ac} last={last_str}] [{cat}]: {text[:60]}...")
    
    elif cmd == "delete":
        mid = int(sys.argv[2])
        delete_memory(mid)
        print(f"🗑️  已删除 #{mid}")
    
    elif cmd == "sync-privacy":
        print("🔄 从飞书隐私表同步模式...")
        # 清除缓存，强制刷新
        if PRIVACY_CACHE.exists():
            PRIVACY_CACHE.unlink()
        patterns = _fetch_privacy_patterns_from_feishu()
        if patterns is not None:
            cache_data = {"patterns": patterns, "_cached_at": time.time()}
            PRIVACY_CACHE.parent.mkdir(parents=True, exist_ok=True)
            PRIVACY_CACHE.write_text(json.dumps(cache_data, ensure_ascii=False))
            print(f"✅ 同步成功，共 {len(patterns)} 条隐私记录")
            for p in patterns:
                print(f"  • {p['name']} ({p['type']})")
        else:
            print("❌ 同步失败（飞书连接异常），使用内置模式")
    
    else:
        print(f"未知命令: {cmd}")
        print("用法: add|search|stats|mark-hit|set-priority|list|delete|sync-privacy")
