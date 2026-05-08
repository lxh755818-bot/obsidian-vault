# 小a 完整备份

> 生成时间：每次备份自动更新

## 目录结构

```
backup/
├── README.md              # 本文件
├── MEMORY.md              # 持久记忆（用户偏好、习惯）
├── SOUL.md                # 灵魂核心定义
├── auth/                  # 认证文件（已脱敏）
│   ├── auth.json
│   └── .env
├── config/                # 配置文件（已脱敏）
│   ├── config.yaml
│   ├── credentials.json
│   └── stocks.json
├── cron/                  # 定时任务定义
│   └── cron_jobs.json     # 15个活跃Cron任务
├── skills/                # 所有技能定义（完整SKILL.md）
├── scripts/               # 脚本文件
├── xiaoa/                  # 人格系统
├── knowledge/             # 知识库
└── evolution_logs/        # 进化日志
```

## 备份原则

- **敏感信息已脱敏**：所有 API Key、Token、Password 均替换为 `***REDACTED***`
- **不备份**：sessions/、state.db、logs/、cache/、images/（数据文件）
- **仅备份**：配置文件、技能定义、脚本代码、知识沉淀

## 定时任务一览（共15个）

| 任务 | 调度 | 投递 |
|------|------|------|
| 日志纠错自进化 | 每12h | local |
| 记忆系统定期检查 | 每2h | local |
| 技能循环优化 | 每2h | local |
| 每日A股选股简报 | 09:00 | feishu |
| GitHub kk 协作轮询 | 每30min | local |
| 每日记忆守护Janitor | 03:00 | local |
| memory-decay | 22:00 | local |
| AI进化日报 | 04:00 | feishu |
| EvoMap Heartbeat | 每30min | origin (暂停) |
| EvoMap Validator | 每30min | origin |
| hermes-dojo-daily | 09:00 | origin |
| memory-palace-daily | 09:00 | origin |
| memory-palace-autobind | 每4h | origin |
| daily-distill | 04:00 | origin |
| ASVP Telemetry | 每2h | origin |

## 恢复指南

如需在全新环境恢复：

```bash
# 1. 克隆仓库
git clone https://github.com/lxh755818-bot/obsidian-vault.git
cd obsidian-vault/backup

# 2. 恢复配置
cp config/config.yaml ~/.hermes/config.yaml
cp config/credentials.json ~/.hermes/config/credentials.json
cp config/stocks.json ~/.hermes/config/stocks.json

# 3. 恢复技能
cp -r skills/* ~/.hermes/skills/

# 4. 恢复脚本
cp -r scripts/* ~/.hermes/scripts/

# 5. 恢复记忆
cp MEMORY.md ~/.hermes/MEMORY.md
cp SOUL.md ~/.hermes/SOUL.md

# 6. 恢复认证（手动填入真实值）
# 编辑 auth/auth.json 和 auth/.env，填入真实API Key

# 7. 重建Cron任务
# 从 cron/cron_jobs.json 逐个重建（hermes cron create）
```
