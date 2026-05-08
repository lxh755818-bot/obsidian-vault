# Source: `minimax-vl-api-debug`

---
name: minimax-vl-api-debug
description: MiniMax VL (Vision) API 调试记录 — 2026-04-25
version: 1.0.0
author: 小a
tags: [minimax, vision, debug]
---

# MiniMax VL API 调试记录

## 问题

用户发送图片，想用 MiniMax VL 分析图片内容。两种方式都失败：

1. **MCP tool `mcp_minimax_understand_image`** → 返回 `login fail: Please carry the API secret key`
2. **Direct API call** → 尝试多个端点都返回 404

## 尝试过的端点（全部失败）

```
https://api.minimaxi.com/v1/vision        → 404
https://api.minimaxi.com/v1/vl            → 404
https://api.minimax.com/v1/vision          → SSL EOF
```

## 可能的解决方案

1. **MCP tool 认证问题**：MCP server 的 API key 配置可能有问题，不是用户凭证问题
2. **端点可能已变更**：MiniMax VL API 端点可能不是 `/vision` 或 `/vl`
3. **尝试正确的端点格式**

## 工作around

当 MiniMax VL 不可用时：
1. 用其他 VLM API（如 OpenAI GPT-4V，如果可用）
2. 让用户描述图片内容

## 待排查

- [ ] 确认 MiniMax VL-01 的正确 API 端点
- [ ] 检查 MCP server 的认证配置
- [ ] 确认 API key 是否有 vision 权限

## 已知失败的调用（2026-04-25）

```
MCP: mcp_minimax_understand_image
  → API Error: login fail (认证问题)

Direct calls to:
  - api.minimaxi.com/v1/vision → 404
  - api.minimaxi.com/v1/vl → 404
  - api.minimax.com/v1/vision → SSL EOF
```

## 新发现（2026-04-26）

**本地 Hermes API 转发也无法处理 vision**：
- 路径：`POST http://127.0.0.1:8642/v1/chat/completions`
- 方式：`{"content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}]}`
- 结果：模型回复"图片没有成功加载"/"看不到图片"
- 原因：本地 API 转发给 MiniMax 时，vision 数据格式可能不兼容

**飞书缓存图片格式问题**：
- 飞书发送的图片存为 `.jpg` 但实际是 WebP 格式
- `file` 工具保存后扩展名不反映真实格式
- 需按文件头判断：`RIFF + WEBP` = WebP，`\xff\xd8` = JPEG，`\x89PNG` = PNG

**当前可用的图片分析方式**：
- 飞书原生支持：用户直接在飞书里@我发图片，飞书自动渲染我能看到
- 终端直接发送：图片作为附件发送，我能通过飞书消息直接查看

## 待排查

- [ ] 确认 MiniMax VL-01 的正确 API 端点
- [ ] 检查 MCP server 的认证配置（API key 可能过期）
- [ ] 确认 API key 是否有 vision 权限
- [ ] 本地 API 转发的 vision 兼容性问题
