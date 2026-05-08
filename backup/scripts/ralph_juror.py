#!/usr/bin/env python3
"""
Ralph JUROR — 评审角色
每次迭代后分析进度，决定策略：EXPLORE / EXPLOIT / REDESIGN

钱学森方法论：定性（判断方向）+ 定量（数据支撑）
"""

import json
from pathlib import Path
from datetime import datetime

RALPH_DIR = Path.home() / ".hermes" / "ralph"
HISTORY_FILE = RALPH_DIR / "progress_history.json"

STRATEGIES = {
    "EXPLORE": "宽范围探索，摸边界，不惜试错，积累 learn",
    "EXPLOIT": "在已知最优路径上深挖，最小化试错，收敛",
    "REDESIGN": "任务分解有问题，需要拆分 story 或重新设计"
}

def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {"iterations": [], "total": 0, "current_strategy": "EXPLORE"}


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def calc_progress(history):
    """量化进度：learnings 数量 + 文件变更量"""
    if not history["iterations"]:
        return 0, {}
    total_learnings = sum(i.get("learnings_count", 0) for i in history["iterations"])
    total_files = sum(len(i.get("files_changed", [])) for i in history["iterations"])
    recent = history["iterations"][-3:]  # 最近 3 次
    recent_learnings = sum(i.get("learnings_count", 0) for i in recent)
    return total_learnings, {"total_files": total_files, "recent_learnings": recent_learnings}


def is_stuck(history, last_n=2):
    """判断是否 stuck：最近 N 次 learnings 都很少或为空"""
    if len(history["iterations"]) < last_n:
        return False
    recent = history["iterations"][-last_n:]
    # 连续 last_n 次 learnings 数量都 <=1
    return all(i.get("learnings_count", 0) <= 1 for i in recent)


def is_converged(history, threshold_pct=5):
    """判断是否收敛：最近 2 次迭代进度变化 < threshold"""
    if len(history["iterations"]) < 2:
        return False
    last = history["iterations"][-1]
    prev = history["iterations"][-2]
    # 用 learnings_count 变化代表进度
    delta = abs(last.get("learnings_count", 0) - prev.get("learnings_count", 0))
    # 如果两次都是 0 或很少，认为收敛
    if last.get("learnings_count", 0) <= 1 and prev.get("learnings_count", 0) <= 1:
        return True
    return False


def should_switch_to_exploit(history):
    """EXPLORE → EXPLOIT 切换条件"""
    if not history["iterations"]:
        return False
    total = history["total"]
    # 钱学森：前 30% 探索，后 70% 深挖
    # 但这里用实际进度判断：有足够的 learn 积累了就切
    total_learnings, _ = calc_progress(history)
    # 有 >=3 条 learn 且迭代过半 → 可以 EXPLOIT
    if total_learnings >= 3 and total >= 2:
        return True
    return False


def is_redesign_needed(result, story):
    """判断是否需要 REDESIGN"""
    # 如果 subagent 报告空 learnings 且 passes:false → story 可能太大
    if not result.get("passes", False):
        if result.get("learnings_count", 0) == 0:
            return True, "passes:false 且无 learnings，story 可能太大，需要拆分"
    # 如果尝试次数 >=3 仍未通过 → 重新设计
    attempt = story.get("attempt", 0)
    if attempt >= 3 and not result.get("passes", False):
        return True, f"尝试 {attempt} 次仍未通过，考虑重新设计"
    return False, ""


def juror_review(last_result=None, story=None):
    """
    JUROR 主评审函数

    Returns:
        dict: {
            "strategy": "EXPLORE" | "EXPLOIT | "REDESIGN",
            "reasoning": "...",
            "adjustments": ["建议1", "建议2"],
            "switch_signal": True | False  # 是否发生了策略切换
        }
    """
    history = load_history()
    total = history["total"]
    current = history["current_strategy"]

    # 如果是 REDESIGN，强制返回 REDESIGN
    if last_result and story:
        need_redesign, reason = is_redesign_needed(last_result, story)
        if need_redesign:
            history["current_strategy"] = "REDESIGN"
            save_history(history)
            return {
                "strategy": "REDESIGN",
                "reasoning": reason,
                "adjustments": ["建议拆分 story 为更小的子任务", "或检查 acceptanceCriteria 是否合理"],
                "switch_signal": current != "REDESIGN"
            }

    # 判断是否 stuck
    if is_stuck(history, last_n=2):
        history["current_strategy"] = "REDESIGN"
        save_history(history)
        return {
            "strategy": "REDESIGN",
            "reasoning": "连续 2 次迭代 learnings <=1，系统 stuck",
            "adjustments": ["建议拆分任务", "或检查 acceptanceCriteria 是否过严"],
            "switch_signal": True
        }

    # 判断是否收敛
    if is_converged(history):
        history["current_strategy"] = "EXPLOIT"
        save_history(history)
        return {
            "strategy": "EXPLOIT",
            "reasoning": "进度变化 <5%，切换到深挖模式",
            "adjustments": ["聚焦已知路径，减少试错"],
            "switch_signal": current == "EXPLORE"
        }

    # EXPLORE → EXPLOIT 切换
    if current == "EXPLORE" and should_switch_to_exploit(history):
        history["current_strategy"] = "EXPLOIT"
        save_history(history)
        return {
            "strategy": "EXPLOIT",
            "reasoning": f"总迭代 {total} 次，learnings 积累充分，切换到深挖",
            "adjustments": ["在已有 learn 基础上精细化", "减少新方向探索"],
            "switch_signal": True
        }

    # 保持当前策略
    return {
        "strategy": current,
        "reasoning": f"保持 {current} 策略",
        "adjustments": [],
        "switch_signal": False
    }


def record_iteration(result):
    """记录本次迭代到历史"""
    history = load_history()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "story_id": result.get("story_id"),
        "strategy": history["current_strategy"],
        "files_changed": result.get("files_changed", []),
        "learnings_count": len(result.get("learnings", [])),
        "learnings": result.get("learnings", []),
        "passes": result.get("passes", False),
        "attempt": result.get("attempt", 1)
    }
    history["iterations"].append(entry)
    history["total"] += 1
    save_history(history)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # CLI 模式
        if sys.argv[1] == "--review":
            verdict = juror_review()
            print(f"JUROR verdict: {verdict}")
        elif sys.argv[1] == "--status":
            h = load_history()
            print(f"Total iterations: {h['total']}")
            print(f"Current strategy: {h['current_strategy']}")
            print(f"Iterations: {len(h['iterations'])}")
    else:
        verdict = juror_review()
        print(json.dumps(verdict, indent=2, ensure_ascii=False))
