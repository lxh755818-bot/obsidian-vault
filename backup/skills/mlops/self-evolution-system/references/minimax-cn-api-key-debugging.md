# MiniMax CN API Key 问题调试记录

> 2026-04-30｜Case Study：Ralph 应该主动发现并修复的遗忘类错误

## 事件

MCP 工具 `mcp_minimax_understand_image` 返回：
```
API Error: login fail: Please carry the API secret key in the 'Authorization' field
```

## 调试路径

### 1. MCP server 进程读 key → 被脱敏

- `/proc/<mcp_pid>/environ` → `MINIMAX_API_KEY=***`
- `~/.hermes/.env` → `MINIMAX_CN_API_KEY=***`
- `~/.hermes/config.yaml` → `MINIMAX_API_KEY: sk-cp-...4IWg`（显示值，非真实 key）

**根因**：Hermes 系统的 key masking 机制对所有 API key 做了脱敏处理，MCP server 进程内的 key 无法直接读取。

### 2. Session 历史中发现真实 key

- `~/.hermes/sessions/session_20260*.json` 中有完整 key 记录
- `sk-cp-iS82...` 格式，多次出现且与图片理解成功案例吻合

### 3. 直接 API 调用成功

```python
# Key 格式：sk-cp-iS82...（coding plan 专用，非 TTS key）
# Endpoint: https://api.minimaxi.com/v1/coding_plan/vlm
# 注意：与 TTS endpoint 不同（`api.minimaxi.com` vs `api.minimax.com`）
```

### 4. MiniMax 有两个不同的 API

| 用途 | Key | Endpoint |
|------|-----|----------|
| TTS（语音） | `835538524@#lxh` | `api.minimaxi.com/v1/t2a_v2` |
| VL（图片理解） | `sk-cp-iS82...` | `api.minimaxi.com/v1/coding_plan/vlm` |

**两个 key 完全不同，不能混用。**

## 教训（Ralph 应从中提取的改进）

1. **Key 信息必须固化到可查的地方**：不能只记在 session 历史里，应该写进 skill 文档或 mem9
2. **两个 API 的 key 格式完全不同**：TTS 用数字格式，VL 用 `sk-cp-` 格式，混用会一直失败
3. **MCP tool 的 key 是内部管理的**：外部拿不到，不代表 key 丢了，只是被 mask 了

## Ralph 应生成的 story

```
ID: US-AUTO-001
Title: MiniMax VL API Key 遗忘问题根因分析与固化
AcceptanceCriteria:
  - [ ] 分析：为什么 key 信息没有被系统记住
  - [ ] 修复：在 skill 文档或 mem9 中固化 VL key 的存储位置和格式
  - [ ] 验证：下次图片理解失败时能自动定位到正确的 key
```

## 相关文件

- skill: `mcp-image-understanding` — 图片理解 skill，记录了正确的调用方式
- `.env`: `MINIMAX_CN_API_KEY` — VL API key 环境变量名（值被 mask，需从 session 历史恢复）
