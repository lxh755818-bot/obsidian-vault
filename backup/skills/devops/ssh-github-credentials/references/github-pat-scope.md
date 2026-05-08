# GitHub PAT 类型与权限问题（2026-04-30 实测）

## 核心教训

**GitHub PAT 有两种类型，权限完全不同：**

| 类型 | 生成位置 | 默认权限 | 写入操作 |
|------|---------|---------|---------|
| **Fine-grained PAT** | Settings → Developer Settings → Fine-grained PATs | 只有 read（甚至 read 也要手动配置） | 全部 403 |
| **Classic PAT** | Settings → Developer Settings → Personal access tokens (classic) | 取决于勾选的 scopes | 需要 `repo` scope |

**经验：首次生成 token 一定要选 classic + 勾 `repo`！**

---

## 症状判断

```
curl -s -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"test","content":"dGVzdAo="}' \
  "https://api.github.com/repos/USER/REPO/contents/test.txt"

# Fine-grained PAT 结果：
{ "message": "Resource not accessible by personal access token", "status": 403 }

# 正确的 classic PAT + repo scope 结果：
{ "status": 422, "message": "\"sha\" wasn't supplied" }  ← 不是权限问题，是参数问题
```

**403 + "Resource not accessible" = Token 没有写权限 scope（通常是 Fine-grained PAT）**

---

## 正确的 Token 配置步骤

1. 打开 https://github.com/settings/tokens
2. **Generate new token (classic)**（不是 Fine-grained）
3. 名字随便填，Expiration 随便选
4. **Scopes：勾 `repo`（第一个）** ← 这个提供完整读写权限
5. Generate → 复制使用

---

## HTTPS Git Push 的 Credential 配置

Token 有写权限但 git push 仍 403？git 没有用到 credentials。

```bash
# 1. 写入 git-credentials 文件
cat > ~/.git-credentials << EOF
https://lxh755818-bot:${TOKEN}@github.com
EOF

# 2. 激活 store helper（全局）
git config --global credential.helper store

# 3. 把 token 直接写进 remote URL（最可靠）
git remote set-url origin "https://lxh755818-bot:${TOKEN}@github.com/USER/REPO.git"

# 4. 验证
git remote -v
# 应该看到：origin  https://lxh755818-bot:***@github.com/USER/REPO.git (push)

# 5. Push
GIT_TERMINAL_PROMPT=0 git push -u origin BRANCH
```

---

## Fetch First 冲突（Remote 有内容，本地也有内容）

**症状：**
```
! [rejected]  main -> main (fetch first)
error: failed to push some refs
hint: The remote contains work that you do not have locally.
```

**场景：** 仓库已有初始 commit（如 GitHub 创建仓库时的 README），本地也有 commit。

**正确处理：**
```bash
# 1. Fetch remote 内容
git fetch origin main

# 2. Rebase 本地到 remote 之上（不产生 merge commit）
git rebase origin/main

# 3. Push
git push origin main
```

**如果想用本地的覆盖 remote（一次性初始化）：**
```bash
git fetch origin main
git rebase origin/main
git push --force origin LOCAL_BRANCH:main
```

---

## 排查命令速查

```bash
# 测试 token 是否有写权限
curl -s -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"test","content":"dGVzdAo="}' \
  "https://api.github.com/repos/USER/REPO/contents/test.txt"

# 检查 git credentials 是否生效
cat ~/.git-credentials
git config --global --list | grep credential

# 检查 remote URL（含 token 的写 git remote -v 会 mask token）
git remote -v

# 详细调试 push
GIT_TRACE=1 GIT_TERMINAL_PROMPT=0 git push origin main 2>&1 | grep -i "credential\|auth\|403\|denied"
```
