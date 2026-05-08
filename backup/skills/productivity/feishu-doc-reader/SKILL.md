---
name: feishu-doc-reader
description: 通过飞书开放平台 API 读取文档内容的技能。包含正确的 docx API 端点、认证流程、和 wiki 文档读取方法。
version: 1.0.0
tags: [feishu, document, wiki, api]
---

# 飞书文档读取技能

## 核心发现（2026-04-29 验证）

飞书开放平台读取文档内容有多层 API：
- Wiki 节点 API：`GET /wiki/v2/spaces/get_node?token=xxx&obj_type=wiki` → 返回 `obj_token`（docx ID）
- Docx 元信息：`GET /docx/v1/documents/{doc_id}` → 返回标题
- **Docx 原始内容**：`GET /docx/v1/documents/{doc_id}/raw_content` → 返回纯文本内容（**正确端点**）

❌ 错误尝试：
- `/docx/v1/document/{doc_id}/content` → 404
- `/docx/v1/documents/{doc_id}/content` → 404
- `/wiki/v2/spaces/get_node_content` → 400

## 完整读取流程

```python
import urllib.request, json

def load_env_key(prefix):
    with open('/data/data/com.termux/files/home/.hermes/.env') as f:
        for line in f:
            line = line.strip()
            if '=' in line and prefix.upper() in line.upper():
                return line.split('=', 1)[1].strip()
    return None

app_id = load_env_key('FEISHU_APP_ID')
app_secret = load_env_key('FEISHU_APP_SECRET')

# Step 1: 获取 tenant access token
token_resp = urllib.request.urlopen(
    urllib.request.Request(
        'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
        data=json.dumps({'app_id': app_id, 'app_secret': app_secret}).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    ), timeout=10
)
tenant_token = json.loads(token_resp.read()).get('tenant_access_token', '')

# Step 2: 如果是 wiki 文档，先获取 docx obj_token
wiki_token = 'TsZtw6rQsigy4skZHRPceKVonVf'  # wiki page token
wiki_resp = urllib.request.urlopen(
    urllib.request.Request(
        f'https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node?token={wiki_token}&obj_type=wiki',
        headers={'Authorization': f'Bearer {tenant_token}'},
        method='GET'
    ), timeout=10
)
wiki_data = json.loads(wiki_resp.read())
obj_token = wiki_data['data']['node']['obj_token']  # docx document ID

# Step 3: 读取 docx 原始内容（正确端点）
doc_resp = urllib.request.urlopen(
    urllib.request.Request(
        f'https://open.feishu.cn/open-apis/docx/v1/documents/{obj_token}/raw_content',
        headers={'Authorization': f'Bearer {tenant_token}'},
        method='GET'
    ), timeout=15
)
doc_data = json.loads(doc_resp.read())
content = doc_data['data']['content']
print(f"Total chars: {len(content)}")
print(content)
```

## Wiki Token vs Doc Token

| 类型 | Token 示例 | 用途 |
|------|-----------|------|
| Wiki Node Token | `TsZtw6rQsigy4skZHRPceKVonVf` | Wiki 页面 URL 中的标识 |
| Docx Object Token | `Vgw4dEJNVom7YmxMCAlc1CPKnJj` | API 调用用的文档 ID |

Wiki API 返回的 `obj_token` 才是 docx API 需要的文档 ID。

## 适用场景

- 飞书 Wiki 文档内容提取
- 飞书多 Bot 跨实例协作指南等内部文档读取
- 无需登录浏览器，直接 API 读取

## 限制

- 需要飞书应用具备文档读取权限
- 仅返回纯文本，不保留格式
