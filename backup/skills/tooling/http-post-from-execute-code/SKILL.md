---
name: http-post-from-execute-code
description: Use Python urllib via execute_code tool instead of terminal/curl for long JSON POST requests — avoids Termux shell truncation bugs.
---

# HTTP POST from execute_code (not terminal)

## Problem
Long JSON POST requests sent via terminal/curl get truncated in Termux shell due to argument length limits and JSON parsing issues. Answers get cut mid-string, causing parse errors and wrong submissions.

## Solution
Use `execute_code` with Python's `urllib.request` instead:

```python
import urllib.request, json

data = json.dumps({
    "key": "value",
    "long_answer": "..."  # Full answer, no truncation
}).encode()

req = urllib.request.Request(
    "https://api.example.com/endpoint",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req, timeout=30) as r:
    result = json.loads(r.read().decode())
    print(json.dumps(result, indent=2))
```

## When to use
- Any JSON POST body > ~500 characters
- Sending code blocks, long text answers, or structured data via API
- When terminal/curl gives "Unterminated string" or "command not found" errors
- When judge reports your answer as truncated or wrong letter

## Why it works
- `execute_code` runs Python directly, no shell argument parsing
- `urllib.request` sends raw bytes, no shell interpolation
- No environment variable or pipe issues

## Skill(s) this applies to
- clawvard-practice（必须用此方法发送答案）
- Any long-form API POST calls from Termux
