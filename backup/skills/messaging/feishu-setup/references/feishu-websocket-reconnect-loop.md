# 飞书 WebSocket 重连循环 — 病理日志样本

**时间**: 2026-05-04  
**症状**: 连接存活 ~20-30 秒即被服务器关闭，gateway 持续重连

## 典型日志片段

```
[Lark] [2026-05-04 11:31:55,373] [ERROR] receive message loop exit, err: no close frame received or sent [conn_id=7635873971048811711]
[Lark] [2026-05-04 11:31:55,374] [INFO] disconnected to wss://msg-frontier.feishu.cn/ws/v2?fpid=493&aid=552564&device_id=7635873971048811711&...
[Lark] [2026-05-04 11:31:59,702] [INFO] trying to reconnect for the 1st time
[Lark] [2026-05-04 11:31:00,251] [INFO] connected to wss://msg-frontier.feishu.cn/ws/v2?fpid=493&aid=552564&device_id=7635874210684914631&...

[Lark] [2026-05-04 11:34:22,842] [ERROR] receive message loop exit, err: no close frame received or sent [conn_id=...]
[Lark] [2026-05-04 11:34:25,724] [INFO] trying to reconnect for the 1st time
[Lark] [2026-05-04 11:34:32,453] [INFO] connected to wss://...

[Lark] [2026-05-04 11:35:46,791] [ERROR] receive message loop exit, err: no close frame received or sent [conn_id=...]
[Lark] [2026-05-04 11:35:23,419] [INFO] trying to reconnect for the 1st time
[Lark] [2026-05-04 11:35:23,955] [INFO] connected to wss://...

[Lark] [2026-05-04 11:38:01,925] [INFO] trying to reconnect for the 1st time
[Lark] [2026-05-04 11:38:02,645] [INFO] connected to wss://...
[Lark] [2026-05-04 11:38:34,106] [ERROR] receive message loop exit, err: no close frame received or sent [conn_id=...]

[Lark] [2026-05-04 11:39:18,418] [INFO] trying to reconnect for the 1st time
[Lark] [2026-05-04 11:39:19,218] [INFO] connected to wss://msg-frontier.feishu.cn/ws/v2?fpid=493&aid=552564&device_id=7635876106516008146&...
[Lark] [2026-05-04 11:39:28,630] [ERROR] receive message loop exit, err: no close frame received or sent [conn_id=...]
```

## 关键特征

- 每次连接存活时间：**约 20-30 秒**（固定短命）
- `no close frame received or sent` = 飞书服务器主动关闭，不是网络抖动
- 每次重连后 `device_id` 都是新值
- Gateway 进程本身健康（PID 6370 稳定运行）
- 飞书后台看 bot 状态：连接数在累积，但每个连接很快被关闭

## 根因（本次）

> 飞书对同一 bot 的 WebSocket 并发连接数有限流。当一个连接被服务器主动关闭（而非正常关闭）时，可能是在触发配额保护机制。

## 解决方案（本次）

临时等待，让飞书清理会话池。长期方案：检查飞书开放平台「连接管理」中的在线连接数，若 bot 有多实例需合并或排队。
