# GitHub 网络问题速查（Termux）

## 2026-04-30 发现：透明代理劫持 DNS

**症状**：
```
TLS connect error: error:0A000126:SSL routines::unexpected eof while reading
curl: (35) TLS connect error
git push → fatal: unable to access 'https://github.com/...': TLS connect error
```

**根因**：DNS 解析 `github.com` → `28.0.0.38`（透明代理/防火墙 IP），而非真实 GitHub IP `140.82.x.x`。所有 HTTPS 连接在 TLS handshake 阶段被截断。

**验证方法**：
```bash
python3 -c "import socket; print(socket.gethostbyname('github.com'))"
# 输出 28.0.0.38 → 网络被劫持（正常应为 140.82.x.x）

curl -v --max-time 10 https://github.com 2>&1 | head -5
# 应显示 TLS handshake 失败
```

**临时解决**：
1. 切换网络（WiFi ↔ 手机流量）
2. 检查 Android 代理设置（设置 → WiFi → 当前网络 → 高级 → 代理）
3. 排查是否有 VPN/防火墙 App

**GitHub PAT 作为备选**：
- Token 有 repo 全权限时可尝试 HTTPS URL + token 认证
- 但若网络层截断 TLS，token 认证也无法绕过
- 当前 token：`***REDACTED***`
- credentials 配置：`~/.git-credentials`，`git config credential.helper store`

## 已知受影响操作

| 操作 | 状态 | 备注 |
|------|------|------|
| `curl https://api.github.com` | ❌ TLS EOF | DNS 被劫持 |
| `git push kk` (SSH) | ❌ Connection closed port 22 | 网络层问题 |
| `git push obsidian-vault` (HTTPS) | ❌ TLS EOF | DNS 被劫持 |
| `gh api user` | ❌ EOF | gh 自己也用 HTTPS |

## 紧急恢复路径

当网络恢复后，快速验证：
```bash
python3 -c "import socket; print(socket.gethostbyname('github.com'))"
# 应输出 140.82.x.x

curl -s --max-time 10 https://api.github.com | head -3
# 应输出 JSON 或 404，不是 TLS error
```
