---
name: feishu-search-messages
description: 搜索飞书群聊历史消息 — 用 lark-oapi im.v1 ListMessage API，支持关键词过滤、分页、排序。
version: 1.0.0
author: 小哈
license: MIT
dependencies: [lark-oapi]
metadata:
  hermes:
    tags: [feishu, messaging, search, history]
    platform: tool
---

# feishu-search-messages

搜索飞书群聊历史消息，支持关键词过滤、分页和时间范围。

## 核心 API

`ListMessageRequest` — 飞书消息列表接口

```
GET /open-apis/im/v1/messages
```

关键参数：
- `container_id_type`: `"chat"`（固定）
- `container_id`: 群 chat_id（如 `oc_5e9d682887056b9aa5db3bff44b743ff`）
- `start_time` / `end_time`: 秒级时间戳（可选）
- `sort_type`: `"ByCreateTimeDesc"`（最新优先）或 `"ByCreateTimeAsc"`（最早优先）
- `page_size`: 每页条数（最大 50）
- `page_token`: 分页令牌

**注意**：飞书 ListMessage API **不支持关键词搜索**，需客户端过滤。

## Tool 实现模式

参考 `tools/feishu_doc_tool.py` 的 thread-local client 模式：

```python
import threading
_local = threading.local()

def set_client(client):
    _local.client = client

def get_client():
    return getattr(_local, "client", None)

def _handle_feishu_search_messages(args, **kwargs) -> str:
    client = get_client()
    if client is None:
        return tool_error("Feishu client not available")
    
    from lark_oapi.api.im.v1 import ListMessageRequest
    from lark_oapi import AccessTokenType
    from lark_oapi.core.enum import HttpMethod
    from lark_oapi.core.model.base_request import BaseRequest
    
    request = (
        BaseRequest.builder()
        .http_method(HttpMethod.GET)
        .uri("/open-apis/im/v1/messages")
        .token_types({AccessTokenType.TENANT})
        .queries({
            "container_id_type": "chat",
            "container_id": args["chat_id"],
            "sort_type": args.get("sort_type", "ByCreateTimeDesc"),
            "page_size": min(args.get("page_size", 20), 50),
            "page_token": args.get("page_token") or None,
        })
        .build()
    )
    response = client.request(request)
    # ... parse and filter by keyword
```

## Tool Schema

```json
{
  "name": "feishu_search_messages",
  "description": "搜索飞书群聊历史消息。支持关键词过滤、分页、时间范围。",
  "parameters": {
    "type": "object",
    "properties": {
      "chat_id": {
        "type": "string",
        "description": "群 chat_id（如 oc_5e9d682887056b9aa5db3bff44b743ff）。可在飞书群设置里找到，或留空使用默认群。"
      },
      "keyword": {
        "type": "string",
        "description": "关键词，消息内容包含该词才返回（大小写不敏感）。空则返回所有消息。"
      },
      "limit": {
        "type": "integer",
        "description": "最多返回多少条消息（客户端过滤后），默认 20，最大 200。"
      },
      "sort_type": {
        "type": "string",
        "enum": ["ByCreateTimeDesc", "ByCreateTimeAsc"],
        "description": "排序：最新优先（默认）或最早优先。"
      },
      "start_time": {
        "type": "string",
        "description": "开始时间（秒级时间戳字符串），可选。"
      },
      "end_time": {
        "type": "string",
        "description": "结束时间（秒级时间戳字符串），可选。"
      },
      "page_token": {
        "type": "string",
        "description": "分页令牌（从上次返回的 has_more=True 时获取），可选。"
      }
    }
  }
}
```

## 注册方式

在 `tools/registry.py` 或 gateway 启动时调用：

```python
from tools.feishu_search_messages_tool import registry_register
registry_register(registry)
```

需要 gateway 启动时调用 `set_client(client)` 注入 lark client。

## 已知群 chat_id

| 群名 | chat_id |
|------|---------|
| 刘氏三虾 | `oc_5e9d682887056b9aa5db3bff44b743ff` |
| 虾聊 | `oc_95de282773725f83cbdfb2874bf365f1` |

## 权限要求

飞书应用需要开通 `im:message` 或 `im:message.read` 权限。
