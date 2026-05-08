# 飞书多维表格（Bitable）API 调用参考

## 认证流程

```python
import json, urllib.request, ssl

APP_ID = "<bitable_app_id>"
APP_SECRET = "<bitable_app_secret>"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Step 1: 获取 tenant_access_token
req = urllib.request.Request(
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    data=json.dumps({'app_id': APP_ID, 'app_secret': APP_SECRET}).encode(),
    headers={'Content-Type': 'application/json'}, method='POST'
)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    raw = resp.read()
token_data = json.loads(raw)
assert token_data.get('code') == 0, f"Auth failed: {token_data}"
tenant_token = token_data['tenant_access_token']
```

## 常用 API

### 列出所有表
```python
BASE_ID = "PlsLbTLynaIF3qsoVXCctXTcnnf"
req = urllib.request.Request(
    f'https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables',
    headers={'Authorization': f'Bearer {tenant_token}'}
)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    tables = json.loads(resp.read())
```

### 列出记录
```python
TABLE_ID = "<table_id>"
req = urllib.request.Request(
    f'https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{TABLE_ID}/records',
    headers={'Authorization': f'Bearer {tenant_token}'}
)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    records = json.loads(resp.read())
```

## 错误排查

| code | msg | 原因 |
|------|-----|------|
| 10014 | app secret invalid | App Secret 错误，确认用的是 Bitable App 的 Secret |
| 10003 | invalid param | app_id 或 app_secret 格式错误 |
| 99991664 | token expired | token 过期，重新获取 |
| 400 | Bad Request | 请求格式问题（如 URL 错误、header 缺失）|

## 重要限制

- **单次请求记录上限**：默认 100 条，需要分页
- **多维表格需要 App 有对应权限**：在飞书开放平台 → 应用 → 权限管理，开通 `bitable:app` 或 `bitable:table:readonly`
- **Base 链接两种格式**：
  - 分享链接：`https://xxx.feishu.cn/base/xxx` → 需 App 有权限才能 API 访问
  - 开放平台格式：App 直接按 base_id 访问，权限不足会返回空或报错
