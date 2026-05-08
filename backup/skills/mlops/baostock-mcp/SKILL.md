---
name: baostock-mcp
description: A股数据 MCP Server v2 — 纯 Python 实现，支持金叉死叉/BOLL突破/支撑压力位检测，自选股配置文件
triggers:
  - A股技术指标查询
  - 股票实时行情
  - 金叉死叉信号检测
  - BOLL突破信号
  - 板块轮动监控
  - MCP Server 集成
---

# baostock-mcp — A股数据 MCP Server 技能 v2

## 功能
纯 Python 实现的 A股数据 MCP Server v2，不依赖 pandas/numpy。用东方财富 API 获取实时行情、K线、技术指标、板块数据，并提供完整的信号检测系统。

## 文件位置
- MCP Server：`/data/data/com.termux/files/home/baostock_mcp.py`
- 情报脚本：`/data/data/com.termux/files/home/.hermes/scripts/stock_intel.py`
- 自选股配置：`~/.hermes/config/stocks.json`
- Cron Job ID：`2d38d300bf28`

## 架构
```
hermes-agent (Termux)
  └── baostock_mcp.py (MCP Server, stdio)
        ├── stock_realtime   → EastMoney push2 实时行情
        ├── stock_kline      → EastMoney push2his K线数据
        ├── stock_indicators → MA/EMA/RSI/MACD/布林带/量比（纯Python）
        ├── stock_sector     → EastMoney 板块排行榜
        ├── stock_watchlist  → 自选股配置管理（view/add/remove）
        └── stock_batch      → 批量查询（带防限流重试）
  └── stock_intel.py (Cron调用脚本)
        ├── 启动 baostock_mcp.py
        ├── stock_batch 查询所有自选股（含信号检测）
        ├── stock_sector 板块TOP5
        └── 输出 markdown → Cron deliver 飞书
```

## MCP 配置
```yaml
mcp_servers:
  baostock:
    command: /data/data/com.termux/files/home/hermes-agent/venv/bin/python
    args: [/data/data/com.termux/files/home/baostock_mcp.py]
    timeout: 30
```

## 工具列表（6个）

### stock_realtime
获取A股实时行情
- 参数：`code` (如 `sh600036`)
- EastMoney 字段映射（已验证）：
  - f57 = 代码, f58 = 名称
  - f43 = 最新价, f169 = 未知含义（勿用）, f170 = **涨跌幅(%)**, f47 = 成交量, f48 = 成交额, f71 = 换手率
  - f170 为百分数格式，无需转换；必须带 ut 参数
- 返回：最新价/最高/最低/今开/昨收/涨跌额/成交量/成交额/换手率

### stock_kline
获取K线数据
- 参数：`code`, `days`(默认60), `freq`(`d`|`w`|`m`)
- 返回：日期/开/收/高/低/成交量/涨跌幅

### stock_indicators
计算技术指标 + 信号检测（纯Python，无numpy/pandas）
- 参数：`code`, `days`(默认60)
- 返回字段：
  - 价格类：最新价、涨跌幅、成交量、成交额、量比
  - 均线类：MA5/10/20/30/60, EMA12/26
  - RSI：RSI6/12/24
  - MACD：DIF, DEA, MACD
  - BOLL：布林上轨/中轨/下轨
  - 支撑/压力：支撑位1/2、压力位1/2、Pivot
  - 信号：`【信号】MACD` / `【信号】RSI` / `【信号】MA均线` / `【信号】布林带`

### stock_sector
板块排行榜
- 参数：`sort`(`f3`涨跌幅|`f9`成交量|`f6`成交额), `top`(默认20)
- 返回：板块名称/涨跌幅/成交量/成交额/上涨家数/下跌家数

### stock_watchlist
自选股配置管理
- 参数：`action`(`view`|`add`|`remove`), `code`(股票代码如`sh600036`), `name`(股票名称)
- view：返回当前自选股列表（从 `~/.hermes/config/stocks.json` 读取）
- add/remove：动态管理自选股
### stock_batch 返回字段（实际验证）

`stock_batch` 只返回以下 **10个字段**（非完整技术指标）：

```
['code', 'name', '最新价', '涨跌幅', 'RSI6', 'MACD',
 'MACD信号', 'RSI信号', 'BOLL信号', '量比']
```

⚠️ **不返回**：MA5/10/20/30/60、EMA、RSI12/24、布林上下轨、支撑压力位、Pivot
如需完整指标，用 `stock_indicators` 单独查询单只股票。

### 信号字段实际值（已验证）

| 字段 | 实际值 |
|------|--------|
| MACD信号 | `golden` / `death` / `bullish_region` / `bearish_region` / `none` |
| RSI信号 | `golden` / `death` / `overbought` / `oversold` / `none` |
| BOLL信号 | `near_upper` / `break_upper` / `near_lower` / `break_lower` / `none` |

## 信号检测规则

### MACD 信号
- `MACD 金叉`：DIF 从下方上穿 DEA（DIF_prev < DEA_prev 且 DIF > DEA）
- `MACD 死叉`：DIF 从上方下穿 DEA（DIF_prev > DEA_prev 且 DIF < DEA）
- `MACD 多头区域`：DIF > 0 且 DIF > DEA
- `MACD 空头区域`：DIF < 0 或 DIF < DEA

### RSI 信号
- `RSI 金叉`：RSI6 从下方上穿 RSI12（RSI6_prev < RSI12_prev 且 RSI6 > RSI12）
- `RSI 死叉`：RSI6 从上方下穿 RSI12（RSI6_prev > RSI12_prev 且 RSI6 < RSI12）
- 极值：`RSI6 > 75` 超买，`RSI6 < 25` 超卖

### MA 均线信号
- `MA5 上穿 MA20`：短期均线上穿长期均线（金叉）
- `MA5 下穿 MA20`：短期均线下穿长期均线（死叉）

### BOLL 信号
- `BOLL 突破上轨`：价格 > 布林上轨
- `BOLL 跌破下轨`：价格 < 布林下轨
- `BOLL 贴近上轨`：价格在上轨 1% 以内
- `BOLL 贴近下轨`：价格在下轨 1% 以内

### 支撑位/压力位
- 支撑位：Pivot 下方 2% / 4%
- 压力位：Pivot 上方 2% / 4%
- Pivot = (昨高 + 昨低 + 昨收) / 3

## 自选股配置
文件路径：`~/.hermes/config/stocks.json`
```json
{
  "stocks": [
    ["sh000001", "上证指数"],
    ["sh600036", "招商银行"],
    ["sh601318", "中国平安"],
    ["sz000858", "五粮液"],
    ["sz300750", "宁德时代"],
    ["sh600519", "贵州茅台"],
    ["sz002594", "比亚迪"]
  ]
}
```
使用 `stock_watchlist` 工具的 add/remove action 可以动态管理，无需手动编辑文件。

## 代码转换
- `sh600000` → EastMoney secid `1.600036`
- `sz000001` → EastMoney secid `0.000001`
- 指数(上证/深证)：`sh000001` = 上证指数, `sz399001` = 深证成指
- 北交所：`bj8xxxxxx` → `bh.8xxxxxx`

## ⚠️ MCP Server 热更新陷阱（关键调试经验）

**MCP Server 进程不会热加载代码！**

当 baostock_mcp.py 被修改后，已运行的进程（PID）仍然使用内存中的旧代码。新代码只会在进程重启后生效。

**诊断方法：**
```bash
# 查看 baostock_mcp.py 进程启动时间
ps aux | grep baostock_mcp

# 查看文件最后修改时间
stat /data/data/com.termux/files/home/baostock_mcp.py | grep Modify

# 如果进程启动时间 < 文件修改时间 → 代码已过时，需要重启
```

**重启方法：**
```bash
# 方法1：杀掉旧进程，让 hermes-agent 自动重启
pkill -f baostock_mcp.py

# 方法2：重启整个 hermes gateway
cd ~/hermes-agent && . venv/bin/activate && hermes gateway restart
```

**调试时注意：**
- 用 curl/requests 直接测 API 返回什么值（独立验证）
- 用 query_stock.py 走 MCP 协议看返回什么值
- 如果两者不一致 → MCP Server 进程在用旧代码

## EastMoney API 字段解析关键发现

### f170 涨跌幅 — 百分数格式（已验证 ✅）
- `f170` 涨跌幅字段返回的是**百分点格式**（如 `-1.86` 表示 -1.86%），**不需要除以 100**
- **必须包含 `ut` 参数**（`ut="fa5fd1943c7b386f172d6893dbfba10b"`），否则 f170 字段含义错误
- 错误修复历史：
  - ❌ 错误尝试 1：除以 100 → -0.0186%（错了两位数）
  - ❌ 错误尝试 2：去掉 ut 参数 → f170 仍为 -1.86（数据虽然对但方法不对）
  - ✅ 正确做法：保留 ut 参数，f170 直接使用（东方财富已返回百分数）

### f169 量比 — 不要使用
- f169 字段返回**负数值**（如 603897 返回 -0.96），物理上不可能是量比
- f169 含义不明，**不要作为量比使用**
- 量比应从 `stock_indicators` 的 K线数据中计算（5日均量 / 今日成交量）

### f57/f58 — 代码和名称
- f57 = 股票代码（如 `600036`）
- f58 = 股票名称（如 `招商银行`）

## EastMoney 限流应对
- K线接口 (`push2his`) 有IP频率限制
- MCP Server 内置 1.5秒请求间隔
- stock_batch 内置 3次重试（等3s/5s/2s 指数退避）
- 限流后等待约 1分钟自动恢复

## 优化方向
- [x] 金叉/死叉检测 — MACD / RSI / MA 完整信号
- [x] 支撑位/压力位计算 — Pivot 系统
- [x] 自选股配置文件 — JSON + stock_watchlist 工具
- [x] BOLL 突破信号检测
- [x] stock_batch 批量查询（带防限流）
- [ ] 多个数据源备份（限流时切换）
- [ ] 异动预警（涨跌幅超阈值自动推）
- [ ] 技术指标历史回溯（趋势评分）
