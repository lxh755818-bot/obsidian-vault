# Source: `lark-cli-termux-install`

---
name: lark-cli-termux-install
description: 在 Termux (Android) 上安装飞书 CLI — npm 不支持，本地源码编译解决 Go DNS 解析 bug
---

# lark-cli (飞书CLI) Termux 安装指南

## 背景

`@larksuite/cli` 的 npm 包不支持 Android (Termux) 平台。GitHub 官方提供了 Linux ARM64 预编译包，但在 Termux 上预编译二进制有 DNS 解析 bug（Go 的 netdns 在 Android 上默认查 ::1 而非 /etc/resolv.conf）。**本地源码编译可解决此问题。**

---

## 安装步骤

### 1. 安装 Go（如果还没有）
```bash
pkg install golang -y
```

### 2. 下载源码
```bash
# 通过 GitHub API 下载 tarball
curl -L "https://api.github.com/repos/larksuite/cli/tarball/v1.0.13" -o larksuite-cli-src.tar.gz
tar -xzf larksuite-cli-src.tar.gz
cd larksuite-cli-*/   # 进入解压目录
```

### 3. 本地编译
```bash
export GOPATH=$HOME/go
export GOCACHE=$HOME/.cache/go-build
go build -o $HOME/bin/lark-cli .
chmod +x $HOME/bin/lark-cli
```

### 4. 验证
```bash
export PATH="$HOME/bin:$PATH"
lark-cli --version
```

---

## 初始化登录（首次使用）

```bash
export PATH="$HOME/bin:$PATH"
lark-cli config init --new
```
会输出授权链接，格式如 `https://open.feishu.cn/page/cli?user_code=XXXX-XXXX&lpv=DEV&ocv=DEV&from=cli`。

**重要**：CLI 会立即开始轮询 `accounts.feishu.cn` 验证授权（最多约200次），**必须在 CLI 等待期间用手机浏览器打开链接完成授权**。如果超时，链接会失效，需重新运行命令生成新链接（user_code 会变化）。

**已验证**（2026-04-18）：链接本身有效，问题是轮询等待时网络不稳定导致 `connection reset by peer`。等几秒重试通常能成功。

---

## 关键经验

- **不要用 `npm install -g @larksuite/cli`**：Android 不支持
- **不要直接用官方预编译 binary**：Go DNS 解析在 Android 上有 bug，表现为 `lookup xxx on [::1]:53` 失败（::1 即 IPv6 loopback，Android 上无 DNS 服务）
- **本地编译有效**：在 Termux 环境中用 `go build` 源码编译出的二进制 DNS 行为正常
- **`GODEBUG=netdns=cgo` 无效**：Go 的 cgo DNS 在 Android 上同样查 ::1，无法解决
- **初始化登录用 `--new` flag**：首次配置必须 `lark-cli config init --new`，会输出带 user_code 的授权链接
- 如果 `go build` 下载依赖模块超时（网络问题），可尝试：
  ```bash
  export GOPROXY=https://goproxy.cn,direct
  ```

## 授权登录失败的处理

### 方案一：App ID + App Secret（非交互式）
如果 `config init --new` 轮询授权时网络不稳定（`connection reset by peer`），可以去飞书开放平台手动创建应用，直接提供 App ID 和 App Secret：

```bash
# 手动创建应用后
lark-cli config init --app-id cli-aaa --app-secret-stdin
# 然后 stdin 输入 App Secret
```

### 方案二：检查网络
`accounts.feishu.cn` 的轮询连接不稳定时：
```bash
curl -v https://accounts.feishu.cn/oauth/v1/app/registration
# 如果 TLS handshake 成功但 Go 程序连接被 reset，说明是服务器端限速/不稳定
# 等几秒再重试
```

### 常见错误排查
| 错误 | 原因 | 解决 |
|---|---|---|
| `lookup xxx on [::1]:53` | Go DNS bug | 本地 `go build` 编译 |
| `EBADPLATFORM` | npm 不支持 Android | 用源码编译 |
| `connection reset by peer` | 网络不稳定或服务器限速 | 等几秒重试 |
| `config init` 无反应 | 授权 URL 未在浏览器打开 | 确保打开链接完成配置 |
