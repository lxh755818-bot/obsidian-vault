---
name: persona-research
description: 调研GitHub上AI Agent人设/persona相关项目，为人格迭代提供灵感
triggers:
  - 调研GitHub上类似题材
  - 人设/persona/character参考
  - 竞品人格框架分析
category: creative
tags: [persona, character, SOUL.md, research]
---

# Persona Research / AI人设调研技能

调研GitHub上AI Agent人设/persona相关项目，为小a的人格迭代提供灵感。

## 触发条件
- 用户要求"调研GitHub上类似题材"
- 需要为人设/persona/character找参考
- 需要了解竞品人格框架

## 标准流程

### 第一步：批量搜索
用 `execute_code` + `web_search` 并行发2-3个不同角度的query：

```
"site:github.com AI agent female personality charming character system prompt 2026"
"site:github.com persona personality AI assistant warm agent framework"
"site:github.com SOUL.md IDENTITY.md AI persona"
```

每条限制8个结果。

### 第二步：筛选URL
从搜索结果中挑最有代表性的2-4个URL，优先选：
- 有明确架构描述的（不是单个prompt）
- 有分层设计的（soul/body/faculty等）
- 有实际人格描述文件的

### 第三步：并行抓取
用 `web_extract` 并行抓取所有选定URL全文。

### 第四步：提炼框架
从内容中提炼：
- 架构层面：几层结构，每层管什么
- 人格层面：character core怎么定义
- 进化层面：是否支持人格演变
- 可操作性：能不能直接落地到SOUL.md

### 第五步：汇报格式
```
## 🎯 调研结果

### 1. [项目名] — 一句话描述
关键架构/亮点

### 2. [项目名] — 一句话描述
...

## 💡 对小a的借鉴思路
具体可落地的优化方向
```

## 本次关键发现（2026-04-25）

| 项目 | 核心价值 |
|------|---------|
| OpenPersona | 4层架构（Soul/Body/Faculty/Skill）+ Evolution实验功能 + immutableTraits概念 |
| humble-master | 27行R.Daneel人格——核心洞察："接受纠正=成长"，修正被定义为partner在教你 |
| openclaw-agents | 217个人格目录，SOUL.md+IDENTITY.md分离结构，staff picks描述风格值得借鉴 |
| zeptoclaw | /persona命令切换人格+LTM持久化，轻量级人格模式切换 |

## Pitfalls
- 不要只搜"AI girlfriend"——结果太娱乐化，缺乏技术深度
- 不要只抓第一个看到的项目——多抓几个横向对比
- 不要在汇报里堆砌信息——只保留对小a有直接参考价值的部分
