# 情报收集查询参考

## 推荐查询组合

每轮情报收集（index % 6 == 0）使用以下6个查询，分6次独立工具调用执行：

| # | 查询字符串 | 用途 | 备注 |
|---|-----------|------|------|
| 1 | `site:github.com/trending?since=weekly` | GitHub Trending 周榜 | 抓周榜页面，snippet 质量不稳定 |
| 2 | `github trending AI agent framework 2026 April` | AI Agent 框架热度 | 返回 CSDN/博客园摘要，效果好 |
| 3 | `open source AI agent github stars ranking 2026` | 项目排名对比 | 补充 framework 专用查询 |
| 4 | `site:github.com/NousResearch/hermes-agent/releases` | Hermes 最新发布 | 官方 release 页面，版本号准确 |
| 5 | `new AI agent framework released 2026 April May` | 新发布框架 | 捕获非 trending 渠道的发布 |
| 6 | `AI agent trending this week github open source` | 本周趋势 | 补充 weekly 粒度 |

## 实测观察（2026-05-07 更新）

### 情报结构字段说明
- `rising_stars`: list of dicts with keys `name` (string), `stars` (string), `trend` (string), `lang` (string)
- `new_entrants`: **注意：可能包含 dict 或 string 两种类型**，必须用 `get_name()` helper 处理混合类型
- `hermes.recent_changes`: 列表中每项是字符串（如 `"v0.12.0 发布（2026-04-30）"`）

### 返回质量
- CSDN/博客园摘要比 GitHub 官方 snippet 更信息密集，适合提取结构化数据
- GitHub Trending 页面直接搜 snippet 通常是无关内容，过滤 `since=weekly` 略有改善
- 横评类查询（如 "2026 开源 AI Agent 框架横评:Hermes Agent / OpenClaw / AutoGPT / CrewAI"）返回包含 Hermes Stars 数据的完整对比表，**推荐添加**

### 2026-05-07 最新数据
| 项目 | Stars | 备注 |
|------|-------|------|
| Hermes Agent | ~89.9k | 快速崛起中，v0.12.0（2026-04-30）|
| OpenClaw | 300k+ | GitHub 星王，超越 Linux |
| DeerFlow (字节跳动) | 50k+ | 2026年2月开源，24h冲上 Trending 第一 |
| agency-agents | 60k+ | 7天狂飙2.3万星，周增长第一 |
| Superpowers | 120k+ | 每日+710星 |
| Everything Claude Code | 113k+ | 每日+1651星 |
| WiFi DensePose | 49k+ | 每日+155星，穿墙人体感知 |
| MiniMax MMX-CLI | — | 2026-04-09 发布，Agent 全模态 CLI |
| Mastra | 23.3k | TypeScript 原生 Agent 框架 |

### 失败模式
- `site:github.com/trending?since=weekly` 的 organic 结果大量是 CSDN 爬虫文章，原始 GitHub 项目信息反而少
- 如果 API 返回 auth 错误，直接跳过该查询，不要在 `execute_code` 中重试
- 情报闭环处理 `rising`/`new_entrants` 列表时必须处理混合类型（dict 和 str），否则 AttributeError

## 情报结构模板

```json
{
  "collected_at": "<ISO>",
  "collection_status": "complete",
  "hermes": {
    "stars": "<~16.8k>",
    "position_trend": "stable|rising|falling",
    "recent_changes": ["<release note 1>", "<release note 2>"]
  },
  "ecosystem": {
    "rising_stars": ["<repo> — <one-line description>"],
    "falling": [],
    "new_entrants": ["<framework> (<publisher>)"],
    "trending_topics": ["<topic 1>", "<topic 2>"]
  },
  "insights": [
    "<key insight with numbers if available>"
  ]
}
```
