# osu!gacha 挂机助手模块 (for KSCN QQBot)

为 `osugacha.com` 定制的高拟人、多用户并发自动开包与出货提醒模块。

## 核心特性
- **多用户隔离**：每个 QQ 用户拥有独立的 Session Cookie、开关状态与统计数据。
- **高拟人行为伪装**：自动伪造前端逆向出的 `Af()` 鼠标轨迹探针（`isTrusted=True`、`hidden=False`、随机 `moves`、随机坐标）。
- **离散时间轮调度**：单线程每 10 秒轻量扫描，用户随机在 6~18 分钟离散开包，拒绝固定频率。
- **安全熔断机制**：检测到服务端返回 `challenge_required`（人机挑战）时立即自杀关停并向 QQ 发送紧急报警，绝不反复盲目重试。
- **出货主动推送**：抽到 Epic / Legendary / Mythic / Divine / Signature 自动带图推送到 QQ。

## QQ 指令说明
- `>gacha bind <cURL/Cookie>` : 在私聊中绑定账号
- `>gacha on [小时数]` : 开启自动开包（默认 2 小时，范围 0.5 ~ 12 小时）
- `>gacha off` : 停止开包
- `>gacha status` : 查看当前挂机状态与今日统计
- `>gacha pull` : 手动立即开 1 包
- `>gacha unbind` : 解绑账号

