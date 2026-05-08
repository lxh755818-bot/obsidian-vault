# Source: `llm-evaluation-via-local-api`

---
name: llm-evaluation-via-local-api
description: 在无法安装 lm-eval 的环境下，通过本地 Hermes API 代理对 LLM 进行基准评测
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [evaluation, benchmark, testing, api, local-testing]
    category: mlops
---

# LLM Evaluation via Local API Proxy

## 场景
在 Termux 等无法安装 lm-eval（EleutherAI Evaluation Harness）的环境下，通过本地 Hermes API 代理对 LLM 进行基准评测。

## 背景
- `pip install lm-eval` 在 Termux 上失败：scipy/scikit-learn 编译依赖构建失败（build error on scipy）
- 其他安装方式尝试：清华镜像源、源码克隆 —— 均因编译工具链缺失而失败
- Hermes Gateway 在 `http://127.0.0.1:8642` 提供 OpenAI-compatible chat completions API
- 该本地 API 接受任意 Bearer token（API key 由 gateway 管理）

## API 端点

```
http://127.0.0.1:8642/v1/chat/completions
```

**注意**：实际 MiniMax API key 存在 Hermes config 中，本地代理自动透传，不需要也不应该硬编码到脚本里。

## 评测脚本模板

```python
import urllib.request
import json

url = "http://127.0.0.1:8642/v1/chat/completions"

questions = [
    ("What is the capital of France?", ["Paris", "London", "Berlin", "Rome"]),
    ("Which planet is known as the Red Planet?", ["Mars", "Venus", "Jupiter", "Saturn"]),
    # ... more questions
]

for q, choices in questions:
    prompt = f"{q}\nOptions: {', '.join(choices)}\nAnswer with just the correct option."
    data = json.dumps({
        "model": "MiniMax-M2.7-highspeed",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 20
    }).encode()

    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer test-key"  # 本地代理忽略此字段
    })
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    
    answer = result["choices"][0]["message"]["content"].strip()
    print(f"Q: {q}")
    print(f"A: {answer}")
```

## 验证结果（2026-04-26）

| 题目类型 | 题数 | 正确率 |
|---------|------|--------|
| 基础知识（首都/元素/乘法/行星/海洋） | 5/5 | 100% |
| 进阶推理（贝叶斯/相遇问题/温室气体/逻辑/有丝分裂） | 5/5 | 100% |

模型：MiniMax-M2.7-highspeed

## 局限

- 需要 Hermes Gateway 运行中
- 无标准化 benchmark 数据集（自己构造题目）
- 无法跑 perplexity 等需 logits 的指标

## 适用场景

1. 追踪模型能力变化（定期跑分）
2. 对比不同模型的同一套题
3. 快速验证模型升级效果
4. 作为 lm-eval 的临时替代（termux/android/embedded 环境）
