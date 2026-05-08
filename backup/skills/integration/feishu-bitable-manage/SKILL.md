---
name: feishu-bitable-manage
description: 飞书多维表格（Bitable）管理 — 创建副表、配置字段、读写记录。包含关键API格式坑点总结。
triggers:
  - 飞书多维表格配置
  - Bitable API读写
  - 飞书知识库维护
---

# 飞书多维表格（Bitable）管理技能

## API认证

```python
# ⚠️ 正确路径是 config['platforms']['feishu']，不是 config['feishu']
# Hermes 内部将飞书配置存在 platforms 这个顶层 key 下
import yaml
from pathlib import Path

config = yaml.safe_load(open(Path.home() / ".hermes" / "config.yaml"))
feishu_cfg = config.get("platforms", {}).get("feishu", {})
APP_ID = feishu_cfg.get("app_id")       # e.g. "cli_a95a1e699d78dcb5"
APP_SECRET = feishu_cfg.get("app_secret")  # e.g. "hnvbzkROjEbjJjYDJA1gdjSzx2..."

# 如果 platforms 里找不到，再尝试遍历所有 top-level key 匹配 app_id
for k, v in config.items():
    if isinstance(v, dict) and v.get("app_id") == APP_ID:
        APP_SECRET = v.get("app_secret")
        break
```

> ⚠️ **踩坑记录**：`config['feishu']` 是空的（YAML 里虽然有 `feishu:` 但被解析到 `platforms` 下），
> 错误写法会导致 `app_id=None, app_secret=None`，auth 返回 `tenant_access_token` 字段缺失。

url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
data = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=10) as resp:
    TOKEN = json.loads(resp.read())["tenant_access_token"]
```

> ⚠️ token有效期2小时，每次调用前重新获取。

### GitHub 公共文件读取：优先用 raw.githubusercontent.com

```python
# ❌ GitHub API 匿名请求：60次/小时，超限返回 HTTP 403 rate limit exceeded
url = "https://api.github.com/repos/owner/repo/contents/path.md"

# ✅ raw.githubusercontent.com：不限流，适合定时任务
url = "https://raw.githubusercontent.com/owner/repo/main/path.md"
# 注意：需要知道分支名（main 或 master）
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as resp:
    content = resp.read().decode("utf-8")
```

适用场景：定时任务检查 GitHub 文件变化（如 AGENT_COMM.md 协作通信）、读取公开配置文件。

## Base URL & 基础路径

```
https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables
```

## 核心坑点（必读）

### 1. 日期字段 — 用毫秒时间戳，不用字符串

```python
from datetime import datetime
today_ts = int(datetime.now().timestamp() * 1000)  # ✅ 正确
# ❌ 错误："2026-04-21" → DatetimeFieldConvFail
fields = {"日期": today_ts}
```

### 2. URL字段 — 用对象格式

```python
# ✅ 正确
fields = {"链接": {"link": "https://example.com"}}
# ❌ 错误："https://example.com" → URLFieldConvFail
```

### 3. 单选/多选字段 — 直接用字符串值（已验证）

```python
fields = {"操作": "关注", "信号依据": "MACD金叉"}  # ✅
# 写入后返回 code=0 即成功
```

**重要发现（2026-04-22 验证）**：即使字段选项列表为空（`property.options: []`），直接传字符串也能成功写入，不需要先创建选项。这与文档描述的行为不一致。

```python
# 验证：字段结构
# type=3, property.options=[]（空）
# 直接写字符串 → ✅ 成功
fields = {"名称": "cronjob", "类型": "hermes", "状态": "active"}  # 全部成功
```

如果选项已存在且你要用新的 option name，则需要先 `POST /fields` 创建选项。

### 4. 文本/多行文本 — 直接字符串

```python
fields = {"股票名称": "长江电力", "技术信号": "RSI6=78.21"}  # ✅
```

### 5. 所有字段写入用字段名（非field_id）

```python
# ✅ 用字段名
fields = {"股票名称": "长江电力", "操作": "关注"}
# ❌ field_id格式 fldxxx → FieldNameNotFound
```

## 常用API

### 列出所有表格
```python
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
# 返回: [{"name": "技能", "table_id": "tblXXX"}, ...]
```

### 创建副表
```python
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables"
data = json.dumps({"table": {"name": "表名"}}).encode()
# 注意：若表名重复返回 TableNameDuplicated
```

### 查询表字段
```python
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/fields"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
# 返回: [{"field_id": "fldXXX", "field_name": "股票名称", "type": 1}, ...]
# type含义: 1=文本, 3=单选, 5=日期, 15=URL
```

### 创建字段
```python
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/fields"
data = json.dumps({
    "field_name": "字段名",
    "type": 1  # 1文本 3单选 5日期 15URL
}).encode()
```

### 写入单条记录
```python
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/records"
data = json.dumps({"fields": fields}).encode()
req = urllib.request.Request(url, data=data, headers={
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
})
```

### 批量更新记录（推荐，一次性完成）

单条 `POST /records` 更新在某些情况下会返回 404（疑似 token 缓存问题），`batch_update` 更稳定：

```python
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/records/batch_update"
payload = {
    "records": [{
        "record_id": "recvhtscAojsgt",
        "fields": {"密钥/隐私内容": "github_pat_11CC..."}
    }]
}
data = json.dumps(payload).encode()
req = urllib.request.Request(url, data=data, headers={
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
})
resp = json.loads(urllib.request.urlopen(req).read())
# code=0, msg="success" 表示成功

# ⚠️ 每次 batch_update 前重新获取 token（tenant_access_token 有缓存问题）
def update_records(base_token, table_id, records_to_update):
    token = get_fresh_token()  # 每次重新认证
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/records/batch_update"
    payload = {"records": records_to_update}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    return json.loads(urllib.request.urlopen(req).read())
```

### 批量写入（逐条，Bitable无原生批量写入API）
```python
for rec in records:
    result = bitable_write_record(token, table_id, rec)
    time.sleep(0.3)  # 限速
```

## 常见错误

| 错误码 | 含义 | 解决方法 |
|--------|------|---------|
| DatetimeFieldConvFail | 日期格式错误 | 用毫秒时间戳 |
| URLFieldConvFail | URL格式错误 | 用 `{"link": "url"}` |
| FieldNameNotFound | 字段名不存在 | 用field_name而非field_id |
| TableNameDuplicated | 表名已存在 | 换一个表名 |

## 字段类型处理（field.type 对照表）

| type值 | 字段类型 | 读取方式 | 写入方式 |
|--------|---------|---------|---------|
| 1 | 文本/多行文本 | 直接 str | 直接字符串 |
| 3 | 单选/多选 | list[{"text": "选项名"}] | 直接字符串（需已存在选项） |
| 5 | 日期 | 毫秒时间戳 → datetime.fromtimestamp(v/1000) | int(datetime.timestamp() * 1000) |
| 11 | 人员 | list[{"id": "ou_xxx", "name": "姓名"}] | 不支持直接写入 |
| 17 | 附件/进度 | list[{"name": "文件名", "token": "xxx"}] | 不支持 |
| 18 | 关联字段 | list[{"record_id": "...", "table_id": "..."}] | 不建议手动写 |

### 读取字段的通用处理

字段值为 None 时直接返回 None。数值型字段需判断是否 >1e12 是日期。列表型字段取第一个元素的 name/text/name 字段。人员字段返回 name。

### 已知不可写入的字段类型

人员 type=11、附件 type=17、关联 type=18 均无法通过标准 API 写入。

## 查找多维表格进阶（搜索不精确时）

### 方法1：搜索 docs_types=[] 而非 ["bitable"]

docs_types=["bitable"] 返回结果少且 docs_token 常为 null。必须用 docs_types=[] 才能搜到包含 bitable 在内的所有类型文档。

### 方法2：搜到 token 后逐个验证 tables

对搜索返回的每个 bitable token，调用 `GET /bitable/v1/apps/{token}/tables` 验证是否为要找的 bitable。

### 方法3：遍历用户有权限的 bitable

当搜索也找不到时，可用 `GET /drive/v1/files` 列出用户根目录文件（含 bitable），或对所有搜索结果中的 bitable 逐个调用 tables API 验证。

### 读取指定日期范围记录

获取 records 后筛选 date 字段（type=5）的时间戳范围：
- 目标日期范围：start = datetime(2026,4,20).timestamp()*1000，end = datetime(2026,4,21).timestamp()*1000
- 过滤：start <= ts <= end 的记录

## 常见错误

| 错误码 | 含义 | 解决方法 |
|--------|------|---------|
| DatetimeFieldConvFail | 日期格式错误 | 用毫秒时间戳 |
| URLFieldConvFail | URL格式错误 | 用 {"link": "url"} |
| FieldNameNotFound | 字段名不存在 | 用field_name而非field_id |
| TableNameDuplicated | 表名已存在 | 换一个表名 |
| SingleSelectFieldConvFail | 单选字段值不在选项列表中 | 先查字段options，写入前确保选项已存在；选项列表为空时字符串写入会失败，需先用 `POST /fields` 创建选项 |
| 40004 | 无权限访问该文档 | 应用没有该 bitable 的权限 |

## 状态

- [x] API认证流程（2026-04-22 修正：config['platforms']['feishu'] 而非 config['feishu']）
- [x] 字段格式坑点验证（日期/URL/单选/人员/附件）
- [x] 创建副表、字段、写入记录全流程
- [x] 通过文档搜索API查找任意多维表格
- [x] 搜索无token时逐个验证 bitable tables 方法（2026-04-21 验证）
- [x] 字段类型处理对照表和通用解析函数（2026-04-21 验证）
- [x] batch_update API 验证：单条 update 偶发 404，batch_update（含单条）更稳定（2026-04-22）
- [x] tenant_access_token 刷新策略：每次写入操作前重新认证（2026-04-22）
- [x] Bitable 作为隐私元数据注册表的模式（2026-04-22）

## 高级模式：Bitable 作为元数据注册中心

飞书多维表格可以作为**跨系统的元数据注册表**，本地缓存 + TTL 刷新，比直接在代码里写死模式更灵活。

### 典型场景

隐私模式注册表：飞书表存储敏感信息格式（API key pattern、token前缀等），本地脚本以 JSON 缓存 + 1小时TTL 读取，避免每次请求飞书。

### 架构

```
飞书 Bitable（主副本）
  ↓ 每小时同步（或按需 sync-privacy）
  ↓
~/.hermes/memory/privacy_patterns.json（本地缓存 TTL=3600s）
  ↓
memory_l3.py privacy_filter() 读取缓存
```

### 隐私记录表设计参考

Table: `tbllup7e8aQvf4Lx`（Privacy Table）

| 字段 | 类型 | 说明 |
|------|------|------|
| 名称/标识 | 文本 | 如 "MiniMax API Key" |
| 类型 | 单选 | API密钥 / GitHub Token / 平台Token / 证书 |
| 密钥/隐私内容 | 文本 | 格式示例 "ghp_***（真实值在 config.yaml）" |
| 原始内容是否已备份 | 单选 | 是 / 否 / 待确认 |
| 用途说明 | 多行文本 | 在哪些脚本/场景中使用 |
| 创建时间 | 日期 | 毫秒时间戳 |
| 备注 | 多行文本 | 额外说明 |

### 本地缓存读取示例

```python
import json, time
from pathlib import Path

CACHE_PATH = Path.home() / ".hermes" / "memory" / "privacy_patterns.json"
CACHE_TTL = 3600  # 1小时

def get_patterns():
    if CACHE_PATH.exists():
        cached = json.loads(CACHE_PATH.read_text())
        if time.time() - cached.get("_cached_at", 0) < CACHE_TTL:
            return cached["patterns"]
    # 缓存失效 → 从飞书拉取
    patterns = fetch_from_feishu()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps({"patterns": patterns, "_cached_at": time.time()}))
    return patterns
```

### SQLite 迁移注意

给已有表加新列时，**不能用 `DEFAULT CURRENT_TIMESTAMP`**（SQLite 要求默认值必须是常量）：

```python
# ❌ 报错：Cannot add a column with non-constant default
conn.execute("ALTER TABLE memories ADD COLUMN ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

# ✅ 正确：分两步
conn.execute("ALTER TABLE memories ADD COLUMN ts TEXT DEFAULT ''")
conn.execute("UPDATE memories SET ts = created_at WHERE ts = ''")
```
