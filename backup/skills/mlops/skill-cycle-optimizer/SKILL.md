---
name: skill-cycle-optimizer
description: 技能循环优化自进化技能。每2小时测试一个已注册技能，执行完整的评估审核流程，监控性能变化，输出优化建议和报告。
version: 1.1.0
author: 小哈
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [Self-Evolution, Performance, Skill Testing, Cron]
    cron_schedule: "0 */2 * * *"
---

# 技能循环优化

## 核心原则

**每次只测试一个技能，严格按顺序循环，不一次测多个。**

每次测试必须产生实际、可量化的评估结果，包含完整的审核流程。

---

## 触发条件

- **Cron 表达式**: `0 */2 * * *`（每2小时）
- **手动触发**: `cronjob action=run job_id=<任务ID>`

---

## 执行流程

### 第一步：读取进度

读取 `~/.hermes/evolution_logs/skill_optimizer/state.json`：

```json
{
  "last_skill_index": 5,
  "total_skills": 83,
  "last_run": "2026-04-17T08:00:00"
}
```

如果文件不存在，初始化为 `last_skill_index: -1`。

### 第二步：确定本次技能

```
next_index = (last_skill_index + 1) % total_skills
```

扫描 `~/.hermes/skills/` 下所有 `SKILL.md` 并排序（使用 `Path.rglob` 递归扫描），得到技能列表：

```python
from pathlib import Path

hermes_home = Path.home() / ".hermes"
skills_dir = hermes_home / "skills"

# 递归扫描所有 SKILL.md
all_skills = []
for md_path in sorted(skills_dir.rglob("SKILL.md")):
    rel = md_path.relative_to(skills_dir)
    category = str(rel.parent)  # e.g. "apple/imessage"
    all_skills.append((category, md_path))

all_skills.sort(key=lambda x: x[0])
total_skills = len(all_skills)
# 技能索引: all_skills[next_index] = (category, md_path)
```

### 第三步：技能类型评估（修复版）

读取技能的 `SKILL.md`，根据 YAML frontmatter metadata.tags 判断类型：

```python
import yaml

def parse_frontmatter(skill_md_path):
    """正确解析 SKILL.md 的 YAML frontmatter"""
    with open(skill_md_path) as f:
        content = f.read()
    if not content.startswith("---"):
        return None, content
    end_idx = content.find("\n---\n", 3)
    if end_idx == -1:
        end_idx = content.find("\n--", 3)
        if end_idx == -1:
            return None, content
    yaml_text = content[3:end_idx].strip()
    body = content[end_idx+4:]
    try:
        frontmatter = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return None, content
    return frontmatter, body

def get_skill_type(skill_md_path):
    """根据 frontmatter metadata.tags 正确判断技能类型"""
    fm, _ = parse_frontmatter(skill_md_path)
    if fm is None:
        return "sandbox"
    tags = fm.get("metadata", {}).get("hermes", {}).get("tags", [])
    if not isinstance(tags, list):
        tags = []
    tags_str = " ".join(tags).lower()

    if "jupyter" in tags_str or "kernel" in tags_str or "notebook" in tags_str:
        return "jupyter"
    elif "api" in tags_str:
        return "api"
    elif "cli" in tags_str or "command" in tags_str:
        return "cli"
    elif "file" in tags_str or "parser" in tags_str:
        return "file_parser"
    elif "pdf" in tags_str or "document" in tags_str or "ocr" in tags_str or "text-extraction" in tags_str:
        return "file_parser"
    elif "integration" in tags_str or "platform" in tags_str:
        return "integration"
    elif "code" in tags_str or "generation" in tags_str:
        return "code_gen"
    else:
        return "sandbox"
```

**技能类型说明：**
- `jupyter`：Jupyter 内核类技能（hamelnb），不检查 API key
- `api`：调用外部 API 的技能
- `cli`：依赖本地命令的技能
- `file_parser`：解析文件的技能
- `integration`：平台集成类技能
- `code_gen`：代码生成类技能
- `sandbox`：其他沙箱类技能

### 第四步：文档完整性审核

正确解析 YAML frontmatter（`---` 分隔符之间的内容），然后检查必要字段：

```python
import yaml, re

def parse_frontmatter(skill_md_path):
    """正确解析 SKILL.md 的 YAML frontmatter"""
    with open(skill_md_path) as f:
        content = f.read()
    
    if not content.startswith("---"):
        return None, content
    
    # 找到第二个 --- 的位置（YAML 结束标记）
    end_idx = content.find("\n---\n", 3)
    if end_idx == -1:
        # 可能 frontmatter 一直延续到文件末尾（无 body）
        end_idx = content.find("\n---", 3)
        if end_idx == -1:
            return None, content
    
    yaml_text = content[3:end_idx].strip()
    body = content[end_idx+4:]
    
    try:
        frontmatter = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return None, content
    
    return frontmatter, body

def audit_doc_complete(skill_md_path):
    """审核文档完整性"""
    fm, body = parse_frontmatter(skill_md_path)
    
    if fm is None:
        return False, "无法解析 YAML frontmatter"
    
    name = fm.get("name", "")
    desc = fm.get("description", "")
    has_name = bool(name and str(name).strip())
    has_desc = bool(desc and len(str(desc).strip()) > 10)
    
    # body 也要有实质内容（至少 50 字符）
    has_body = len(body.strip()) >= 50
    
    doc_complete = has_name and has_desc and has_body
    
    return doc_complete, {
        "has_name": has_name,
        "has_description": has_desc,
        "has_body": has_body,
        "name": name,
        "description": desc[:50] + "..." if len(str(desc)) > 50 else desc
    }
```

评分：`doc_complete_pass: bool`

**正确解析逻辑：**
1. 文件必须以 `---` 开头
2. 找到第一个换行后的第二个 `---` 作为结束标记
3. 取两个 `---` 之间的内容作为 YAML
4. 用 `yaml.safe_load` 解析
5. 检查 `name` 非空、`description` > 10 字符、`body` >= 50 字符

### 第五步：依赖可用性审核（修复版）

根据技能类型检查依赖：

| 类型 | 检查方式 |
|------|---------|
| `api` | 检查 `MINIMAX_API_KEY` / `OPENAI_API_KEY` 等环境变量 |
| `cli` | 用 `shutil.which` 检查命令是否存在 |
| `file_parser` | 检查文件路径是否可读 |
| `integration` | 检查平台相关环境变量或配置 |
| `jupyter` | 检查 hamelnb 脚本路径 `$HOME/.agent-skills/hamelnb/` 是否存在 |
| `sandbox` | 检查必要目录是否存在 |
| `code_gen` | 检查代码生成相关依赖 |

**注意**：`jupyter` 类型不检查任何 API key 环境变量，因为它是本地 Jupyter 连接工具。

### 第六步：执行测试

根据技能类型执行实际测试：

#### `api` 类型
```python
import time
t0 = time.time()
try:
    if skill == "minimax-image-generation":
        result = minimax_image_generate("test prompt", aspect_ratio="1:1")
        result_data = json.loads(result)
        success = result_data.get("success", False)
        output_valid = "image" in result_data
    # 其他 API 技能类似
except Exception as e:
    success = False
    error = str(e)
latency_ms = int((time.time() - t0) * 1000)
```

#### `cli` 类型
```python
import subprocess, shutil
cmd = skill_config.get("command", skill_name)
t0 = time.time()
success = None
output_valid = False  # 必须无条件初始化，避免跨调用 NameError
error = ""

if shutil.which(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
        exit_code = result.returncode
        success = exit_code == 0
        output_valid = success
        error = "" if success else result.stderr.decode()[:100]
    except subprocess.TimeoutExpired:
        success = False
        error = "timeout"
    except Exception as e:
        success = False
        error = str(e)
else:
    # 命令不存在 → expected_fail，不阻塞流程
    success = None
    error = f"{cmd} not installed"
    output_valid = False

latency_ms = int((time.time() - t0) * 1000)
```

#### `file_parser` 类型
```python
import time
t0 = time.time()
with open(skill_path) as f:
    content = f.read()
    parsed = yaml.safe_load(content)  # 尝试解析
success = parsed is not None
latency_ms = int((time.time() - t0) * 1000)
output_valid = "name" in parsed if parsed else False
```

#### sandbox / integration 类型
使用 `parse_frontmatter()` 解析（不能用 `yaml.safe_load(content)` 直接加载整个文件——SKILL.md 可能有多个 YAML 文档，第二个 `---` 后的内容会导致 "expected a single document" 解析错误）：

```python
# ✅ 正确：用 parse_frontmatter 提取第一个 YAML 文档
fm_test, body_test = parse_frontmatter(skill_md_path)
output_valid = fm_test is not None and isinstance(fm_test, dict)
success = output_valid

# ❌ 错误：直接 yaml.safe_load(content) 会因多文档而失败
# parsed = yaml.safe_load(content)  # "expected a single document" error
```

#### 其他类型
执行通用测试：读取文件 + 基础验证

### 第七步：性能稳定性审核

读取 `trends.json` 中该技能的历史数据：

```python
history = [r for r in trends.get("records", []) if r["skill"] == current_skill]
if history:
    last = history[-1]
    delta_pct = (latency_ms - last["latency_ms"]) / last["latency_ms"] * 100
    if abs(delta_pct) <= 10:
        perf_stable = "stable"
    elif delta_pct > 10:
        perf_stable = "degraded"
    else:
        perf_stable = "improved"
```

| 状态 | 判断标准 |
|------|---------|
| `stable` | 变化 ≤ ±10% |
| `degraded` | 变慢 > 10% |
| `improved` | 变快 > 10% |

### 第八步：错误率审核

统计该技能历史记录中的错误：

```python
total_runs = len([r for r in history if r.get("skill") == current_skill])
# 用 classify_run()（见 Bug 7）判断，不依赖 status 字符串
error_runs = len([r for r in history if classify_run(r) == "unexpected_fail"])
error_rate = (error_runs / total_runs * 100) if total_runs > 0 else 0
```

| 错误率 | 评分 |
|--------|------|
| 0% | pass |
| < 5% | warning |
| >= 5% | fail |

### 第九步：生成完整审核报告

```json
{
  "task": "skill_cycle_optimizer",
  "timestamp": "2026-04-17T08:00:00",
  "current_index": 5,
  "total_skills": 83,
  "current": {
    "skill": "minimax-image-generation",
    "category": "media",
    "type": "api",
    "metrics": {
      "latency_ms": 8500,
      "success": false,
      "output_valid": true,
      "error": "MINIMAX_API_KEY not set"
    },
    "audit": {
      "doc_complete": "pass",
      "dep_available": "fail",
      "load_time_ms": 12,
      "error_rate_pct": 0,
      "perf_stable": "stable",
      "output_valid": true
    },
    "vs_last": null,
    "suggestions": [
      "依赖不可用: MINIMAX_API_KEY 未设置，建议配置或标记为 manual_only"
    ],
    "status": "warning"
  },
  "summary": {
    "audit_passed": 5,
    "audit_warnings": 1,
    "action": "依赖缺失，需要配置"
  }
}
```

### 第十步：保存所有数据

1. `~/.hermes/evolution_logs/skill_optimizer/current_benchmark.json`（覆盖）
2. `~/.hermes/evolution_logs/skill_optimizer/history/YYYYMMDD_HHMMSS_<skill>.json`
3. `~/.hermes/evolution_logs/skill_optimizer/trends.json`（追加）
4. `~/.hermes/evolution_logs/skill_optimizer/state.json`（更新索引）

### 第十一步：SkillTree 健康度记录

每次技能审核完成后，将结果写入 SkillTree。**必须用 try/except 包裹**（hermes_agent.evolution 在 Termux 环境下可能不可用）：

```python
import sys
sys.path.insert(0, "/data/data/com.termux/files/home/hermes-agent")

try:
    from hermes_agent.evolution import SkillTree
    st = SkillTree()
    st.record_invocation(
        skill_name=current_skill,
        success=(report["current"]["status"] in ("healthy", "warning")),
        latency_ms=latency_ms,
        tags=skill_tags,
        category=skill_category,
    )
except ImportError as e:
    print(f"SkillTree 导入失败（{e}），跳过")
except Exception as e:
    print(f"SkillTree 更新失败: {e}，跳过")
```

### 第十二步：GapAnalyzer 缺口分析

每轮技能测试后运行缺口分析，识别系统性改进机会。**必须用 try/except 包裹**：

```python
try:
    from hermes_agent.evolution import GapAnalyzer
    ga = GapAnalyzer()
    gaps = ga.run_full_analysis()
    if gaps:
        report_path = ga.save_report(gaps)
        print(f"GapAnalyzer: {len(gaps)} gaps -> {report_path}")
        critical = [g for g in gaps if g.severity in ("critical", "high")]
        for g in critical:
            print(f"  [{g.severity}] {g.title}: {g.suggested_action}")
except ImportError as e:
    print(f"GapAnalyzer 导入失败（{e}），跳过")
except Exception as e:
    print(f"GapAnalyzer 执行失败: {e}，跳过")
```

### 失败信号监控（每轮测试后执行）

每次技能测试完成后，立即运行完整的 HERMES DOJO 闭环。**优先使用手动6步模块调用**，因为 `dojo.py` 曾多次在 Step 1 后提前退出（只输出 Monitor 结果，无 Step 2-6）。

```python
import subprocess, sys
from pathlib import Path

LOG = Path.home() / ".hermes/evolution_logs/skill_optimizer"
MODULES = ["monitor.py", "analyzer.py", "fixer.py", "reporter.py", "learning_curve.py", "apply_fixes.py"]

for mod in MODULES:
    p = LOG / mod
    if p.exists():
        r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True, timeout=60)
        print(f"=== {mod} (rc={r.returncode}) ===")
        print(r.stdout[:200] if r.stdout else "(empty)")
        if r.stderr:
            print("STDERR:", r.stderr[:100])
    else:
        print(f"{mod} not found, skipping")

# 飞书推送（可选）
from hermes_tools import send_message
send_message(action="send", target="feishu", message=dojo_report_text)
```

**⚠️ 验证要求**：检查输出是否包含所有 6 个 Step 的标题（"Step 2: Analyzer"、"Step 3: Fixer" 等）。如果只看到 Monitor 输出，说明 dojo.py 未完成全部步骤，必须立即手动触发剩余模块。

**完整数据流**：
```
trends.json（测试结果） ──┐
                          ├──► Monitor ──► failure_signals.json
error_ledger.md（错误） ──┘         │
                                    ▼
                         Analyzer v2 ──► improvement_plan.json
                                                  │
                                    ┌─────────────┴─────────────┐
                                    ▼                           ▼
                          Fixer v2                         Auto-Fixer
                          fixes_pending/                  (仅 doc_fail)
                          *_diag_v2.json
                          *_fix_v2.json
                                    │                           │
                                    └───────── human review ────┘
                                                   │
                                                   ▼
                                            修复 → 重新测试 → 闭环
```

**各模块职责**：

| 模块 | 职责 | 输出文件 |
|------|------|---------|
| Monitor | 采集48h内失败信号 | `failure_signals.json` |
| Analyzer v2 | 动态评分 → 决策 | `improvement_plan.json` |
| Fixer v2 | 诊断依赖 + 方案生成 | `fixes_pending/*.json` |
| Auto-Fixer | 对 doc_fail 执行写入 | 修改 SKILL.md（需 --approve）|
| Reporter | 生成 CLI/JSON 报告 | `reports/*.txt` |
| Learning Curve | 长期趋势 + WoW 对比 | `skill_history.json` |

**决策类型与对应动作**：

| Decision | 含义 | Fixer 行为 |
|----------|------|-----------|
| `deep_review` | 运行时错误 | 输出诊断报告，跳过自动修复 |
| `new_skill` | 文档问题 | 生成修复方案（auto_fixable=doc_fail） |
| `add_rule` | 需加规则 | 写入 HEARTBEAT.md |
| `archive` | 低优先级 | 归档，仅记录 |

**已知问题**：
- `error_ledger.md` 格式变化时 Monitor 正则解析会失效
- Fixer 的 `check_python_deps` 依赖 frontmatter `dependencies` 字段，字段为空时从 body 扫描 import，准确度降低
- deep_review 类型需要 human review 后手动处理，不自动执行

---

### 情报收集查询模板

情报收集使用 `mcp_minimax_web_search` 工具执行。推荐查询组合和注意事项见 `references/intelligence-queries.md`。

> 📁 已存在：`references/intelligence-queries.md`（2026-05-04 实测有效查询 + 失败模式记录）

## 情报收集流程（index % 6 == 0 时执行）

**重要**：情报收集**不能**在 `execute_code` 中调用 MCP 工具。必须作为独立的**工具调用**执行。

当 `current_index % 6 == 0` 时，**分两步执行**：

#### 步骤 A（在 execute_code 中准备数据 + 保存占位）

```python
import json
from pathlib import Path
from datetime import datetime

hermes_home = Path.home() / ".hermes"
log_base = hermes_home / "evolution_logs" / "skill_optimizer"
intel_path = log_base / "intelligence_latest.json"
intel_path.parent.mkdir(parents=True, exist_ok=True)

# 先写入占位数据，标记为待填充
intel_data = {
    "collected_at": datetime.now().isoformat(),
    "collection_status": "pending",
    "hermes": {"stars": "", "position_trend": "", "recent_changes": []},
    "ecosystem": {"rising_stars": [], "falling": [], "new_entrants": [], "trending_topics": []},
    "insights": []
}
with open(intel_path, "w") as f:
    json.dump(intel_data, f, indent=2, ensure_ascii=False)

print(f"占位情报已保存: {intel_path}")
print("下一步: 使用 mcp_minimax_web_search 工具执行实际搜索")
```

#### 步骤 B（作为独立工具调用执行 web 搜索）

使用 `mcp_minimax_web_search` 工具对以下查询执行搜索：

1. `site:github.com/trending?since=weekly`
2. `github trending AI agent framework 2026 April`
3. `open source AI agent github stars ranking 2026`
4. `site:github.com/NousResearch/hermes-agent/releases`
5. `new AI agent framework released 2026 April`
6. `AI agent trending this week github`

每次搜索后，解析结果并更新 `intelligence_latest.json`。如果 API 返回 auth 错误，跳过该查询并记录。

#### 步骤 C（更新情报文件并执行闭环）

在 `execute_code` 中读取收集到的情报，执行 intelligence-action-loop 闭环逻辑：

```python
import json
from pathlib import Path

intel_path = Path.home() / ".hermes/evolution_logs/skill_optimizer/intelligence_latest.json"
with open(intel_path) as f:
    intel = json.load(f)

# 更新 collection_status
intel["collection_status"] = "complete"
with open(intel_path, "w") as f:
    json.dump(intel, f, indent=2, ensure_ascii=False)

# 情报闭环
from hermes_tools import skill_view
skill_view(name="intelligence-action-loop")
# 执行 intelligence-action-loop 的决策逻辑
```

**已知失败模式**：`mcp_minimax_web_search` 调用失败（auth error）时，直接跳过，不要在 `execute_code` 中尝试调用。

---

## 审核评分标准

| 审核项 | pass | warning | fail |
|--------|------|---------|------|
| `doc_complete` | 所有字段完整 | 缺少非关键字段 | 缺少 name/description |
| `dep_available` | 依赖都可用 | 部分缺失 | 核心依赖缺失 |
| `load_time` | < 500ms | 500-2000ms | > 2000ms |
| `error_rate` | 0% | < 5% | >= 5% |
| `perf_stable` | ±10% 内或变快 | - | 变慢 > 10% |
| `output_valid` | 格式正确 | - | 格式错误或空 |

**最终状态判断：**
- `healthy`：所有审核项 pass
- `warning`：有 warning 项但无 fail
- `degraded`：有 fail 项

---

## 目录结构

```
~/.hermes/evolution_logs/skill_optimizer/
├── current_benchmark.json    # 当前测试报告
├── state.json               # 进度状态
├── trends.json              # 历史趋势（30条）
├── failure_signals.json     # Monitor 输出：失败信号
├── improvement_plan.json    # Analyzer 输出：改进决策（v2 动态评分）
├── skill_history.json       # Learning Curve：每日快照时间序列
├── monitor.py              # Monitor 模块（采集失败信号）
├── analyzer.py             # Analyzer 模块（v2 动态评分）
├── fixer.py               # Fixer 模块（v2 诊断+方案生成）
├── reporter.py             # Reporter 模块（CLI/JSON/飞书卡片报告）
├── learning_curve.py       # Learning Curve 模块（WoW 趋势对比）
├── apply_fixes.py          # Auto-Fixer（实际执行 doc_fail 修复）
├── dojo.py                # 完整闭环编排（一键运行全部6步）
├── fixes_pending/          # 待审批修复方案（Fixer 输出）
│   ├── _fixer_summary_v2.json
│   ├── <skill>_diag_v2.json      # 深度检修诊断报告
│   └── <skill>_fix_v2.json       # 文档修复方案
├── reports/                # 历史日报存档
│   └── report_YYYYMMDD_HHMMSS.txt
└── backups/               # Auto-Fixer 备份（修改前快照）
    └── YYYYMMDD_HHMMSS_<skill>.md
```

~/.hermes/evolution_logs/gap_analyzer/   # GapAnalyzer 输出
~/.hermes/evolution_logs/skill_tree/     # SkillTree 健康数据
~/.hermes/evolution_logs/cost_router/    # CostAwareRouter 路由日志
```

## 注意事项

- API 技能测试可能因为缺少 key 而失败，这是**预期行为**，记录但不阻塞
- CLI 技能如果没有对应命令，标记为 `manual_only`
- 沙箱测试后清理所有临时文件
- trends.json 只保留最近 30 条记录
- 递归避免：不要对 `skill-cycle-optimizer` 本身执行实际 API 调用
- **导入新模块**时需先将 hermes-agent 路径加入 sys.path：
  ```python
  import sys
  sys.path.insert(0, "/data/data/com.termux/files/home/hermes-agent")
  from hermes_agent.evolution import GapAnalyzer, SkillTree, CostAwareRouter
  ```

---

## 已知 Bug 和修复记录

### Bug 1: YAML frontmatter 解析错误（2026-04-17）

**问题现象**: `imessage` 技能有完整的 `name:` 和 `description:`，但审核报告 `doc_complete: fail`。

**根因**: 用正则 `re.search(r'^name:\s*\S', fm_text, re.MULTILINE)` 匹配多行文本时，位置判断错误；且只读取前 5 行，无法处理不同格式。

**正确做法**:
```python
import yaml

def parse_frontmatter(skill_md_path):
    with open(skill_md_path) as f:
        content = f.read()
    if not content.startswith("---"):
        return None, content
    # 找到第二个 --- 的位置
    end_idx = content.find("\n---\n", 3)
    if end_idx == -1:
        end_idx = content.find("\n---", 3)
        if end_idx == -1:
            return None, content
    yaml_text = content[3:end_idx].strip()
    body = content[end_idx+4:]
    try:
        frontmatter = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return None, content
    return frontmatter, body
```

### Bug 2: 递归扫描技能列表遗漏（2026-04-17）

**问题现象**: 83 个技能中只扫到 1 个（dogfood），其余 82 个嵌套在子目录中的技能全部漏掉。

**根因**: 用 `skills_dir.iterdir()` 只扫描一层目录，很多技能在 `software-development/plan`、`apple/imessage` 等嵌套路径下。

**正确做法**:
```python
all_skills = []
for md_path in sorted(skills_dir.rglob("SKILL.md")):
    rel = md_path.relative_to(skills_dir)
    category = str(rel.parent)  # e.g. "apple/imessage"
    all_skills.append((category, md_path))
all_skills.sort(key=lambda x: x[0])
total_skills = len(all_skills)
```

### Bug 3: trends.json 写入 audit 字段路径错误（2026-04-17）

**问题现象**: trends.json 中每条记录的 `audit` 字段为空（`{}`），导致历史性能对比失效。

**根因**: `report["audit"]` 不存在，实际路径是 `report["current"]["audit"]`。

**正确做法**:
```python
audit_result = report["current"]["audit"]  # 不是 report["audit"]
trends["records"].append({..., "audit": audit_result})
```

### Bug 4: Cron Job 不加载更新后的 Skill 代码（2026-04-19）

**问题现象**: 更新了 skill-cycle-optimizer 的 SKILL.md 后，手动触发 cron job，情报收集轮次仍未执行。原因是 cron job 在创建时就固定了 prompt 内容，后续更新 skill 文件不会影响已创建的 job。

**解决方案**:
- 方案1：删除旧 cron job，重新创建（`cronjob remove` + 重新 `create`）
- 方案2：手动执行情报收集，将结果写入 `intelligence_latest.json`
- 方案3：创建新的独立 cron job 专门做情报收集，与技能测试分离

**验证**: 更新 skill 后检查 job 的 `prompt_preview` 是否包含新内容，或直接查看 `intelligence_latest.json` 是否更新。

### Bug 5: execute_code 跨调用状态不持久（2026-04-19）

**问题现象**: 技能执行时多次出现 `NameError: name 'xxx' is not defined`，例如 `log_base`、`current_path` 等变量在第二次 `execute_code` 调用时未定义。

**根因**: `execute_code` 每次调用都是全新 Python 进程，**所有变量和 import 均不跨调用保留**。脚本不能假设前一步定义的变量在后一步中仍然存在。

**正确做法**:
- 将完整工作流封装在**单个** `execute_code` 调用中
- 所有 import、函数定义、变量初始化都放在同一个代码块开头
- 不要拆分到多个 `execute_code` 调用中执行逐步调试

```python
# ✅ 正确：所有步骤在一个 execute_code 中
import json, yaml, time
from pathlib import Path

hermes_home = Path.home() / ".hermes"
skills_dir = hermes_home / "skills"
log_base = hermes_home / "evolution_logs" / "skill_optimizer"

def parse_frontmatter(path):
    ...

# ... 所有后续步骤 ...
# Step 1: scan
# Step 2: read state
# Step 3: determine skill
# Step 4-9: audit + test + save
print("Done")
```

```python
# ❌ 错误：跨调用依赖变量（会 NameError）
# --- 第一次调用 ---
log_base = Path.home() / ".hermes/evolution_logs/skill_optimizer"
# --- 第二次调用 ---
# log_base 未定义！
state_path = log_base / "state.json"  # NameError
```

**验证**: 技能执行过程中如果出现 `NameError`，立即将所有步骤合并到单一 `execute_code` 调用中重试。

### Bug 6: 情报收集中不能在 execute_code 里调用 MCP 工具（2026-04-21）

**问题现象**: 在 `execute_code` 中调用 `mcp_minimax_web_search(...)` 时出现 `NameError: name 'mcp_minimax_web_search' is not defined`。

**根因**: MCP 工具（如 `mcp_minimax_web_search`）是 agent 工具，只能通过 agent 的工具调用机制使用。`execute_code` 是独立 Python 进程，**不继承** agent 的工具函数命名空间。两者是完全独立的调用路径。

**正确做法**:
1. 在 `execute_code` 中准备好 `intel_data` 结构并写入 `intelligence_latest.json`（占位）
2. 然后用**独立的工具调用** `mcp_minimax_web_search` 执行实际搜索
3. 搜索完成后回到 `execute_code` 更新情报文件并执行闭环

```python
# ❌ 错误：在 execute_code 中调用 mcp_minimax_web_search
# 这会 NameError，因为 execute_code 没有这个函数
result = mcp_minimax_web_search(query="...")

# ✅ 正确：execute_code 只负责文件 IO
# 实际搜索用独立的工具调用
intel_data = {"collection_status": "pending", ...}
with open(intel_path, "w") as f:
    json.dump(intel_data, f)
print("请在下一步使用 mcp_minimax_web_search 工具执行搜索")
```

**验证**: 如果 `execute_code` 报 `NameError` 且错误信息包含 MCP 工具名，就说明违反了此规则。

### Bug 7: `success=None` 被错误计为失败（2026-04-28）

**问题现象**: 通过率显示 0-14%，但实际测试大部分通过。google-workspace 明明 `success=true` 却被计入失败。

**根因**: `not r.get("success")` 对 `None` 返回 `True`，将"测试无法运行"错误分类为"测试失败"。同时 `skill_history.json` 的 `passed` 字段计算也有同样问题——`if r.get("success")` 对 `None` 返回 `False`。

**正确做法**: 使用显式三值判断（见 Bug 7）：
```python
def classify_run(r):
    success = r.get("success")
    status = r.get("status", "")
    error = str(r.get("error", "") or "").lower()
    EXPECTED_PATTERNS = ("not configured", "not installed", "not set", "not found", "missing", "unavailable")
    if success is True:
        return "pass"
    if success is None and status in ("healthy", "pass", "warning"):
        return "pass"  # 旧 schema 兼容
    if success is False:
        if any(p in error for p in EXPECTED_PATTERNS):
            return "expected_fail"  # 环境缺失，不算真正失败
        return "unexpected_fail"
    return "not_run"  # success=None 且无 healthy status → 未运行
```

**影响范围**: `reporter.py`（通过率计算）+ `learning_curve.py`（历史快照生成）+ `trends.json`（历史记录）

### Bug 14: 错误率统计用 `status != "success"` 判断（2026-05-01）

**问题现象**: error_rate 计算时用 `status != "success"` 判断错误，但实际 status 值是 `"healthy"` 或 `"warning"`，导致所有记录都被计为错误。

**根因**: 第八步错误率审核的判断条件写死了 `"success"`，但 report 中 status 字段实际值是 `"healthy"` / `"warning"` / `"degraded"`。

**正确做法**: 用 `classify_run()` 函数统一判断，或直接用 `success` 字段：
```python
total_runs = len([r for r in history if r.get("skill") == current_skill])
# 用 classify_run 判断，不依赖 status 字符串
error_runs = len([r for r in history if classify_run(r) == "unexpected_fail"])
error_rate = (error_runs / total_runs * 100) if total_runs > 0 else 0
```

### Bug 8: dojo.py 完整闭环模块存在但未被文档化（2026-04-30）

**问题现象**: `~/.hermes/evolution_logs/skill_optimizer/dojo.py` 存在，提供一键运行全部6步的编排能力，但在 skill 文档中完全未提及。

**正确做法**: 在"失败信号监控"章节中，用 `dojo.py` 替代逐个调用6个模块的冗长方式：

```python
# ✅ 推荐：一键运行完整 DOJO 闭环
import subprocess, sys
from pathlib import Path

LOG = Path.home() / ".hermes/evolution_logs" / "skill_optimizer"
DOJO = LOG / "dojo.py"

r = subprocess.run([sys.executable, str(DOJO)], capture_output=True, text=True, timeout=120)
print(r.stdout)
if r.stderr:
    print("STDERR:", r.stderr[:300])
```

**⚠️ 重要：dojo.py 执行后必须验证所有步骤是否完成。** 实际观察发现 dojo.py 有时会只运行 Monitor（Step 1）就退出，不会自动继续后续步骤。如果输出只包含 "Step 1: Monitor" 而没有 Step 2-6，应回退到手动6步调用：

```python
# 如果 dojo.py 未完成全部步骤，回退到手动执行
MODULES = ["monitor.py", "analyzer.py", "fixer.py", "reporter.py", "learning_curve.py", "apply_fixes.py"]
for mod in MODULES:
    p = LOG / mod
    if p.exists():
        r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True, timeout=60)
        print(r.stdout)
```

**验证方法**：检查 dojo 输出中是否包含所有 6 个 Step 的标题（如 "Step 2: Analyzer"、"Step 3: Fixer" 等）。如果只看到 Monitor 输出，立即手动触发剩余步骤。

原6步手动调用方式仍然有效，但 dojo.py 是更简洁的接口——前提是它实际运行完全部步骤。

### Bug 10: trends.json 历史记录 schema 不一致（2026-04-28）

**问题现象**: 不同时间生成的 history 文件使用了不同 schema——新 schema 把结果嵌套在 `current.metrics` 下，旧 schema 直接放在顶层。导致分析工具读不到正确字段。

**根因**: skill-cycle-optimizer 在不同阶段迭代了不同版本的输出格式，但 trends.json 是追加写入的，混入了新旧两种格式。

**正确做法**: 读取 history 文件时同时兼容两种 schema：
```python
if "current" in data:
    # 新 schema
    skill = data["current"].get("skill", "?")
    success = data["current"].get("metrics", {}).get("success")
    error = data["current"].get("metrics", {}).get("error", "")
else:
    # 旧 schema
    skill = data.get("skill", "?")
    success = data.get("success")
    error = data.get("error", "")
```

**修复措施**: 已重建 `trends.json`（从 117 个 history 文件重新生成），以后 history 文件统一用新 schema。

### Bug 11: sandbox 测试直接用 yaml.safe_load 解析多文档 SKILL.md（2026-04-30）

**问题现象**: `google-workspace` 的 sandbox 测试执行时报告 `success=False, error="expected a single document in the stream"`。

**根因**: 直接用 `yaml.safe_load(content)` 加载整个 SKILL.md 文件，但很多 SKILL.md 包含多个 YAML 文档（用 `---` 分隔），第二个文档会导致解析失败。

**正确做法**: 所有 YAML 解析统一使用 `parse_frontmatter()`，它只提取第一个 `---...---` 块作为 frontmatter：

```python
# ✅ 正确
fm_test, body_test = parse_frontmatter(skill_md_path)
output_valid = fm_test is not None

# ❌ 错误
parsed = yaml.safe_load(content)  # 多文档时报错
```

### Bug 9: xiaoa-persona-system 重复注册导致双重统计（2026-04-28）

**问题现象**: `xiaoa-persona-system` 和 `mlops/xiaoa-persona-system` 都存在，前者是 0 字节空文件，后者是真实内容。rglob 扫描会扫到两个路径，导致同一个技能的失败被计两次。

**根因**: 历史上复制/移动技能时在两个路径各创建了一份。

**正确做法**: 删除空文件：
```bash
rm ~/.hermes/skills/xiaoa-persona-system/SKILL.md
# mlops/xiaoa-persona-system/SKILL.md 保留
```
同时在 `fixes_pending` 中清除对应的空修复方案。

### Bug 12: 性能对比 ZeroDivisionError（2026-05-01）

**问题现象**: `nano-pdf` 测试时，唯一的 historical record 的 `latency_ms = 0`（数据损坏），导致：
```
delta_pct = (latency_ms - last["latency_ms"]) / last["latency_ms"] * 100
ZeroDivisionError: division by zero
```

**根因**: 第七步性能稳定性审核直接用 `last["latency_ms"]` 作除数，没有检查是否为 0 或 None。

**正确做法**:
```python
last_latency = last.get("latency_ms", 0)
if last_latency and last_latency > 0:
    delta_pct = (current_latency - last_latency) / last_latency * 100
    perf_stable = "stable" if abs(delta_pct) <= 10 else ("degraded" if delta_pct > 10 else "improved")
else:
    perf_stable = "stable"  # 无有效历史数据，标记为 stable
```

### Bug 13: SkillTree 和 GapAnalyzer 无法从 hermes_agent.evolution 导入（2026-05-01）

**问题现象**: 执行以下导入时报错：
```python
from hermes_agent.evolution import SkillTree  # ImportError
from hermes_agent.evolution import GapAnalyzer  # ImportError
```

**根因**: `hermes_agent.evolution` 模块不存在这两个类，或者路径/名称已变更。

**影响**: 第十一步（SkillTree 更新）和第十二步（GapAnalyzer 缺口分析）每次都失败。

**正确做法**: 用 try/except 包裹，失败时记录日志并继续，不阻塞主流程：
```python
try:
    from hermes_agent.evolution import SkillTree, GapAnalyzer
    st = SkillTree()
    gaps = GapAnalyzer().run_full_analysis()
except ImportError as e:
    print(f"SkillTree/GapAnalyzer 导入失败（{e}），跳过")
```

### Bug 15: perf_audit 把 "improved" 误判为 fail（2026-05-01）

**问题现象**: 性能变快（improved）被标记为 `perf_audit: fail`，导致技能状态从 `healthy` 降级为 `degraded`。

**根因**: 判断逻辑写成了 `perf_audit = "pass" if perf_stable == "stable" else "fail"`，没有考虑 `"improved"` 也是正常/良好状态。

**正确做法**: `"improved"` 等同于 `"stable"` — 两者都是 pass：
```python
perf_audit = "pass" if perf_stable in ("stable", "improved") else "fail"
# 对应的审核评分标准也要更新：
# | `perf_stable` | ±10% 内或变快 | - | 变慢 > 10% |
```

**影响**: 第九步生成报告的 `summary.audit_passed` 计数会少计一项，导致退化技能被误判。

### Bug 16: CLI 测试 `output_valid` 未无条件初始化（2026-05-02）

**问题现象**: `xitter` 测试时 `NameError: name 'output_valid' is not defined`。

**根因**: `output_valid` 只在 `if x_cli_exists:` 分支内赋值，当命令不存在时代码进入 `else:` 分支但未设置 `output_valid`，导致后续 `report["current"]["metrics"]["output_valid"]` 引用时 `NameError`。

**正确做法**: 在条件分支之前将 `output_valid = False` 作为默认值初始化，后续分支内按需覆盖：
```python
success = None
output_valid = False  # 必须无条件初始化
error = ""

if shutil.which(cmd):
    # ... set success/output_valid/error inside
else:
    success = None
    error = f"{cmd} not installed"
    output_valid = False  # else 分支也显式赋值，保持一致
```

### Bug 17: `hermmes_home` 变量名拼写错误（2026-05-04）

**问题现象**: `NameError: name 'hermmes_home' is not defined`。

**根因**: `hermes_home` 误写为 `hermmes_home`，是 Python 脚本中常见的手滑错误（双重 m）。

**正确做法**: 写完变量赋值后立即引用一次，或使用 IDE/编辑器的拼写检查。本次执行中第一次调用就捕获了该错误，因为 `execute_code` 是单次独立进程，错误不会跨调用隐藏。

### Bug 18: `delta_pct` 在 history 存在但 last_latency=0 时未初始化（2026-05-04）

**问题现象**: 当 `history` 列表非空但其中记录的 `latency_ms = 0`（数据损坏或首次运行）时，`delta_pct` 在 `if last_latency and last_latency > 0:` 分支内未被赋值，但后续 `print(f"...delta={delta_pct:.1f}%...")` 在该分支外执行，导致 `NameError: name 'delta_pct' is not defined`。

**根因**: `delta_pct` 的赋值语句在 `if` 内，而 print 在 `if` 外。当历史延迟为 0 时，分支跳过，变量永远不被创建。

**正确做法**: 在 `if` 分支之前将 `delta_pct = 0.0` 作为默认值初始化：
```python
delta_pct = 0.0  # 必须在外层初始化，否则 history 非空但 last_latency=0 时 NameError
if history:
    last = history[-1]
    last_latency = last.get("latency_ms", 0)
    if last_latency and last_latency > 0:
        delta_pct = (latency_ms - last_latency) / last_latency * 100
        # ...
```

### Bug 19: reporter.py 在 skill_optimizer 上下文中崩溃（2026-05-04）

**问题现象**: 手动6步 DOJO 闭环中，`reporter.py` 返回 `rc=1` 并输出 Python traceback，但 skill-cycle-optimizer 未能记录错误详情（只打印了截断的 stderr）。

**根因**: 未完全确认。可能是 reporter.py 读取 trends.json 或 skill_history.json 时遇到 schema 不一致，或依赖某个在 cron 环境下不可用的模块。

**正确做法**: reporter.py 的输出截断到 100 字符不足以诊断根因。应改进日志记录：
```python
# 在 skill_optimizer 触发 reporter.py 后，记录完整错误
if r.returncode != 0:
    full_error_path = log_base / f"reporter_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    with open(full_error_path, "w") as f:
        f.write(f"STDOUT:\n{r.stdout}\n\nSTDERR:\n{r.stderr}")
    print(f"reporter.py failed (rc={r.returncode}), full log: {full_error_path}")
```
**影响**: 每次运行 reporter.py 的错误会被静默忽略，不利于发现 DOJO 系统的实际问题。

**诊断参考**: `references/reporter-crash-diagnostics.md` — 包含完整的诊断步骤、常见根因表和修复方向。reporter.py 在 `format_cli_` line 366 崩溃是已知表现，截至 2026-05-08 仍未解决。

### Bug 20: intelligence-action-loop 处理混合类型列表时崩溃（2026-05-07）

**问题现象**: `AttributeError: 'str' object has no attribute 'get'` 在遍历 `rising` 和 `new_entrants` 时崩溃。

**根因**: `rising_stars` 和 `new_entrants` 列表中的元素类型不一致——有些是 `dict`（含 `name`/`trend` 字段），有些是纯 `str`。直接调用 `p.get("name", "")` 对字符串元素报错。

**正确做法**: 使用统一的取值 helper 函数处理混合类型：
```python
def get_name(p):
    """处理 rising/new_entrants 中 dict 或 str 混合类型"""
    if isinstance(p, dict):
        return p.get("name", "")
    elif isinstance(p, str):
        return p
    return str(p)

def get_trend(p):
    if isinstance(p, dict):
        return p.get("trend", "")
    return ""

# 使用
for p in rising + new_entrants:
    name = get_name(p)
    trend = get_trend(p)
    if name and not any(t.get("topic") == name for t in known["researched"]):
        # ...
```

**影响**: 情报闭环在第二轮及以后的情报处理中必然崩溃，导致所有调研任务无法生成。

The user has provided the following instruction alongside the skill invocation: