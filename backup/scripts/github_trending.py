#!/usr/bin/env python3
"""GitHub Trending 抓取脚本
抓取 GitHub Trending 页面，提取今日热门项目
"""

import urllib.request
import json
import re
from datetime import datetime

GITHUB_TRENDING_URL = "https://github.com/trending"

def fetch_github_trending():
    """抓取 GitHub Trending 页面"""
    req = urllib.request.Request(
        GITHUB_TRENDING_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; HermesBot/1.0)",
            "Accept": "text/html",
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode('utf-8')
    
    # 解析项目卡片
    # 格式: <h2><a href="/owner/repo">owner/repo</a></h2>
    # 解析项目卡片 - 按 Box-row 分割
    # 每个 Box-row 包含一个 repo 的信息
    rows = re.split(r'Box-row', html)
    
    results = []
    # rows[0] 是 header，rows[1] 到 rows[16] 是实际的 repo 行
    for row in rows[1:17]:  # 取前16个
        # 找第一个 repo 链接（跳过导航链接）
        m = re.search(r'href="/([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)"', row)
        if not m:
            continue
        repo_path = m.group(1)
        # 过滤非 repo 链接
        if any(x in repo_path for x in ['login', 'sponsors', 'apps/', 'trending', 'settings', 'notifications']):
            continue
        full_url = f"https://github.com/{repo_path}"
        # 提取描述
        desc_m = re.search(r'class="col-9[^\"]*"[^>]*>([^<]+)<', row)
        desc = desc_m.group(1).strip() if desc_m else ""
        results.append({
            "repo": repo_path,
            "url": full_url,
            "description": desc,
            "fetched_at": datetime.now().isoformat()
        })
    
    return results

def main():
    repos = fetch_github_trending()
    print(f"# GitHub Trending - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    for r in repos[:10]:
        print(f"## {r['repo']}")
        print(f"URL: {r['url']}")
        if r['description']:
            print(f"描述: {r['description']}")
        print()
    
    # 保存 JSON
    output_path = f"/data/data/com.termux/files/home/.hermes/evolution_logs/github_trending.json"
    with open(output_path, 'w') as f:
        json.dump({
            "fetched_at": datetime.now().isoformat(),
            "repos": repos
        }, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存 {len(repos)} 个项目到 {output_path}")

if __name__ == "__main__":
    main()
