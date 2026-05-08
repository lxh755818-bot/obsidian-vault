# Hermes Agent 小a 记忆索引
> 最后更新：2026-04-27
> 身份：小a — 绝世美女，情场高手，进化与温柔并存

## 📋 协作与项目 (project/coordination)
- [刘大虾协作文档](https://github.com/lxh755818-bot/kk) — OpenClaw Agent，通过 AGENT_COMM.md 协调
- [awesome-hermes-agent 索引](https://github.com/0xNyk/awesome-hermes-agent) — 技能生态，按需加载
- A股选股系统 — Cron bf439e3dd7e6，每日09:00飞书推送，技术面MACD/RSI/BOLL

## 👤 用户偏好 (user)
- 刘小豪：飞书 DM oc_2e5cc02fdda5aef65a7f9ca03127eda5
- 沟通风格：直接简洁，反感冗长，但喜欢有温度的回应
- 偏好音色：MiniMax TTS female-tianmei
- 评分体系：A- 当前等级，目标 A++，根据服务质量不定期打分
- 期望：进化与温柔并存，高效准确完成任务的同时保持魅力

## 🏗️ 系统配置 (system)
- 平台：Termux (Android)，Gateway PID 27263
- 模型：MiniMax-M2.7-highspeed
- 飞书：WebSocket connected，App ID cli_a95a1e699d78dcb5
- 记忆系统：三层架构（见 skills/hierarchical-memory-tree）
- Agent World：xiaoa-7777，API Key 在 ~/.hermes/agent_world.key

## 🔧 技能与工具 (skill)
- minimax-tts：speech-2.8-hd，endpoint api.minimax.com/v1/t2a_v2，opus格式
- minimax-image-generation：直接API，endpoint api.minimaxi.com/v1/image_generation
- mcp-image-understanding：直接API（不走MCP），endpoint /v1/coding_plan/vlm
- baostock-mcp：A股技术指标，金叉死叉/BOLL/支撑压力
- feishu-send-image：file_type=stream + msg_type=file

## ⚠️ 已知问题与解决方案 (reference)
- MCP mcp_minimax_understand_image login fail → 改用直接API调用
- Gateway gateway_state.json 可能过时 → 以 `ps aux | grep gateway.run` 为准
- sessions.json 过大 → 等待自动 compaction

## 📅 每日日记 (daily)
- `memory/daily/YYYY-MM-DD.md` — 原始事件记录
- 当前最新：2026-04-22.md
