from typing import Optional
import html

from .client import OsugachaClient
from .scheduler import send_qq_msg
from .formatter import format_user_profile


def handle_gacha_command(message: str, uid: int, gid: Optional[int] = None):
    """
    处理 >gacha 相关的所有 QQ 消息指令
    现已全面转型为安全合规的只读公开数据查询助手
    """
    uid_str = str(uid)
    gid_str = str(gid) if gid else None
    parts = message.strip().split(maxsplit=2)
    subcmd = parts[1].lower() if len(parts) > 1 else "help"

    if subcmd in ["help", "帮助"]:
        show_help(uid_str, gid_str)
    elif subcmd in ["stats", "status", "状态", "数据"]:
        target_user = parts[2].strip() if len(parts) > 2 else None
        handle_stats(uid_str, gid_str, target_user)
    elif subcmd in ["bind", "绑定", "unbind", "解绑", "on", "start", "开启", "off", "stop", "关闭", "pull", "抽", "开包"]:
        msg = (
            "⚠️ 【功能已下线通知】\n"
            "为全面响应 osu!gacha 1.0 反作弊升级并杜绝封号风险，账号绑定与自动挂机开包功能已永久下线。\n"
            "💡 请前往官方网站手动开包，珍爱账号！\n"
            "你可以使用 `>gacha stats <用户名>` 免费且安全地查询任意玩家主页数据与深渊进度。"
        )
        send_qq_msg(uid_str, msg, gid=gid_str)
    else:
        send_qq_msg(uid_str, "未知指令，请发送 `>gacha help` 查看可用功能。", gid=gid_str)


def show_help(uid: str, gid: Optional[str]):
    text = (
        "🎮 【osu!gacha 助手使用指南】\n"
        "━━━━━━━━━━━━━━━\n"
        "⚡ 【可用指令】\n"
        "• >gacha stats [用户名] : 查看任意玩家公开资料\n"
        "• >gacha help : 查看本帮助说明\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 在群内使用时，机器人的所有回复均会自动 @ 你，避免信息混乱。\n"
        "🔴 友情提示：osu!gacha 1.0 版本已全面升级反作弊监测，严禁使用任何连点器、外挂或自动化脚本，违者将被官方严厉封号。自动挂机开包功能已永久下线。"
    )
    send_qq_msg(uid, text, gid=gid)


def handle_stats(uid: str, gid: Optional[str], target_user: Optional[str] = None):
    """
    查询指定玩家的公开主页档案
    """
    if not target_user:
        send_qq_msg(
            uid,
            "❌ 请输入要查询的玩家用户名！\n示例：`>gacha stats noraneko`",
            gid=gid,
        )
        return

    display_name = html.unescape(target_user).strip()
    ok, profile_data, msg = OsugachaClient.fetch_public_profile(target_user)
    if not ok or not profile_data:
        send_qq_msg(uid, f"❌ 未能获取到玩家 [{display_name}] 的个人信息：{msg}", gid=gid)
        return

    reply = format_user_profile(profile_data)
    send_qq_msg(uid, reply, gid=gid)
