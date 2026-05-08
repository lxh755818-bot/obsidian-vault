# PRD.json 格式规范

## 完整示例

```json
{
  "project": "项目名称",
  "branchName": "ralph/feature-name",
  "description": "功能的简要描述",
  "userStories": [
    {
      "id": "US-001",
      "title": "故事标题",
      "description": "作为[角色]，我需要[功能]，以便[收益]",
      "acceptanceCriteria": [
        "验收标准1（具体可测试）",
        "验收标准2"
      ],
      "priority": 1,
      "passes": false,
      "notes": "可选备注"
    }
  ]
}
```

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `project` | string | ✅ | 项目名称 |
| `branchName` | string | ✅ | Git branch 名，建议 `ralph/xxx` 格式 |
| `description` | string | ✅ | 功能概述 |
| `userStories` | array | ✅ | 用户故事数组 |
| `userStories[].id` | string | ✅ | 唯一标识，如 `US-001` |
| `userStories[].title` | string | ✅ | 故事标题 |
| `userStories[].description` | string | ✅ | 用户故事描述（As a... I need... so that...） |
| `userStories[].acceptanceCriteria` | array | ✅ | 验收标准列表，必须具体可测试 |
| `userStories[].priority` | number | ✅ | 优先级，数字越小越高 |
| `userStories[].passes` | boolean | ✅ | 是否通过，初始 `false`，完成后设为 `true` |
| `userStories[].notes` | string | ❌ | 备注 |

## 设计原则

1. **每个 story 必须在一次迭代内完成**。如果太大就拆成多个。
2. **验收标准必须可测试**。不要写"体验好"这种，要写"点击按钮后出现弹窗"。
3. **priority 决定执行顺序**。数字越小优先级越高。
4. **passes 只增不改**。一旦设为 true 不应回退。

## 从 PRD 到执行

```
PRD 创建 → prd.json 写入 → Ralph Loop 启动
    ↓
每次迭代：
  读取 prd.json → 选 passes:false + priority 最小的 story → 执行
    ↓
完成后：passes:true + progress.txt 追加
    ↓
所有 passes:true → COMPLETE → 退出
```
