# 飞书卡片设计参考 (2026-05-01)

## CardKit 2.0 API 关键限制

### note 元素 — 不支持

**CardKit 2.0 已移除 `note` 组件**。官方替代方案：

```json
{
  "tag": "plain_text",
  "content": "备注信息",
  "text_size": "small",
  "color": "grey"
}
```

用 `plain_text` + `grey` 颜色 + `icon` 属性模拟。不可使用 `{"tag": "note", "elements": [...]}` 结构。

**来源**: https://open.feishu.cn/document/feishu-cards/card-components/content-components/note

### Markdown 元素 — 有限支持（实测验证，2026-05-01）

CardKit markdown 支持部分 GitHub Flavored Markdown。以下结论均经过**实际飞书 DM 发卡 + 截图分析**验证：

| 支持 | 不支持 | 备注 |
|------|--------|------|
| `**粗体**` | 连续4个 `*` 加粗 | |
| `` `行内代码` `` | HTML5 标签如 `<details>`/`<summary>` | ❌ 折叠标签直接显示为纯文本，很丑 |
| 代码块 ` ```lang ` | | ✅ 支持，有语法高亮 |
| `- 无序列表` / `1. 有序列表` | | ✅ 序号蓝色，有缩进 |
| `| col1 \| col2 |` Markdown 表格 | | ✅ 正常渲染成表格 |
| `:emoji_name:` Feishu emoji shortcode | | ✅ 自动渲染成 emoji |
| 裸 emoji | | ✅ 也正常显示 |

**折叠方案结论**：`<details>` / `<summary>` 在飞书卡片中 **不渲染为折叠**，标签直接显示为纯文本。**不要在飞书卡片中使用 HTML 折叠标签。** 替代：用分区标题 + 水平分割线组织内容。

### Header template 可用颜色

```
red, grey, blue, purple, green, yellow, orange, turquoise, indigo, violet, lime, wathet, carmine, red_wathet
```

状态映射推荐：
```
thinking  → indigo
answering → blue  
completed → green
failed    → red
```

---

## 卡片结构设计原则

### 推荐布局（当前最佳实践）

```
┌─ Header: 状态色 + "思考中/生成中/已完成"
├─ 💭 思考过程（独立 markdown 块，限300字）
├─ ✨ 回答（独立 markdown 块）
├─ 🔧 工具调用 N次
│    ✅ `tool_name` — 已完成
│    ⏳ `tool_name` — 运行中
├─ hr 分割线
└─ footer: 耗时 · 模型 · ↑token · ↓token · ctx %
```

### emoji 在飞书卡片的注意事项

飞书对 emoji 的支持较好，但注意：
- 避免连续叠加 emoji（如 `✅🔧` 容易在部分客户端错位）
- 推荐在 emoji 后加空格或用 `—` 连接
- 长度控制：单行不超过飞书卡片宽度

### 长文本分段

`render.py` 中 `MAIN_CONTENT_CHUNK_CHARS = 2400`，超过的文本会自动分割为多个 `markdown` element，用不同 `element_id` 标识。飞书 `update_multi: true` 支持增量更新每个 element。

---

## Python 3.13 json.dumps surrogate 编码问题

**症状**: `json.dumps(card, ensure_ascii=False)` 抛出 `UnicodeEncodeError: surrogates not allowed`

**原因**: Python 3.13 对包含 emoji 的字符串做 JSON 序列化时，如果字符串含有 Unicode surrogate code point，会在 `ensure_ascii=False` 路径触发编码器校验失败。

**影响**: 在 Termux (Python 3.13) 环境中无法通过终端/echo 输出包含 emoji 的 JSON，难以预览卡片渲染结果。

**临时方案**:
```python
import re
card_str = json.dumps(card, ensure_ascii=False)
card_str = re.sub(r'[\ud800-\udfff]', '?', card_str)
```

**或用 execute_code 工具**（沙盒隔离，无 surrogate 问题）做预览。

---

## 真实 DM chat_id (2026-05-01 实测)

```
chat_id: oc_2e5cc02fdda5aef65a7f9ca03127eda5
用户: 刘小豪
```

发送测试卡片到 DM 的 API 调用：
```python
payload = {
    "receive_id": "oc_2e5cc02fdda5aef65a7f9ca03127eda5",
    "msg_type": "interactive",
    "content": card_json_str,  # json.dumps(card, ensure_ascii=False)
}
# POST https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id
# Header: Authorization: Bearer {tenant_access_token}
```

---

## 飞书卡片迭代工作流

当需要改进卡片设计或测试新元素时，使用以下工作流：

```
1. 在 execute_code 中构建测试卡片 JSON
2. 直接发到飞书 DM（chat_id: oc_2e5cc02fdda5aef65a7f9ca03127eda5）
3. 截图或查看飞书渲染效果
4. 如需视觉分析：保存截图到 ~/.hermes/cache/images/
   → 用 mcp_minimax_understand_image 分析截图
5. 根据结果更新 render.py
6. 提交推送
```

**注意**：由于 Python 3.13 surrogate 编码问题，在 `execute_code` 工具内构建和发送卡片最可靠，避免终端编码错误。

## render.py 美化改动记录 (2026-05-01)

分支: `feat/card-beautify`

**改动目标**: 改进卡片信息层次，提升可读性

**核心变化**:
1. 思考内容与回答内容分离，不再混在一个 markdown 块
2. 思考区用 emoji 标题 `💭 思考过程` 标识
3. 回答区用 `✨ 回答` 标题标识
4. 工具调用区用 `🔧 工具调用` 标题 + emoji 图标 + 状态标签
5. 状态映射：`thinking→indigo / answering→blue / completed→green / failed→red`

**待改进项（已更新 2026-05-01）：**
- ~~`<details>` 折叠标签不支持~~ → ❌ 已确认不支持，不要用
- 工具调用区改用 Markdown 表格 ✅ 已实现
- emoji 分区标题（💭/✨/🔧） ✅ 已实现
- footer 改用 English 标签（IN/OUT/CTX） ✅ 已实现
- 状态 subtitle 改用 English ✅ 已实现
