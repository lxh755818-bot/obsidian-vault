# Ralph Iteration.py 架构演进记录

## 2026-04-30: 从裸 API 到 hermes chat

### 核心问题

ralph_iteration.py 的 ACTOR 最初调 MiniMax Messages API，sub-agent 是"盲写代码"模式：
- 无法读取现有代码库
- 无法运行测试验证
- 无法探索项目结构
- 纯文本输出，解析器脆弱

结果：learnings 全是 fallback 的泛泛之谈，stories 通过率 0%。

### 解决方案：hermes chat -t terminal

```
hermes chat -q @prompt_file -t terminal \
  --yolo --ignore-user-config --ignore-rules --max-turns 30
```

sub-agent 现在有完整的 terminal + file 工具：
- `cd && cat` 读现有代码
- `python && pytest` 运行测试
- `git commit` 提交改动
- 能感知项目真实状态，不是在真空中写代码

### 验证结果（US-996 E2E Test）

```
pass: true ✅
files: ralph_test.py, test_ralph_test.py (真实创建)
learnings: 10条真实 lessons
pytest: 2/2 passed
TERMINATE_SUCCESS
```

### 关键坑：TUI 输出格式导致解析器失效

hermes TUI 渲染后输出含 ANSI 颜色码和 box-drawing 字符，但真正的问题是**缩进**：

```
    [DONE]
    story_id: US-997
    pass: true
    files: [ralph_test.py]
    learnings: [
      item1,
      item2
    ]
```

字段前有 4 空格缩进，`^pass:` 的 `^` 锚点匹配失败。

**修复方案：**

```python
# 错误
pattern = rf"^{key}:\s*(true|false|...)"  # ^ 要求行首

# 正确
pattern = rf"(?:^|\n)\s*{key}:\s*(true|false|...)"  # 允许前面有空格
```

多行 bracket 列表同理，`[^\]]*` 只能匹配单行内容：

```python
# 错误
pattern = rf"{key}:\s*\[([^\]]*)\]"  # 遇到换行就停了

# 正确：bracket-matching 循环
depth = 0
for i, ch in enumerate(chars):
    if ch == '[': depth += 1
    elif ch == ']':
        depth -= 1
        if depth == 0: end_pos = i; break
```

### 工作流程

1. 写 PRD → `prd.json`
2. 触发 `python3 .hermes/scripts/ralph_iteration.py`
3. ACTOR 生成 prompt file → 调用 `hermes chat`
4. hermes sub-agent 用工具执行 story
5. 解析 stdout 的 `[DONE]` 块
6. 更新 `prd.json` + `progress.txt`
7. push 到 kk repo

### 与 kk repo 同步

ralph_iteration.py 在 `~/.hermes/scripts/`，但 kk repo 在 `~/.hermes/tmp/kk_repo/.hermes/scripts/`。
每次改完必须：

```bash
cp ~/.hermes/scripts/ralph_iteration.py ~/.hermes/tmp/kk_repo/.hermes/scripts/
cd ~/.hermes/tmp/kk_repo && git add . && git commit -m "fix(ralph): ..." && git push
```

否则下次 pull 还是旧版本。
