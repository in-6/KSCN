import time
import datetime
from typing import Optional

from .client import OsugachaClient, extract_cookie_from_text
from .storage import storage
from .scheduler import send_qq_msg, scheduler
from .formatter import format_pack_results


def handle_gacha_command(message: str, uid: int, gid: Optional[int] = None):
    """
    处理 >gacha 相关的所有 QQ 消息指令
    """
    uid_str = str(uid)
    gid_str = str(gid) if gid else None
    parts = message.strip().split(maxsplit=2)
    subcmd = parts[1].lower() if len(parts) > 1 else "help"

    if subcmd in ["help", "帮助"]:
        show_help(uid_str, gid_str)
    elif subcmd in ["bind", "绑定"]:
        handle_bind(uid_str, gid_str, message)
    elif subcmd in ["unbind", "解绑"]:
        handle_unbind(uid_str, gid_str)
    elif subcmd in ["on", "start", "开启"]:
        hours_str = parts[2] if len(parts) > 2 else "2"
        handle_start(uid_str, gid_str, hours_str)
    elif subcmd in ["off", "stop", "关闭"]:
        handle_stop(uid_str, gid_str)
    elif subcmd in ["status", "状态"]:
        handle_status(uid_str, gid_str)
    elif subcmd in ["pull", "抽", "开包"]:
        handle_manual_pull(uid_str, gid_str)
    else:
        send_qq_msg(uid_str, "未知指令，请发送 `>gacha help` 查看说明。", gid=gid_str)


def show_help(uid: str, gid: Optional[str]):
    text = (
        "🎮 【osu!gacha 挂机助手使用指南】\n"
        "━━━━━━━━━━━━━━━\n"
        "1. 电脑浏览器登录 osugacha.com\n"
        "2. 按键盘 F12（开发者工具）-> 选【网络/Network】\n"
        "3. 刷新页面，在列表中随便找一个请求右键\n"
        "   -> 复制(Copy) -> 复制为 cURL (Copy as cURL)\n"
        "4. 点击机器人头像【私聊】发送：\n"
        "   >gacha bind [粘贴刚复制的整段内容]\n"
        "━━━━━━━━━━━━━━━\n"
        "⚡ 【常用控制指令】\n"
        "• >gacha on [小时数] : 开启自动开包 (如 >gacha on 3)\n"
        "• >gacha off : 立即停止挂机\n"
        "• >gacha status : 查看当前挂机状态与出货统计\n"
        "• >gacha pull : 手动开 1 包测试欧气\n"
        "• >gacha unbind : 解除账号绑定\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 提示：在群内使用时，机器人的所有回复与出货战报均会自动 @ 你，避免信息混乱。"
    )
    send_qq_msg(uid, text, gid=gid)


def handle_bind(uid: str, gid: Optional[str], raw_message: str):
    # 安全检查：禁止在群聊中发送 Cookie/cURL
    if gid:
        send_qq_msg(
            uid,
            "⚠️ 为了你的账号隐私安全，请点击机器人头像，在【私聊】中发送绑定命令！",
            gid=gid,
        )
        return

    # 从消息中截取参数
    # 消息格式: >gacha bind <content>
    content = raw_message.split(maxsplit=2)
    if len(content) < 3:
        send_qq_msg(
            uid,
            "绑定格式错误！正确格式：\n"
            ">gacha bind <你的Cookie或复制的cURL>\n\n"
            "💡 获取方法：电脑按 F12 -> Network -> 随便右键一个请求 -> Copy as cURL，直接整段粘贴发过来即可。",
        )
        return

    raw_payload = content[2]
    cookie = extract_cookie_from_text(raw_payload)

    if not cookie:
        send_qq_msg(uid, "❌ 未能从你发送的内容中提取到有效 Cookie，请确认复制完整。")
        return

    # 验证 Cookie
    client = OsugachaClient(cookie)
    ok, user_info, msg = client.verify()

    if not ok or not user_info:
        send_qq_msg(uid, f"❌ 凭据验证失败: {msg}\n请确认已在 osugacha.com 保持登录并重新复制。")
        return

    osu_username = user_info.get("username") or user_info.get("name") or "未知玩家"
    osu_id = user_info.get("osuUserId") or user_info.get("id") or 0

    user_data = {
        "cookie": cookie,
        "osu_username": osu_username,
        "osu_id": osu_id,
        "is_running": False,
        "stop_timestamp": 0,
        "next_pull_time": 0,
        "min_interval": 360,   # 最小随机开包间隔 6 分钟
        "max_interval": 1080,  # 最大随机开包间隔 18 分钟
        "gid": None,
        "stats": {
            "session_opened": 0,
            "total_opened": 0,
            "best_pull": "暂无",
        },
    }

    storage.save_user(uid, user_data)
    send_qq_msg(
        uid,
        f"✅ 【osugacha 绑定成功】\n"
        f"绑定玩家: {osu_username} (ID: {osu_id})\n"
        f"发送 `>gacha on 3` 即可开启 3 小时自动开包！",
    )


def handle_unbind(uid: str, gid: Optional[str]):
    user = storage.get_user(uid)
    if not user:
        send_qq_msg(uid, "你尚未绑定任何 osugacha 账号。", gid=gid)
        return

    storage.delete_user(uid)
    send_qq_msg(uid, "✅ 已成功解除 osugacha 账号绑定并清除数据。", gid=gid)


def handle_start(uid: str, gid: Optional[str], hours_str: str):
    user = storage.get_user(uid)
    if not user:
        send_qq_msg(uid, "❌ 你还没有绑定账号！请先私聊机器人发送 `>gacha bind <cURL>` 完成绑定。", gid=gid)
        return

    try:
        hours = float(hours_str)
        if hours <= 0 or hours > 12:
            send_qq_msg(uid, "❌ 单次挂机时长建议设置在 0.5 到 12 小时之间，防止被官方检测。", gid=gid)
            return
    except ValueError:
        send_qq_msg(uid, "❌ 时长格式错误，请输入数字（如 `>gacha on 3` 或 `>gacha on 1.5`）。", gid=gid)
        return

    now = time.time()
    stop_ts = now + hours * 3600
    # 首次开包在 30~80 秒后触发
    first_pull = now + 45
    stop_time_str = datetime.datetime.fromtimestamp(stop_ts).strftime("%H:%M")

    stats = user.get("stats", {})
    stats["session_opened"] = 0

    storage.update_user_fields(
        uid,
        is_running=True,
        stop_timestamp=stop_ts,
        next_pull_time=first_pull,
        gid=gid,
        stats=stats,
    )

    send_qq_msg(
        uid,
        f"🟢 【AutoGacha 挂机已开启】\n"
        f"• 挂机时长: {hours} 小时 (预计 {stop_time_str} 自动停机)\n"
        f"• 拟人间隔: 6 ~ 18 分钟随机波动\n"
        f"• 首次开包预计将在 1 分钟内进行，祝你开出Divine！",
        gid=gid,
    )


def handle_stop(uid: str, gid: Optional[str]):
    user = storage.get_user(uid)
    if not user or not user.get("is_running"):
        send_qq_msg(uid, "你当前没有正在运行的开包任务。", gid=gid)
        return

    stats = user.get("stats", {})
    session_opened = stats.get("session_opened", 0)
    storage.update_user_fields(uid, is_running=False)

    send_qq_msg(
        uid,
        f"🔴 【AutoGacha 挂机已停止】\n本次挂机共开包: {session_opened} 次。",
        gid=gid,
    )


def handle_status(uid: str, gid: Optional[str]):
    user = storage.get_user(uid)
    if not user:
        send_qq_msg(uid, "❌ 你还没有绑定账号！请先私聊机器人发送 `>gacha bind <cURL>`。", gid=gid)
        return

    now = time.time()
    is_running = user.get("is_running", False)
    status_text = "🟢 运行中" if is_running else "🔴 已停止"
    username = user.get("osu_username", "未知")

    stop_ts = user.get("stop_timestamp", 0)
    next_ts = user.get("next_pull_time", 0)
    stats = user.get("stats", {})

    remaining_str = "--"
    next_in_str = "--"

    if is_running:
        rem_sec = max(0, int(stop_ts - now))
        remaining_str = f"{rem_sec // 3600}小时{(rem_sec % 3600) // 60}分"

        next_sec = max(0, int(next_ts - now))
        next_in_str = f"约 {next_sec // 60} 分钟后"

    reply = (
        f"📊 【osu!gacha 状态看板】\n"
        f"• 绑定账号: {username}\n"
        f"• 挂机状态: {status_text}\n"
        f"• 剩余时间: {remaining_str}\n"
        f"• 下次开包: {next_in_str}\n"
        f"• 今日开包: {stats.get('total_opened', 0)} 包\n"
        f"• 最佳出货: {stats.get('best_pull', '暂无')}"
    )
    send_qq_msg(uid, reply, gid=gid)


def handle_manual_pull(uid: str, gid: Optional[str]):
    user = storage.get_user(uid)
    if not user:
        send_qq_msg(uid, "❌ 请先私聊机器人发送 `>gacha bind <cURL>` 绑定账号。", gid=gid)
        return

    client = OsugachaClient(user.get("cookie", ""))
    ok, inv_data, msg = client.get_inventory()

    if not ok or not inv_data:
        send_qq_msg(uid, f"❌ 获取卡包失败: {msg}", gid=gid)
        return

    packs = inv_data if isinstance(inv_data, list) else inv_data.get("packs", inv_data.get("items", []))
    if not packs:
        send_qq_msg(uid, "📦 当前没有可开的卡包，等待自然回复中（1包/分钟，上限10包）。", gid=gid)
        return

    first_pack = packs[0]
    pack_id = first_pack.get("id") or first_pack.get("inventoryId") or first_pack.get("packId")

    open_ok, open_data, open_msg = client.open_pack(pack_id)
    if not open_ok:
        send_qq_msg(uid, f"❌ 开包失败: {open_msg}", gid=gid)
        return

    # 解析抽出的卡片并排版美化 (纯文本，无图片刷屏)
    pulled_cards = (
        open_data.get("cards", [])
        if isinstance(open_data, dict)
        else (open_data if isinstance(open_data, list) else [])
    )

    reply = format_pack_results(pulled_cards)
    send_qq_msg(uid, reply, gid=gid)

