#!/usr/bin/env python3
"""
Ralph TERMINATOR — 终止判决
基于 AgenticControl 的量化终止条件

钱学森：系统稳定性判定 — 何时停止迭代
"""

import json
from pathlib import Path
from datetime import datetime

RALPH_DIR = Path.home() / ".hermes" / "ralph"
PRD_FILE = RALPH_DIR / "prd.json"
HISTORY_FILE = RALPH_DIR / "progress_history.json"

# 量化阈值（来自 AgenticControl 论文）
THRESHOLDS = {
    "min_iterations_before_terminate": 3,   # 至少 3 次迭代才考虑终止
    "max_change_percent": 5,                 # 进度变化 ≤5% 认定收敛
    "max_iterations": 50,                   # 全局最大迭代保护
    "min_learnings_per_story": 1,            # 每个 story 至少 1 条 learning
    "min_pass_rate": 0.8,                   # 至少 80% story 通过
}


def load_prd():
    if not PRD_FILE.exists():
        return None
    with open(PRD_FILE) as f:
        return json.load(f)


def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {"iterations": [], "total": 0}


def all_stories_done(prd):
    return all(s.get("passes", False) for s in prd["userStories"])


def pass_rate(prd):
    total = len(prd["userStories"])
    if total == 0:
        return 0
    done = sum(1 for s in prd["userStories"] if s.get("passes", False))
    return done / total


def avg_learnings_per_story(history):
    """平均每个 story 的 learnings 数量"""
    if not history["iterations"]:
        return 0
    total = sum(i.get("learnings_count", 0) for i in history["iterations"])
    stories = set(i["story_id"] for i in history["iterations"])
    return total / max(len(stories), 1)


def is_stuck_seriously(history, last_n=3):
    """连续 N 次无实质进展"""
    if len(history["iterations"]) < last_n:
        return False
    recent = history["iterations"][-last_n:]
    # 连续 N 次都没有 learnings
    if all(i.get("learnings_count", 0) == 0 for i in recent):
        return True
    # 连续 N 次 passes 都是 false
    if all(not i.get("passes", False) for i in recent):
        return True
    return False


def terminator_judge():
    """
    TERMINATOR 判决函数

    Returns:
        dict: {
            "decision": "TERMINATE_SUCCESS"
                      | "TERMINATE_STUCK"
                      | "TERMINATE_MAX"
                      | "CONTINUE",
            "reason": "...",
            "metrics": {...}
        }
    """
    history = load_history()
    prd = load_prd()

    if not prd:
        return {
            "decision": "ERROR",
            "reason": "PRD 文件不存在",
            "metrics": {}
        }

    total = history["total"]
    iterations = history["iterations"]
    metrics = {
        "total_iterations": total,
        "all_done": all_stories_done(prd),
        "pass_rate": pass_rate(prd),
        "avg_learnings": avg_learnings_per_story(history),
        "is_stuck": is_stuck_seriously(history, last_n=3),
    }

    # 条件 1：全部完成
    if all_stories_done(prd):
        return {
            "decision": "TERMINATE_SUCCESS",
            "reason": "所有 story 通过验收",
            "metrics": metrics
        }

    # 条件 2：严重卡住
    if is_stuck_seriously(history, last_n=3):
        return {
            "decision": "TERMINATE_STUCK",
            "reason": "连续 3 次迭代无实质进展，需要人工介入",
            "metrics": metrics
        }

    # 条件 3：达到最大迭代
    if total >= THRESHOLDS["max_iterations"]:
        return {
            "decision": "TERMINATE_MAX",
            "reason": f"达到最大迭代数 ({THRESHOLDS['max_iterations']})",
            "metrics": metrics
        }

    # 条件 4：最小迭代保护 — 少于 3 次迭代不考虑成功终止
    if total < THRESHOLDS["min_iterations_before_terminate"]:
        return {
            "decision": "CONTINUE",
            "reason": f"迭代次数 ({total}) < 最小保护次数 ({THRESHOLDS['min_iterations_before_terminate']})，继续",
            "metrics": metrics
        }

    # 条件 5：learnings 过少
    avg_l = avg_learnings_per_story(history)
    if avg_l < THRESHOLDS["min_learnings_per_story"]:
        return {
            "decision": "CONTINUE",
            "reason": f"平均 learnings ({avg_l:.1f}) < 阈值 ({THRESHOLDS['min_learnings_per_story']})，继续探索",
            "metrics": metrics
        }

    # 条件 6：通过率过低
    rate = pass_rate(prd)
    if rate < THRESHOLDS["min_pass_rate"] and total >= THRESHOLDS["min_iterations_before_terminate"]:
        # 但如果 stuck 了也要终止
        if is_stuck_seriously(history, last_n=2):
            return {
                "decision": "TERMINATE_STUCK",
                "reason": f"通过率 {rate:.0%} 过低且 stuck",
                "metrics": metrics
            }

    return {
        "decision": "CONTINUE",
        "reason": f"迭代 {total} 次，各指标正常，继续执行",
        "metrics": metrics
    }


if __name__ == "__main__":
    import sys
    result = terminator_judge()
    print(json.dumps(result, indent=2, ensure_ascii=False))
