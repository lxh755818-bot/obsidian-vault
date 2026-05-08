# GitHub Secret Scanning & Push Protection

GitHub's secret scanning automatically blocks pushes that contain detected secrets, **even after you think you've redacted them**. This creates a specific failure mode where a `git push --force` with an amended commit still fails because the secret pattern persists in the file content.

---

## The Core Problem

GitHub Push Protection scans commit content, not just commit messages. It uses pattern matching that can trigger on:
- Real API tokens (`ghp_...`, `sk-cp-...`, `eyJ...`)
- `***` patterns that structurally resemble tokens (e.g., `"access_token": "***"` triggers GH013)
- Partial/redacted strings that still match token prefixes

**Key insight**: Simply replacing a token with `***` does NOT always pass GitHub's scanner. The scanner sees the surrounding JSON structure (`"access_token": "***"`) and flags it.

---

## Real-World Failure Sequence (2026-05-08)

1. Commit added `backup/auth/auth.json` with real tokens
2. GitHub blocked push → `GH013: Repository rule violations found`
3. Opened file, saw `"access_token": "***"` — assumed already redacted
4. Amended commit with no changes → still blocked on same file
5. Only when file was **completely rewritten** (all `***` → `[REDACTED]`) did push succeed

**Root cause**: The JSON had real values written via `json.dump()` that didn't update on disk because Python's JSON module wrote to a temp file and renamed. The `***` on disk was the old truncated value from `write_file`'s auto-redaction layer, but the real token was still in the file bytes.

---

## Patterns That Trigger GH013

| Pattern | Why It Triggers | Fix |
|---------|----------------|-----|
| `"access_token": "***"` | `***` looks like a truncated token | Use `"[REDACTED]"` or `"REDACTED"` |
| `"access_token": "ghp_..."` | Real GitHub PAT | Replace with placeholder |
| `"access_token": "eyJ..."` | Real JWT token | Replace with placeholder |
| `tvly-dev-...` | Real Tavily key | Replace with placeholder |
| `hnvbzk...` | Real Feishu secret | Replace with placeholder |

---

## Pre-Push Secret Scan Command

Before pushing, run this to find secrets GitHub will block:

```bash
grep -rEn "ghp_[a-zA-Z0-9]{36}|eyJ[a-zA-Z0-9/+=.-]{40,}|tvly-dev-[a-zA-Z0-9]{20,}|hnvbzk[a-zA-Z0-9/+=]{20,}|sk-cp-[a-zA-Z0-9]{20,}" \
  /path/to/repo/ 2>/dev/null \
  | grep -v "REDACTED\|example\|sample\|xxx\|\.\.\.\|display\|truncated\|format"
```

If this returns results, fix them before pushing.

---

## JSON Redaction That Actually Works

**Wrong** (triggers GH013):
```json
"access_token": "***"
```

**Correct** (passes GH013):
```json
"access_token": "[REDACTED]"
```

**For `.env` files** — always rebuild from template:
```bash
cat > /tmp/.env.template << 'EOF'
# Backup version - fill in real values manually
MINIMAX_CN_API_KEY=***REDACTED***
FEISHU_APP_SECRET=***REDACTED***
GITHUB_PAT=***REDACTED***
EOF
```

**For JSON config files** — parse and rebuild:
```python
import json

with open('auth.json', 'r') as f:
    data = json.load(f)

def redact(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'access_token':
                obj[k] = '[REDACTED]'
            elif isinstance(v, (dict, list)):
                redact(v)
    elif isinstance(obj, list):
        for item in obj:
            redact(item)

redact(data)

with open('auth.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write('\n')
```

---

## When Amend Still Fails After Apparent Fix

If you've fixed a file but `git push --force` still fails with GH013 on the same path:

1. **The file bytes haven't actually changed** — GitHub scanned the old bytes
2. Verify actual bytes on disk (not just what `cat` shows):
   ```bash
   python3 -c "
   with open('auth.json', 'rb') as f:
       raw = f.read()
   print(raw[440:520])  # Print raw bytes around the token area
   "
   ```
3. If real tokens still appear in raw bytes → rewrite the file completely
4. Then `git add -A && git commit --amend -m "fix: redaction" && git push --force`

---

## Recovering a Blocked Push

```bash
# Fix the file, then amend the commit
git add -A
git commit --amend -m "commit message"
git push --force

# If GH013 still appears on the same file after genuine fix:
# The file bytes on disk weren't actually updated
# → Rewrite the file completely (delete and recreate)
```

---

## GitHub Secret Scanning Allowlist (Alternative)

If you have a legitimate secret that can't be redacted (e.g., a test credential), you can allowlist it via the GitHub security settings:

```
https://github.com/{owner}/{repo}/security/secret-scanning/unblock-secret/{secret-id}
```

Each GH013 error message includes a direct link to unblock that specific secret.

---

## Key Takeaway

> **Never assume a file is clean just because it shows `***` or `[REDACTED]` in your terminal.** The only safe approach is: rewrite the file completely with explicit `[REDACTED]` strings, then run the pre-push grep scan to confirm before attempting push.
