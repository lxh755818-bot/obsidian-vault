# Stash Diff 手工合并技术（Python 版）

> 当 `git apply` 或 `git stash pop` 因行号偏移失败时，用 Python 字符串替换手工合并 stash 改动。

## 触发条件

两个 Agent 从同一 base commit 分别修改了同一文件的相同区域，生成两个冲突的 stash。特征：

```
error: patch does not apply
# 或
error: while searching for:
        f'[SYSTEM: The user has invoked the "{skill_name}" skill, indicating they want '
error: agent/skill_commands.py: patch does not apply
```

## 根因

`git apply` 是上下文敏感的（context-sensitive）：每个 hunk 依赖精确的行号和上下文行（`@@ -621,8 +621,10 @@` 中的数字）。如果目标文件在你创建 stash 后有过任何改动（即使是注释、空白行），上下文行数就会偏移，hunk 就匹配不上。

## 标准合并流程

### Step 1：读取 stash 内容

```python
import subprocess

stash_text = subprocess.run(
    ['git', 'stash', 'show', '-p', 'stash@{0}'],
    capture_output=True, text=True,
    cwd='/data/data/com.termux/files/home/hermes-agent'
).stdout
```

### Step 2：确认 base commit

两个冲突的 stash 一定从**同一个 base** 分支。确认方法：

```bash
git log --oneline stash@{0} -3
git log --oneline stash@{1} -3
git merge-base stash@{0} stash@{1}   # 应该是同一个 commit hash
```

### Step 3：确认哪些文件被修改

```python
files = {}
for line in stash_text.split('\n'):
    if line.startswith('diff --git a/'):
        # 提取 b/ 路径（目标文件）
        b_path = line.split(' b/')[1].split()[0]
        files[b_path] = ''
    elif files:
        files[list(files.keys())[-1]] += line + '\n'
```

### Step 4：逐文件手工合并

对每个被修改的文件：

1. **读取当前文件内容**（working tree 状态，即已经包含 stash 改动的状态）
2. **从 stash 提取 new block**（`+` 开头的行，去掉 `+` 前缀）
3. **在当前文件中找到对应的 old block**（`-` 开头的行或上下文注释）
4. **用 new block 替换 old block**

```python
# 典型模式
new_block = '''    # Measure tool dispatch latency so post_tool_call and
    # transform_tool_result hooks can observe per-tool duration.
    _dispatch_start = time.monotonic()
    if function_name == "execute_code":'''

old_block = '''    # Measure tool dispatch latency so post_tool_call and
    # transform_tool_result hooks can observe per-tool duration.
    # Inspired by Claude Code 2.1.119, which added ``duration_ms`` to
    # PostToolUse hook inputs so plugin authors can build latency
    # dashboards, budget alerts, and regression canaries without having
    # to wrap every tool manually.  We use monotonic() so the value is
    # unaffected by wall-clock adjustments during the call.
    _dispatch_start = time.monotonic()
    if function_name == "execute_code":'''

if old_block in content:
    content = content.replace(old_block, new_block)
    print("SUCCESS: replaced block")
else:
    print("FAIL: exact match not found")
```

### Step 5：验证语法正确

```bash
python3 -c "import model_tools; print('OK')"
python3 -c "from agent.skill_commands import build_skill_invocation_message; print('OK')"
```

### Step 6：git commit（不 stash pop）

**关键**：手工合并后，working tree 已经包含 stash 的内容，**不需要** `git stash pop`。

```bash
git add <已合并的文件>
git commit -m "feat: 合并刘大虾的 observer/instinct hooks"

# 丢弃 stash（内容已经合并进去，不需要 pop）
git stash list
git stash drop   # 或 git stash drop stash@{N}
```

## 常见陷阱

### 陷阱 1：文件已有部分改动但并非完整 stash 状态

某些文件可能已经被更新（如 feishu.py 已有真实 handler，而 stash 里是 stub）。这种情况需要**交叉比对**：

- 如果当前文件改动和 stash 一致 → 跳过该文件
- 如果当前文件没有这个改动 → 手工注入

### 陷阱 2：多文件同时修改时的交叉依赖

observer/instinct 改动的 6 个文件可能互相引用（如 plugins.py 注册了新 hook，model_tools.py 调用它）。合并时必须**一次性验证所有文件的 import 链**：

```bash
python3 -c "
from hermes_cli.plugins import VALID_HOOKS
from hermes_agent.skill_chain import build_pre_task_prompt
from plugins.observer import on_session_start
from plugins.verification import on_pre_tool_verification
print('All imports OK')
"
```

### 陷阱 3：Stub 模块缺失

手工合并后，如果代码引用了不存在的模块（如 `hermes_agent.skill_chain`），会导致 import 错误。**先创建 stub**，再合并引用它的代码：

```python
# 先创建 stub
with open('hermes_agent/skill_chain.py', 'w') as f:
    f.write('def build_pre_task_prompt(): return ""\n')
    f.write('def after_skill_loaded(name): return ""\n')
```

## 什么时候选择「不合并」

如果改动的文件太多（如 main.py 有 8 个 hunk，200+ 行新命令），手工注入风险高且容易出错。可以：

1. Commit 已合并的部分（model_tools, plugins, skill_commands, run_agent）
2. 对 main.py 的 CLI 命令：**单独创建一个 commit message 记录**（说明 TODO），后续作为独立任务处理
3. 这样保证系统处于**可验证的稳定状态**

## 判断标准总结

| 情况 | 正确处理 |
|------|---------|
| `git apply` 失败，行号偏移 | 用 Python 字符串替换手工合并 |
| 多个 stash 冲突 | 确认 base commit，逐文件交叉合并 |
| 手工合并后文件已包含 stash 内容 | 直接 `git add + commit`，不要 `stash pop` |
| 某文件已有部分 stash 改动 | 跳过该文件，只合并缺失部分 |
| 改动文件太多（>5 个）且有交叉依赖 | 分批 commit，先保证核心链可 import |

## 为什么不用 `git merge` 或 `git rebase`？

当两个 stash 从同一 base 修改了**相同文件的相同区域**，`git merge` 会产生三方冲突（3-way merge），但 Git 的 merge algorithm 对这种上下文敏感的 patch 冲突判断不准确。更直接的方式是**读懂两个版本的差异，用字符串替换显式合并**。
