---
name: stock-selector-system
description: A股选股系统 — 三层漏斗模型：消息面(外部信号) → 技术面(baostock扫描) → 基本面(过滤)。每日 Cron 简报自动推送飞书。
triggers:
  - A股选股系统搭建
  - 每日选股简报
  - 股票技术面扫描
  - 板块轮动分析
dependencies: []
---

# A股选股系统 — 三层漏斗模型

## 核心理念
- **不追高** — 等回调企稳后切入
- **有潜力** — 基本面+技术面共振
- **A股为主** — 专注A股机会
- **三层过滤** — 消息面→技术面→基本面

---

## 三层漏斗模型

```
📰 消息面（外部信号）
   你告诉我的国际/国内/热点事件
        ↓
📈 技术面（择时信号）
   baostock 扫描 MACD/RSI/BOLL/支撑压力
        ↓
💰 基本面（过滤）
   PE/ROE/净利润 过滤垃圾股
```

### 第一层：消息面 — 三大影响因子

| 因子 | 影响逻辑 | 例子 |
|------|---------|------|
| **国际/军事** | 地缘冲突 → 军工/能源/稀有金属 | 台海/中东 → 军工 |
| **国内政策** | 政策导向 → 板块轮动 | 十五五 → AI/机器人/医药 |
| **全球热点** | 热点事件 → 概念炒作 | 大宗商品轮动 |

### 第二层：技术面 — baostock 扫描

使用 `stock_batch` 批量扫描自选股：

```python
# 扫描自选股技术信号
stock_batch(days=30)
# 返回：MACD金叉/RSI超买超卖/BOLL突破/支撑压力位
```

**关键信号：**

| 信号 | 含义 | 操作 |
|------|------|------|
| MACD 金叉 | DIF 上穿 DEA | ✅ 买入信号 |
| MACD 死叉 | DIF 下穿 DEA | ❌ 卖出 |
| RSI < 25 | 超卖 | ✅ 关注 |
| RSI > 75 | 超买 | ⚠️ 谨慎 |
| BOLL 贴近下轨 | 超跌反弹机会 | ✅ 关注 |
| BOLL 突破上轨 | 强势但可能回调 | ⚠️ 不追 |

**支撑压力位：**
- 支撑位：Pivot 下方 2% / 4%
- 压力位：Pivot 上方 2% / 4%
- Pivot = (昨高 + 昨低 + 昨收) / 3

### 第三层：基本面 — 过滤

| 指标 | 过滤标准 |
|------|---------|
| PE | < 30 倍（大盘股可适当放宽） |
| ROE | > 10% |
| 净利润 | 近3年持续增长 |

---

## 每日选股简报 Cron

### 触发时间
- **Cron ID**：`bf439e3dd7e6`
- **时间**：09:00（周一至周五，DAY 2确认）
- **搜索方向**：热门国际新闻、军事新闻、AI新闻、政策（DAY 2确认）

### 简报模板

```
📋 每日选股简报 — YYYY-MM-DD

【今日关注方向】
🌍 国际：xxx 事件 → 影响 xxx 板块
🇨🇳 国内：xxx 政策 → 影响 xxx 板块
🔥 热词：xxx → 相关概念股

【技术面关注标的】
✅ 股票A：MACD 金叉形成，回调至支撑位，关注
⚠️ 股票B：RSI 超买，暂不介入
🔴 股票C：跌破 BOLL 下轨，观望

【操作建议】
• 今日主线：xxx
• 谨慎追高，等待回调
• 建议关注：xxx（支撑位 xx 元）
```

---

## 板块轮动规律（2026年验证）

```
货币(黄金/白银) → 工业金属(铜/铝) → 能源化工 → 消费
     ↑                   ↑             ↑          ↑
  2024-2025初         2025中       2025底     2026年初
```

| 板块 | 当前状态 | 机会 |
|------|---------|------|
| 黄金/白银 | 已大涨 150%+ | ⚠️ 估值高 |
| 铜/铝 | PE 23-25 倍 | ⚠️ 已充分定价 |
| 石油/能源 | 刚启动 | ✅ 关注"三桶油"（中海油最纯） |
| 化工 | 受益油价+反内卷 | ✅ 供需改善 |
| 消费 | 即将轮动到 | 🔔 关注涨价传导 |

---

## 长期方向（十五五规划）

| 方向 | 细分 | 逻辑 |
|------|------|------|
| **AI** | 大模型/应用 | 全球领先，持续投入 |
| **高端制造** | 人形机器人/自动化 | 国家战略扶持 |
| **生物制药** | 创新药 | 全球竞争力提升 |
| **反内卷** | 供需改善 | 持续数年的长期主题 |

---

## 配置清单

### 1. 自选股配置
```
TAVILY_API_KEY=tvly-dev-xxx
```
**注意**：修改 .env 后需要 `hermes gateway restart` 才生效

### 3. 自选股配置
```bash
stock_watchlist add sh600900 长江电力
stock_watchlist add sh601318 中国平安
# ... 按需添加
```

---

## ⚠️ 重大架构变更（2026-04-23）：不再依赖 baostock_mcp.py subprocess

**背景**：Python 3.13 上 `mcp` 包（从 `mcp.server` 导入）无法安装（numpy/pandas 编译失败），导致 `subprocess.Popen` 启动 `baostock_mcp.py` 时直接崩溃（ModuleNotFoundError）。

**新架构（v6+）：直接调东方财富 API + 纯 Python 指标计算**
```
stock_intel_v2.py（独立脚本）
  ├── 直接调 EastMoney API（push2his / push2）
  ├── 纯 Python 实现 MACD/RSI/BOLL/均线/支撑压力
  ├── Tavily 热点搜索
  └── 写入飞书多维表格
  └── 不依赖任何外部 MCP 进程
```
脚本路径：`~/.hermes/scripts/stock_intel_v2.py`

**baostock_mcp.py 文件仍存在，但不再被 cron 脚本使用**，保留作为 MCP Server 工具定义参考。

### 核心 API 端点（已验证）

```
K线:   GET https://push2his.eastmoney.com/api/qt/stock/kline/get
实时:  GET https://push2.eastmoney.com/api/qt/stock/get
板块:  GET https://push2.eastmoney.com/api/qt/clist/get
```

### 技术指标实现（纯 Python，无 numpy/pandas）

所有指标计算逻辑直接内嵌在脚本中：
- `_macd_series` / `_macd` → DIF, DEA, MACD 柱
- `_rsi_series` / `_rsi` → RSI6/12/24
- `_boll` → 布林上轨/中轨/下轨
- `_vol_ratio` → 量比（5日均量对比）
- `_detect_cross` → 金叉/死叉检测（通用）
- `_detect_macd_cross` / `_detect_rsi_cross` / `_detect_boll_break` → 各指标信号

### 信号字段的实际值

| 字段 | 可能值 |
|------|--------|
| MACD信号 | `"golden"` / `"death"` / `"bullish_region"` / `"bearish_region"` / `"none"` |
| RSI信号 | `"golden"` / `"death"` / `"overbought"` / `"oversold"` / `"none"` |
| BOLL信号 | `"near_upper"` / `"break_upper"` / `"near_lower"` / `"break_lower"` / `"none"` |

### Cron 脚本规范

1. 脚本放在 `~/.hermes/scripts/` 目录
2. 脚本内用 `=== FULL_REPORT_START ===` 和 `=== FULL_REPORT_END ===` 包裹完整报告
3. Cron prompt 提取两个标记之间的内容发送飞书
4. **asyncio 事件循环**（Python 3.10+）：用 `asyncio.new_event_loop()` + `asyncio.set_event_loop()` + `loop.run_until_complete()`，避免 `get_event_loop()` deprecation warning
5. Tavily API Key 直接写在脚本里

## 新闻获取最佳实践（2026-04-21 更新）

### Tavily 搜索配置

```python
from datetime import datetime, timedelta

today = datetime.now().strftime("%Y年%m月%d日")
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")
day_before = (datetime.now() - timedelta(days=2)).strftime("%Y年%m月%d日")

query = f"{today} OR {yesterday} OR {day_before} A股 股市 政策 军事 AI 重大消息"

payload = {
    "api_key": TAVILY_KEY,
    "query": query,
    "search_depth": "advanced",   # 而非 basic
    "max_results": 8,
    "include_answer": False,       # 勿用！返回英文摘要，对中文查询无意义
    "include_raw_content": False   # 勿用！返回整页HTML非正文
}
```

### ⚠️ 关键教训：asyncio 事件循环（Python 3.10+ 必须用新写法）

```python
# ❌ 旧写法（Python 3.10+ deprecation warning）
hot = asyncio.get_event_loop().run_until_complete(get_market_hot())

# ✅ 正确写法
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
hot = loop.run_until_complete(get_market_hot())
loop.close()
```

### ⚠️ 关键教训：Tavily content 字段的局限

**国内财经站（人民网/东方财富/凤凰网/新浪）使用 JS 动态渲染**，Tavily 的 `content` 字段返回的是整页内容而非干净正文，会混入：
- 导航链（"+ 毛主席纪念堂 + 周恩来纪念网 +..."）
- 菜单项（"财经 焦点 股票 新股 期指 期权..."）
- 侧边栏噪音

`html2text` 对这些站同样无效，无法提取干净正文。

### 内容清理正则（实用方案）

```python
import re
raw = r.get("content", "") or ""
raw = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", raw)  # 去掉 ![](...) 图片语法，注意用 [^)]* 而非 [^)]+（某些来源没有 URL）
raw = re.sub(r"\b(Macromedia|Flash|Player)\b", "", raw)
raw = re.sub(r"\s+", " ", raw).strip()
content = raw[:200].strip() if len(raw.strip()) >= 30 else ""
```

### 新闻标题本身就是摘要

对于正文提取失败的站点（如人民网/东财），**标题已含关键信息**，无需强求正文。例如：
- "美军向伊朗货船开火并控制" → 直接反映地缘冲突
- "特朗普威胁炸毁伊朗发电厂" → 地缘风险升级信号

### `include_answer=True` 的坑

即使查询是中文，`include_answer=True` 仍返回英文摘要，无法使用。

## 当前配置

### 自选股（9只，中小盘+四大方向）

配置路径：`~/.hermes/config/stocks.json`

| 方向 | 股票 | 代码 | 信号状态 |
|------|------|------|---------|
| 6G | 金信诺 | sz300252 | ✅ MACD多头+RSI金叉，贴近上轨 |
| 6G | 盛路通信 | sz002446 | ✅ MACD多头，贴近上轨 |
| AI算力 | 盛弘股份 | sz300693 | ✅ MACD多头，储能变流器龙头 |
| AI算力 | 科士达 | sz002518 | ✅ MACD多头+RSI金叉，贴近上轨 |
| 专精特新 | 本川智能 | sz300964 | ⚠️ MACD死叉+RSI金叉，偏高 |
| 专精特新 | 臻镭科技 | sh688270 | ✅ MACD多头，卫星射频芯片龙头 |
| 专精特新 | 富满微 | sz300671 | 专精特新小巨人，低价半导体 |
| 电力能源 | 江波龙 | sz301308 | 存储芯片，AI算力+电力储能 |
| 电力能源 | 固德威 | sh688390 | 储能逆变器龙头 |

**注意**：全部贴近 BOLL 上轨，短期注意追高风险，建议等回调后介入。

### 四大方向说明
- **6G**：中小盘通信设备，本川智能（创业板）、金信诺、盛路通信
- **AI算力**：光模块/储能变流器中小标的，盛弘股份、科士达
- **专精特新**：工信部认证小巨人，臻镭科技（科创板）、富满微、本川智能
- **电力能源**：储能+电力设备，固德威（科创板）、江波龙（创业板）

### Cron 任务
- ID: `bf439e3dd7e6`
- 时间: 0 9 * * 1-5（周一至周五 09:00）
- 内容: 市场热点 + 板块TOP5 + 自选股技术信号

### 脚本
- `~/.hermes/scripts/stock_intel_v2.py` — A股选股简报主脚本

## 状态

- [x] 调研框架完成（Day 1）
- [x] Cron 简报任务配置（Day 1）
- [x] 自选股配置（9只，含长江电力、长城科技）
- [x] 接入外部新闻源（Tavily，Day 2）
- [x] 新闻日期范围优化（3天，今天+昨天+前天，Day 3）
- [x] 新闻内容清理（正则过滤，Day 3）
- [x] 脚本重写为直接调东方财富 API（2026-04-23）— 不再依赖 baostock_mcp subprocess
- [x] asyncio 事件循环兼容 Python 3.10+（2026-04-23）
- [x] 技术指标准确性验证（2026-04-23，9/9 股票全部成功）
- [x] 自选股全面换仓：大盘权重 → 中小盘四大方向（6G/AI算力/专精特新/电力能源）
