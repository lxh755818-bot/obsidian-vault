#!/usr/bin/env python3
"""
A股情报收集脚本 v2 — 定时运行
启动 baostock_mcp.py，查询重点股票完整指标（含信号检测），推送飞书
"""
import asyncio
import json
import subprocess
import sys
import os
from datetime import datetime

MCP_PATH = "/data/data/com.termux/files/home/baostock_mcp.py"

def load_env():
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("FEISHU") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

async def call_mcp(proc, method, params):
    id_ = 1
    obj = {"jsonrpc": "2.0", "id": id_, "method": method, "params": params}
    proc.stdin.write(json.dumps(obj).encode() + b"\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        return None
    return json.loads(line)

def format_change(pct):
    try:
        v = float(str(pct).replace("%", ""))
        if v > 0:
            return f"🔴+{v:.2f}%"
        elif v < 0:
            return f"🟢{v:.2f}%"
        else:
            return f"⚪{v:.2f}%"
    except:
        return str(pct)

def signal_emoji(signal: str) -> str:
    """信号 → emoji"""
    mapping = {
        "golden": "💹 金叉",
        "death": "💸 死叉",
        "break_upper": "🔺 突破上轨",
        "break_lower": "🔻 跌破下轨",
        "near_upper": "⏫ 贴近上轨",
        "near_lower": "⏬ 贴近下轨",
        "none": "➖",
    }
    return mapping.get(signal, signal)

def build_message(batch_data, sector_data):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"## 📈 A股智能情报 · {now}\n"]

    # 个股
    lines.append("### 个股技术信号\n")
    lines.append("| 名称 | 最新价 | 涨跌 | RSI6 | MACD信号 | RSI信号 | BOLL信号 | 量比 |")
    lines.append("|---|---|---|---|---|---|---|---|")

    for d in batch_data:
        if not d or d.get("error"):
            continue
        name = d.get("name", d.get("code", ""))
        macd_sig = signal_emoji(d.get("MACD信号", "none"))
        rsi_sig = signal_emoji(d.get("RSI信号", "none"))
        boll_sig = signal_emoji(d.get("BOLL信号", "none"))
        lines.append(
            f"| {name} | "
            f"{d.get('最新价', '-')} | "
            f"{format_change(d.get('涨跌幅', '0%'))} | "
            f"{d.get('RSI6') or '-'} | "
            f"{macd_sig} | "
            f"{rsi_sig} | "
            f"{boll_sig} | "
            f"{d.get('量比') or '-'} |"
        )

    # 板块
    if sector_data:
        lines.append("\n### 🔥 板块涨幅TOP5\n")
        for s in sector_data[:5]:
            lines.append(f"- {s.get('板块名称','')}: {format_change(s.get('涨跌幅', 0))}")

    # 信号汇总
    golden_stocks = [d for d in batch_data if d.get("MACD信号") == "golden" or d.get("RSI信号") == "golden"]
    death_stocks = [d for d in batch_data if d.get("MACD信号") == "death" or d.get("RSI信号") == "death"]
    break_upper = [d for d in batch_data if d.get("BOLL信号") == "break_upper"]
    break_lower = [d for d in batch_data if d.get("BOLL信号") == "break_lower"]

    if golden_stocks:
        lines.append("\n### 💹 MACD/RSI 金叉信号\n")
        for d in golden_stocks:
            lines.append(f"- {d['name']} {d.get('最新价')} {format_change(d.get('涨跌幅','0%'))}")
    if death_stocks:
        lines.append("\n### 💸 死叉信号\n")
        for d in death_stocks:
            lines.append(f"- {d['name']} {d.get('最新价')} {format_change(d.get('涨跌幅','0%'))}")
    if break_upper:
        lines.append("\n### 🔺 BOLL 突破上轨\n")
        for d in break_upper:
            lines.append(f"- {d['name']} {d.get('最新价')}")
    if break_lower:
        lines.append("\n### 🔻 BOLL 跌破下轨\n")
        for d in break_lower:
            lines.append(f"- {d['name']} {d.get('最新价')}")

    return "\n".join(lines)

def send_feishu(content):
    """通过 hermes send_message 工具发送（由 Cron job 的 deliver 机制处理，此处跳过）"""
    pass  # Cron 的 deliver: feishu 会自动处理

async def main():
    load_env()

    print("🚀 启动 baostock_mcp...")
    proc = subprocess.Popen(
        [sys.executable, MCP_PATH],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    try:
        r = await call_mcp(proc, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "stock-intel-v2", "version": "2.0"}
        })
        if not r or r.get("error"):
            print("MCP初始化失败:", r)
            return

        await call_mcp(proc, "notifications/initialized", {})

        # 用 stock_batch 一次性获取所有自选股
        print("📊 批量查询自选股指标...")
        r = await call_mcp(proc, "tools/call", {
            "name": "stock_batch",
            "arguments": {"days": 30}
        })
        batch = json.loads(r["result"]["content"][0]["text"])
        success = [d for d in batch if not d.get("error")]
        failed = [d for d in batch if d.get("error")]
        print(f"  成功: {len(success)}/{len(batch)}")
        if failed:
            print(f"  失败: {[d['code'] for d in failed]}")

        # 板块
        print("🏭 查询板块数据...")
        r = await call_mcp(proc, "tools/call", {
            "name": "stock_sector",
            "arguments": {"sort": "f3", "top": 5}
        })
        sector = json.loads(r["result"]["content"][0]["text"])
        print(f"  板块TOP5: {[s.get('板块名称') for s in sector[:5]]}")

        # 构推送
        msg = build_message(batch, sector)
        print("\n=== 情报摘要 ===")
        print(msg[:600])

        send_feishu(msg)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("✅ 情报收集完成")

if __name__ == "__main__":
    asyncio.run(main())
