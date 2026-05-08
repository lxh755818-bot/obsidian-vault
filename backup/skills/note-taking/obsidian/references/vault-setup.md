# Vault GitHub Sync 配置（2026-04-30 实测）

## 环境状态

- **Vault 路径**：`/storage/emulated/0/Documents/xiaoack/小a/`（**Android vault，不是 Termux**）
- **GitHub 仓库**：`lxh755818-bot/obsidian-vault.git`
- **分支映射**：Android vault `master` → GitHub `main`
- **Token**：classic PAT + `repo` scope，存于 `~/.git-credentials`
- **Sync 脚本**：`~/.hermes/scripts/obsidian_vault_sync.sh`

## 问题排查记录

### ⚠️ GitHub Token scope 不够（最常见 403 根因）

**症状**：
- `curl /user` → 200 ✅（能读身份）
- `git push` → `403 Permission denied to lxh755818-bot` ❌
- GitHub API `/repos/:owner/:repo` 返回 `"permissions": {"push": true}` 但 push 仍然 403

**根因**：Token 可能是 Fine-grained PAT，或 classic PAT 但没勾 `repo` scope。

**验证命令**（按顺序执行）：
```bash
# Step 1: 确认 token 能读
TOKEN="github_pat_..."
curl -s -H "Authorization: Bearer $TOKEN" https://api.github.com/user | \
  python3 -c "import sys,json; print('Login:', json.load(sys.stdin)['login'])"

# Step 2: 确认仓库存在且 token 认为有 push 权限
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/lxh755818-bot/obsidian-vault" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print('perms:', d.get('permissions'))"

# Step 3: 测试 API 写操作（不走 git）
curl -s -X PUT -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"test","content":"dGVzdAo="}' \
  "https://api.github.com/repos/lxh755818-bot/obsidian-vault/contents/test.txt"
# 返回 403 "Resource not accessible" = scope 不够
```

**解决方案**：
1. 打开 https://github.com/settings/tokens
2. 点击 **Generate new token (classic)**（不是 Fine-grained）
3. **勾 `repo`（第一个勾选框）**
4. Generate → 复制新 token
5. 更新 credentials：
   ```bash
   echo "https://lxh755818-bot:${新TOKEN}@github.com" > ~/.git-credentials
   ```
6. 验证：`GIT_TERMINAL_PROMPT=0 git push origin main`

**Token 权限速查**：
| 操作 | 所需 scope |
|------|-----------|
| 读 public 仓库 | 无 |
| 读/写自己的 public 仓库 | `repo` (classic) |
| git push over HTTPS | `repo` (classic) |
| 创建仓库 | `repo` (classic) |
| Fine-grained PAT | 粒度细，易缺权限，不推荐 |

---

### GitHub DNS 被劫持（已恢复，备用记录）

```
github.com → 28.0.0.38（透明代理劫持，而非真实 IP 140.82.x.x）
症状：TLS EOF error，所有 HTTPS 连接失败，curl 返回 HTTP 000
```

**诊断**：
```bash
getent hosts github.com
# 正常：140.82.112.4
# 被劫持：28.0.0.x

python3 -c "import socket; print(socket.gethostbyname('github.com'))"
```

**恢复后操作**：执行 vault sync 脚本即可。

---

### curl 返回 HTTP 000（连接层失败）

**含义**：TCP 连接阶段就失败了，不是应用层返回。

**诊断步骤**：
```bash
curl -s --max-time 10 -o /dev/null -w "%{http_code}" https://api.github.com
# 000 = 网络不通（DNS/路由/端口阻断）
# 200 = 网络正常
# 403 = 网络通但认证/权限有问题
```

常见原因：
1. DNS 劫持 → 检查 `getent hosts github.com`
2. TLS 中间人 → `curl -v` 看 TLS alert
3. 端口被墙 → `nc -zv github.com 443`

---

### vault sync 脚本内容

位置：`~/.hermes/scripts/obsidian_vault_sync.sh`

```bash
#!/usr/bin/env bash
VAULT="${OBSIDIAN_VAULT:-/data/data/com.termux/files/home/obsidian-vault}"
cd "$VAULT" || exit 1

export GIT_AUTHOR_NAME="小a Hermes" GIT_AUTHOR_EMAIL="xiaoa@hermes"
export GIT_COMMITTER_NAME="小a Hermes" GIT_COMMITTER_EMAIL="xiaoa@hermes"

if ! git add -A && git commit -m "Auto-sync $(date '+%Y-%m-%d %H:%M')"; then
    echo "Nothing to commit. Vault is up to date."
    exit 0
fi

if git push origin main; then
    echo "✅ Synced to GitHub"
elif [ -n "$(git status | grep 'github.com.*push')" ]; then
    echo "⚠️  Push denied — check bot token has write access to obsidian-vault"
fi
```

---

### distill_learnings 中的 vault 写入（已集成）

位置：`~/.hermes/scripts/ralph_iteration.py` → `distill_learnings()`

```python
from pathlib import Path

def distill_learnings(learnings, story_id=None):
    vault_path = Path.home() / "obsidian-vault"
    if vault_path.exists():
        date_str = ...
        filename = f"learnings/{date_str}-{story_id}.md" if story_id else f"learnings/{date_str}.md"
        vault_file = vault_path / filename
        vault_file.write_text(content, encoding="utf-8")
        
        sync_script = Path.home() / ".hermes" / "scripts" / "obsidian_vault_sync.sh"
        if sync_script.exists():
            import subprocess as _subprocess
            _subprocess.run(["bash", str(sync_script)], capture_output=True, timeout=30)
```

---

### 本地 tar 打包（网络断时备用）

```bash
cd /data/data/com.termux/files/home
tar -czf obsidian-vault.tar.gz \
  --exclude='obsidian-vault/.git' \
  obsidian-vault

ls -lh obsidian-vault.tar.gz
```

---

### GitHub 上创建 obsidian-vault 仓库

1. 登录 github.com/lxh755818-bot
2. New repository → `obsidian-vault`
3. 不要初始化 README（本地已有）
4. 获取 HTTPS URL：`https://github.com/lxh755818-bot/obsidian-vault.git`
