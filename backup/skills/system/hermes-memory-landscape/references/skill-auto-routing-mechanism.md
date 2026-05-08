# Source: `skill-auto-routing-mechanism`

---
name: skill-auto-routing-mechanism
description: Hermes skill 自动路由机制——gateway/skill_router.py 在消息入口自动匹配相关 skill
---

# Skill 自动路由机制

## 架构

- **gateway/skill_router.py**：实现自动路由（match_skills + 索引构建）
- 集成在 `gateway/run.py` 的 `_handle_message()` 入口（line 3226）
- 消息进来时自动检索相关 skill 并注入 context

## 路由原理

### 匹配维度
1. **media_types**（主要）：skill 声明 `media: [image, photo, picture, ...]`，图片/音频/视频消息直接命中
2. **trigger_words**（辅助）：从 skill body 提取关键词做 TF-IDF 评分

### 关键发现
- `trigger` 字段**只是文档**，不参与自动匹配
- `extract_skill_trigger_words` 对 CJK 文本有 n-gram 切分 bug（"分析图片"被切成无意义字符），**不影响路由**
- 路由主要靠 `media_types` 字段匹配，这是正确的设计

### Skill 注册格式
```yaml
media: [image, photo, picture, screenshot, jpg, png, webp]
trigger: 分析图片, 识别图片, 图片理解, ...
```

## 验证结果（2026-04-26）

| 测试场景 | 输入 | 结果 |
|----------|------|------|
| 纯图片 | `media=["img_xxx.jpg"]` | `['mcp-image-understanding']` ✓ |
| 图片+文字 | `"看看这张图"` + 图片 | `['mcp-image-understanding']` ✓ |

## 限制

- 不支持纯文字指令（如"分析图片"）的自动路由（trigger 提取 bug 严重）
- 图片消息自动路由**完全正常**

## 图片理解正确执行方式

收到图片任务时，必须：
1. `skill_view("mcp-image-understanding")` 加载 skill
2. 按 skill 推荐的 **直接 API 调用**方式执行（不走 MCP）
3. 不瞎猜方法
