#!/usr/bin/env python3
"""RSS Feeds 抓取脚本
抓取配置的 RSS 源，提取新条目，保存到 learnings/
"""

import urllib.request
import feedparser
import json
import yaml
import re
from datetime import datetime, timedelta
from pathlib import Path

FEEDS_CONFIG = "/data/data/com.termux/files/home/.hermes/evolution_logs/feeds.yaml"
LEARNINGS_DIR = Path("/data/data/com.termux/files/home/.hermes/evolution_logs/learnings")
STATE_FILE = LEARNINGS_DIR / "state.json"

def load_feeds():
    with open(FEEDS_CONFIG) as f:
        config = yaml.safe_load(f)
    return [f for f in config['feeds'] if f.get('enabled', True)]

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_fetch": {}, "seen_urls": set()}

def save_state(state):
    # seen_urls can be large, save separately
    seen = state.pop("seen_urls", set())
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def fetch_feed(feed_config):
    """抓取单个 RSS 源，返回新条目"""
    try:
        feed = feedparser.parse(feed_config['url'])
        entries = []
        for entry in feed.entries[:20]:  # 只取最新20条
            # 获取唯一 ID 或链接
            entry_id = getattr(entry, 'id', '') or getattr(entry, 'link', '')
            if not entry_id:
                continue
            
            # 获取标题和摘要
            title = getattr(entry, 'title', 'N/A') or 'N/A'
            summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '') or ''
            # 清理 HTML 标签
            summary = re.sub(r'<[^>]+>', '', summary)
            summary = summary[:300] + '...' if len(summary) > 300 else summary
            
            # 获取发布时间
            published = getattr(entry, 'published', '') or datetime.now().isoformat()
            
            entries.append({
                'id': entry_id,
                'title': title,
                'summary': summary,
                'link': getattr(entry, 'link', ''),
                'published': published,
                'source': feed_config['name'],
                'tags': feed_config.get('tags', [])
            })
        return entries
    except Exception as e:
        print(f"  ⚠️ {feed_config['name']}: {e}")
        return []

def main():
    feeds = load_feeds()
    state = load_state()
    seen_urls = set(state.get('seen_urls', []))
    
    today = datetime.now().strftime('%Y-%m-%d')
    all_new_entries = []
    
    print(f"# RSS Fetch - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    for feed_config in feeds:
        print(f"📡 {feed_config['name']}...")
        entries = fetch_feed(feed_config)
        new_count = 0
        for entry in entries:
            if entry['id'] not in seen_urls:
                seen_urls.add(entry['id'])
                all_new_entries.append(entry)
                new_count += 1
        print(f"  → {len(entries)} 条, {new_count} 条新")
    
    # 保存新条目到 learnings
    if all_new_entries:
        output_file = LEARNINGS_DIR / f"rss_{today}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'date': today,
                'entries': all_new_entries,
                'count': len(all_new_entries)
            }, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 今日新增 {len(all_new_entries)} 条知识碎片 → {output_file.name}")
    else:
        print("\n📭 今日无新条目")
    
    # 更新 state
    state['seen_urls'] = list(seen_urls)  # Convert set to list for JSON
    state['last_fetch'] = datetime.now().isoformat()
    save_state(state)
    
    return all_new_entries

if __name__ == "__main__":
    main()
