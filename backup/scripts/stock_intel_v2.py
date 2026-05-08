#!/usr/bin/env python3
"""
A股选股简报脚本 v6 — 每日定时运行
- 直接调东方财富 API + 自研技术指标（不依赖 baostock MCP subprocess）
- 查询自选股技术指标（MACD/RSI/BOLL）
- 获取板块异动
- 整合 Tavily 搜索获取当日市场热点
- 自动写入飞书多维表格（大A表 + 资讯表）
- 输出 Markdown 简报
"""
import asyncio
import json
import math
import os
import re
import sys
import time
import hashlib
import requests
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

TAVILY_KEY = "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"
FEISHU_APP_ID = "cli_a95a1e699d78dcb5"
FEISHU_APP_SECRET = "hnvbzk...MOgT"
BITABLE_BASE_TOKEN = "PlsLbT...cnnf"
BITABLE_STOCK_TABLE = "tbl9Eo8lorQklkLf"
BITABLE_NEWS_TABLE = "tblFxaLIZT15IRIp"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36",
    "Referer": "https://finance.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
}
TIMEOUT = 15
_last_request_time = {}

EM_KLINE = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
EM_REALTIME = "https://push2.eastmoney.com/api/qt/stock/get"
EM_SECTOR = "https://push2.eastmoney.com/api/qt/clist/get"
CONFIG_FILE = Path.home() / ".hermes" / "config" / "stocks.json"

# ── 东方财富 HTTP ──────────────────────────────────────────────

def em_get(url: str, params: dict) -> dict:
    for attempt in range(3):
        try:
            now = time.time()
            if url in _last_request_time and now - _last_request_time[url] < 1.5:
                time.sleep(1.5 - (now - _last_request_time[url]))
            _last_request_time[url] = time.time()
            r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200 and r.text.strip():
                return r.json()
            time.sleep(3)
        except requests.exceptions.ConnectionError:
            time.sleep(5)
        except Exception:
            time.sleep(2)
    return {}

def em_realtime(secid: str) -> dict:
    try:
        now = time.time()
        if EM_REALTIME in _last_request_time and now - _last_request_time[EM_REALTIME] < 1.2:
            time.sleep(1.2 - (now - _last_request_time[EM_REALTIME]))
        _last_request_time[EM_REALTIME] = time.time()
        r = requests.get(EM_REALTIME, params={
            "secid": secid,
            "fields": ("f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,"
                      "f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,"
                      "f70,f71,f72,f73,f74,f75,f76,f77,f170"),
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fltt": "2", "invt": "2"
        }, headers=HEADERS, timeout=TIMEOUT)
        return r.json()
    except Exception:
        return {}

# ── 代码转换 ───────────────────────────────────────────────────

def to_em_secid(code: str) -> str:
    c = code.strip().lower()
    if c.startswith("sh"): return f"1.{c[2:].zfill(6)}"
    if c.startswith("sz"): return f"0.{c[2:].zfill(6)}"
    if c.startswith("bj"): return f"0.{c[2:]}"
    return code

def to_display_code(secid: str) -> str:
    parts = secid.split(".")
    if len(parts) != 2: return secid
    return f"{'sh' if parts[0] == '1' else 'sz'}{parts[1]}"

# ── K线获取 ────────────────────────────────────────────────────

def get_klines(secid: str, days: int = 60, freq: str = "d") -> list:
    klt_map = {"d": "101", "w": "102", "m": "103"}
    data = em_get(EM_KLINE, {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": klt_map.get(freq, "101"),
        "fqt": "1",
        "end": "20500101",
        "lmt": days,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    })
    if not data or not data.get("data"):
        return []
    raw_lines = data["data"].get("klines", [])
    fields = ["date","open","close","high","low","volume","amount","pctChg","pctChange","turnover","amplitude"]
    result = []
    for line in raw_lines:
        parts = line.split(",")
        row = {}
        for i, f in enumerate(fields):
            try:
                row[f] = parts[i] if f == "date" else (float(parts[i]) if parts[i] not in ("-", "") else None)
            except (IndexError, ValueError):
                row[f] = None
        result.append(row)
    return result

# ── 技术指标（纯 Python，无 numpy/pandas） ───────────────────────

def _ma(data: list, n: int) -> float:
    if len(data) < n: return None
    return round(sum(data[-n:]) / n, 3)

def _ema(data: list, n: int) -> float:
    if not data: return 0.0
    k = 2 / (n + 1)
    ema = data[0]
    for p in data[1:]: ema = p * k + ema * (1 - k)
    return round(ema, 3)

def _ema_series(data: list, n: int) -> list:
    if len(data) < n: return []
    k = 2 / (n + 1)
    ema = [data[0]]
    for p in data[1:]: ema.append(p * k + ema[-1] * (1 - k))
    return ema

def _rsi(data: list, n: int = 14) -> float:
    if len(data) < n + 1: return None
    gains, losses = 0.0, 0.0
    for i in range(-n, 0):
        d = data[i] - data[i-1]
        if d > 0: gains += d
        else: losses -= d
    if losses == 0: return 100.0
    return round(100 - 100 / (1 + gains / losses), 2)

def _rsi_series(data: list, n: int = 14) -> list:
    if len(data) < n + 1: return []
    result = []
    for i in range(n, len(data) + 1):
        window = data[i-n:i]
        gains, losses = 0.0, 0.0
        for j in range(1, n):
            d = window[j] - window[j-1]
            gains += d if d > 0 else 0
            losses -= d if d < 0 else 0
        result.append(100.0 if losses == 0 else round(100 - 100 / (1 + gains / losses), 2))
    return result

def _macd_series(data: list, fast: int = 12, slow: int = 26, signal: int = 9):
    if len(data) < slow: return [], [], []
    ef = _ema_series(data, fast)
    es = _ema_series(data, slow)
    dif = [f - s for f, s in zip(ef, es)]
    k = 2 / (signal + 1)
    dea = [dif[0]]
    for d in dif[1:]: dea.append(d * k + dea[-1] * (1 - k))
    macd = [round((d - de) * 2, 4) for d, de in zip(dif, dea)]
    return dif, dea, macd

def _macd(data: list) -> dict:
    dif, dea, macd = _macd_series(data)
    if not dif: return {"dif": None, "dea": None, "macd": None}
    return {"dif": round(dif[-1], 4), "dea": round(dea[-1], 4), "macd": round(macd[-1], 4)}

def _boll(data: list, n: int = 20, k: float = 2.0) -> dict:
    if len(data) < n: return {"upper": None, "mid": None, "lower": None}
    mid = sum(data[-n:]) / n
    std = math.sqrt(sum((p - mid)**2 for p in data[-n:]) / n)
    return {"upper": round(mid + k*std, 3), "mid": round(mid, 3), "lower": round(mid - k*std, 3)}

def _vol_ratio(klines: list) -> float:
    if len(klines) < 6: return None
    today_vol = klines[-1].get("volume") or 0
    avg5 = sum((klines[i].get("volume") or 0) for i in range(-6, -1)) / 5
    return round(today_vol / avg5, 2) if avg5 else None

# ── 信号检测 ────────────────────────────────────────────────────

def _detect_cross(series_a: list, series_b: list) -> str:
    if len(series_a) < 3 or len(series_b) < 3: return "none"
    for offset in [-2, -1]:
        try:
            prev_a, curr_a = series_a[offset - 1], series_a[offset]
            prev_b, curr_b = series_b[offset - 1], series_b[offset]
            if prev_a <= prev_b and curr_a > curr_b: return "golden"
            if prev_a >= prev_b and curr_a < curr_b: return "death"
        except (IndexError, TypeError): continue
    return "none"

def _detect_macd_cross(closes: list) -> dict:
    dif, dea, _ = _macd_series(closes)
    if not dif or len(dif) < 3: return {"signal": "none"}
    cross = _detect_cross(dif, dea)
    if cross == "golden": return {"signal": "golden"}
    if cross == "death": return {"signal": "death"}
    return {"signal": "none" if dif[-1] < dea[-1] else "bullish_region"}

def _detect_rsi_cross(closes: list) -> dict:
    rsi6 = _rsi_series(closes, 6)
    rsi12_all = _rsi_series(closes, 12)
    if not rsi6 or not rsi12_all or len(rsi6) < 3: return {"signal": "none"}
    cross = _detect_cross(rsi6, rsi12_all)
    if cross == "golden": return {"signal": "golden"}
    if cross == "death": return {"signal": "death"}
    rsi6_val = rsi6[-1]
    if rsi6_val > 80: return {"signal": "overbought"}
    if rsi6_val < 20: return {"signal": "oversold"}
    return {"signal": "none"}

def _detect_boll_break(closes: list, klines: list) -> dict:
    if len(closes) < 20: return {"signal": "none"}
    today_close = closes[-1]
    boll = _boll(closes, 20)
    upper, lower, mid = boll["upper"], boll["lower"], boll["mid"]
    if None in (upper, lower, mid): return {"signal": "none"}
    if today_close > upper: return {"signal": "break_upper"}
    if today_close < lower: return {"signal": "break_lower"}
    dist_to_upper = (today_close - upper) / upper * 100
    dist_to_lower = (lower - today_close) / lower * 100
    if dist_to_upper < 1: return {"signal": "near_upper"}
    if dist_to_lower < 1: return {"signal": "near_lower"}
    return {"signal": "none"}

# ── 板块数据 ────────────────────────────────────────────────────

def get_sectors(sort: str = "f3", top: int = 20) -> list:
    try:
        r = requests.get(EM_SECTOR, params={
            "pn": 1, "pz": top, "po": 1, "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": 2, "invt": 2,
            "fid": sort, "fs": "m:90+t:2",
            "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21",
        }, headers=HEADERS, timeout=TIMEOUT)
        data = r.json()
        if not data or not data.get("data"): return []
        return [{
            "板块名称": line.get("f14", ""),
            "涨跌幅": line.get("f3", 0),
            "成交量": line.get("f5", 0),
            "成交额": line.get("f6", 0),
            "上涨": line.get("f10", 0),
            "下跌": line.get("f20", 0),
        } for line in data["data"].get("diff", [])]
    except Exception:
        return []

# ── 飞书 API ───────────────────────────────────────────────────

def load_env():
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

def get_feishu_token() -> str:
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read()).get("tenant_access_token", "")

def bitable_write_record(token: str, table_id: str, fields: dict):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_BASE_TOKEN}/tables/{table_id}/records"
    data = json.dumps({"fields": fields}).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

def write_stocks_to_bitable(token: str, records: list):
    print(f"\n📝 写入大A表 ({len(records)}条)...")
    for rec in records:
        try:
            result = bitable_write_record(token, BITABLE_STOCK_TABLE, rec)
            if result.get("code") == 0:
                print(f"  ✅ {rec.get('股票名称', '?')} ({rec.get('操作', '?')})")
            else:
                print(f"  ❌ {rec.get('股票名称', '?')}: {result.get('msg')}")
        except Exception as e:
            print(f"  ❌ {rec.get('股票名称', '?')}: {e}")
        time.sleep(0.3)

def write_news_to_bitable(token: str, records: list):
    print(f"\n📝 写入资讯表 ({len(records)}条)...")
    for rec in records:
        try:
            result = bitable_write_record(token, BITABLE_NEWS_TABLE, rec)
            if result.get("code") == 0:
                print(f"  ✅ [{rec.get('类别', '?')}] {rec.get('标题', '?')[:30]}...")
            else:
                print(f"  ❌ [{rec.get('类别', '?')}]: {result.get('msg')}")
        except Exception as e:
            print(f"  ❌ {rec.get('类别', '?')}: {e}")
        time.sleep(0.3)

# ── 工具函数 ───────────────────────────────────────────────────

def format_change(pct):
    try:
        v = float(str(pct).replace("%", ""))
        if v > 0: return f"🔴 +{v:.2f}%"
        elif v < 0: return f"🟢 {v:.2f}%"
        else: return f"⚪ {v:.2f}%"
    except: return str(pct)

def parse_signal(macd_sig: str, rsi_sig: str, boll_sig: str) -> str:
    parts = []
    if macd_sig and macd_sig != "none": parts.append(f"MACD:{macd_sig}")
    if rsi_sig and rsi_sig != "none": parts.append(f"RSI:{rsi_sig}")
    if boll_sig and boll_sig != "none": parts.append(f"BOLL:{boll_sig}")
    return " / ".join(parts) if parts else "➖ 无明显信号"

def analyze_opportunity(d: dict) -> str:
    suggestions = []
    macd_sig = d.get("MACD信号", "none")
    rsi_sig = d.get("RSI信号", "none")
    boll_sig = d.get("BOLL信号", "none")
    rsi6 = d.get("RSI6", 50)
    if boll_sig in ("near_upper", "break_upper"): suggestions.append("⚠️ 贴近/突破上轨，谨慎追高")
    if rsi_sig == "overbought" or (isinstance(rsi6, (int, float)) and rsi6 > 80): suggestions.append("⚠️ RSI 超买，警惕回调")
    if macd_sig in ("golden", "bullish_region"): suggestions.append("✅ MACD 多头/金叉")
    if rsi_sig == "golden": suggestions.append("✅ RSI 金叉")
    if boll_sig in ("near_lower", "break_lower"): suggestions.append("✅ 关注下轨支撑/超跌反弹")
    return " / ".join(suggestions) if suggestions else "⏸️ 观望等待信号"

# ── 自选股加载 ─────────────────────────────────────────────────

def load_watchlist() -> list:
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            return [(c, n) for c, n in data.get("stocks", [])]
        except Exception: pass
    return [
        ("sh000001", "上证指数"), ("sh600036", "招商银行"), ("sh601318", "中国平安"),
        ("sz000858", "五粮液"), ("sz300750", "宁德时代"), ("sh600519", "贵州茅台"),
        ("sz002594", "比亚迪"), ("sh600900", "长江电力"), ("sh603897", "长城科技"),
    ]

# ── 市场热点 ───────────────────────────────────────────────────

async def get_market_hot() -> tuple:
    try:
        url = "https://api.tavily.com/search"
        today = datetime.now().strftime("%Y年%m月%d日")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")
        day_before = (datetime.now() - timedelta(days=2)).strftime("%Y年%m月%d日")
        query = f"{today} OR {yesterday} OR {day_before} A股 股市 政策 军事 AI 重大消息"
        payload = json.dumps({
            "api_key": TAVILY_KEY,
            "query": query,
            "search_depth": "advanced",
            "max_results": 8,
            "include_answer": False,
            "include_raw_content": False
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        raw_results = []
        for r in data.get("results", [])[:8]:
            title = r.get("title", "")[:80]
            url_link = r.get("url", "")
            published = r.get("published_date", "")
            raw = r.get("content", "") or ""
            raw = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", raw)
            raw = re.sub(r"\b(Macromedia|Flash|Player)\b", "", raw)
            raw = re.sub(r"\s+", " ", raw).strip()
            content = raw[:200].strip() if len(raw.strip()) >= 30 else ""
            raw_results.append({"title": title, "content": content, "url": url_link, "published": published})
        results = []
        for d in raw_results:
            if d["content"]: results.append(f"• **{d['title']}** — {d['content']}...")
            else: results.append(f"• **{d['title']}**")
        return results, raw_results
    except Exception as e:
        print(f"  ⚠️ 热点搜索失败: {e}")
        return [], []

# ── 主程序 ─────────────────────────────────────────────────────

def main():
    load_env()

    print("📊 查询自选股指标...")
    stocks = load_watchlist()
    success = []
    failed = []

    for scode, sname in stocks:
        time.sleep(1.5)  # 防限流
        secid = to_em_secid(scode)
        klines = get_klines(secid, days=30)
        if not klines:
            failed.append({"code": scode, "name": sname, "error": "获取K线失败"})
            continue
        closes = [k["close"] for k in klines if k.get("close") is not None]
        today = klines[-1]
        macd_sig = _detect_macd_cross(closes)
        rsi_sig = _detect_rsi_cross(closes)
        boll_sig = _detect_boll_break(closes, klines)
        macd = _macd(closes)
        success.append({
            "code": scode, "name": sname,
            "最新价": today.get("close"),
            "涨跌幅": f"{today.get('pctChg', 0):.2f}%",
            "RSI6": _rsi(closes, 6),
            "MACD": macd["macd"],
            "MACD信号": macd_sig["signal"],
            "RSI信号": rsi_sig["signal"],
            "BOLL信号": boll_sig["signal"],
            "量比": _vol_ratio(klines),
        })

    print(f"  成功: {len(success)}/{len(stocks)}")
    if failed: print(f"  失败: {[d['code'] for d in failed]}")

    print("🏭 查询板块TOP5...")
    sector = get_sectors(sort="f3", top=5)

    print("🔥 获取市场热点...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    hot, raw_hot = loop.run_until_complete(get_market_hot())
    loop.close()

    # ── 准备飞书数据 ──
    now = datetime.now()
    today_ts = int(now.timestamp() * 1000)
    today_str = now.strftime("%Y-%m-%d")

    stock_records = []
    for d in success:
        code = d.get("code", "")
        name = d.get("name", "?")
        price = d.get("最新价", "-")
        chg_str = d.get("涨跌幅", "0%")
        rsi6 = d.get("RSI6", "-")
        macd_val = d.get("MACD", "-")
        macd_sig = d.get("MACD信号", "none")
        rsi_sig = d.get("RSI信号", "none")
        boll_sig = d.get("BOLL信号", "none")
        vol_ratio = d.get("量比", "-")
        opp = analyze_opportunity(d)

        if "✅" in opp and "⚠️" not in opp: op = "关注"
        elif "⚠️" in opp and "✅" not in opp: op = "观望"
        elif "⚠️" in opp and "✅" in opp: op = "谨慎关注"
        else: op = "观望"

        if macd_sig == "golden": signal_basis = "MACD金叉"
        elif rsi_sig == "golden": signal_basis = "RSI金叉"
        elif boll_sig in ("near_lower", "break_lower"): signal_basis = "BOLL下轨"
        elif boll_sig in ("near_upper", "break_upper"): signal_basis = "BOLL上轨"
        elif rsi_sig == "death": signal_basis = "RSI死叉"
        else: signal_basis = "无明显信号"

        stock_records.append({
            "日期": today_ts,
            "股票代码": code,
            "股票名称": name,
            "操作": op,
            "信号依据": signal_basis,
            "技术信号": f"RSI6={rsi6} / MACD={macd_val}({macd_sig}) / RSI信号={rsi_sig} / BOLL={boll_sig} / 量比={vol_ratio}",
            "操作建议": f"最新价{price} {format_change(chg_str)}。{opp}",
            "结果": "待观察"
        })

    news_records = []
    for item in raw_hot:
        title = item.get("title", "")
        content = item.get("content", "")
        url_link = item.get("url", "")
        lower_title = title.lower()
        if any(k in lower_title for k in ["军事", "战争", "伊朗", "中东", "武器", "航母", "军工"]): cat = "军事"
        elif any(k in lower_title for k in ["政策", "两会", "证监会", "央行", "监管", "AI治理", "规划"]): cat = "政策"
        elif any(k in lower_title for k in ["人工智能", "AI", "大模型", "GPT", "机器学习", "科技股"]): cat = "AI"
        else: cat = "国际"
        news_records.append({
            "日期": today_ts,
            "类别": cat,
            "标题": title,
            "摘要": content,
            "相关板块": "",
            "链接": {"link": url_link} if url_link else {"link": ""}
        })

    # ── 构建 Markdown 简报 ──
    lines = [f"## 📈 A股选股简报 · {now.strftime('%Y-%m-%d %H:%M')}\n"]

    if hot:
        lines.append("### 🔥 今日市场热点\n")
        for h in hot: lines.append(h + "\n")
        lines.append("\n---\n")

    if sector:
        lines.append("### 📊 板块异动TOP5\n")
        for s in sector[:5]:
            chg = float(str(s.get("涨跌幅", "0%")).replace("%", ""))
            emoji = "🔴" if chg > 0 else "🟢"
            lines.append(f"- {emoji} **{s.get('板块名称', '')}**: {format_change(s.get('涨跌幅', '0%'))}")
        lines.append("\n---\n")

    lines.append("### 📋 自选股技术信号\n\n")
    for d in success:
        name = d.get("name", "?")
        code = d.get("code", "")
        price = d.get("最新价", "-")
        chg_str = d.get("涨跌幅", "0%")
        rsi6 = d.get("RSI6", "-")
        macd_val = d.get("MACD", "-")
        macd_sig = d.get("MACD信号", "none")
        rsi_sig = d.get("RSI信号", "none")
        boll_sig = d.get("BOLL信号", "none")
        vol_ratio = d.get("量比", "-")
        macd_summary = parse_signal(macd_sig, rsi_sig, boll_sig)
        opp = analyze_opportunity(d)

        lines.append(f"**{name}** (`{code}`)\n")
        lines.append(f"| 最新价 | {price} {format_change(chg_str)} |\n")
        lines.append(f"| RSI(6) | {rsi6} |\n")
        lines.append(f"| MACD | {macd_val} → {macd_sig} |\n")
        lines.append(f"| RSI信号 | {rsi_sig} |\n")
        lines.append(f"| BOLL信号 | {boll_sig} |\n")
        lines.append(f"| 量比 | {vol_ratio} |\n")
        lines.append(f"| **信号汇总** | {macd_summary} |\n")
        lines.append(f"| **操作建议** | {opp} |\n")
        lines.append("\n")

    lines.append("---\n")
    lines.append("*📌 信号说明：MACD 金叉/多头=关注，死叉=谨慎；RSI>80超买/<20超卖；BOLL 贴近下轨=反弹机会，上轨=谨慎追高*\n")

    msg = "\n".join(lines)

    # ── 写入飞书 ──
    try:
        token = get_feishu_token()
        if token:
            write_stocks_to_bitable(token, stock_records)
            write_news_to_bitable(token, news_records)
        else:
            print("\n⚠️ 无法获取飞书token，跳过表格写入")
    except Exception as e:
        print(f"\n⚠️ 飞书表格写入失败: {e}")

    # 输出完整简报供 Cron 捕获
    print("\n=== FULL_REPORT_START ===")
    print(msg)
    print("=== FULL_REPORT_END ===")
    print("\n=== 简报摘要 ===")
    print(msg[:500])
    print("\n✅ 选股简报生成完成")

if __name__ == "__main__":
    main()
