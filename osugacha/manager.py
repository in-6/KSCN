import html
from typing import Optional

from .client import OsugachaClient
from .scheduler import send_qq_msg
from .formatter import (
    format_user_profile,
    format_market_listings,
    format_player_owners,
)


def handle_gacha_command(message: str, uid: int, gid: Optional[int] = None):
    """
    处理 >gacha 相关的所有 QQ 消息指令
    现已全面转型为安全合规的官方 API 只读查询助手
    """
    uid_str = str(uid)
    gid_str = str(gid) if gid else None
    parts = message.strip().split(maxsplit=2)
    subcmd = parts[1].lower() if len(parts) > 1 else "help"
    arg = parts[2].strip() if len(parts) > 2 else None

    if subcmd in ["help", "帮助"]:
        show_help(uid_str, gid_str)
    elif subcmd in ["stats", "status", "状态", "数据", "info", "me", "profile"]:
        handle_stats(uid_str, gid_str, arg)
    elif subcmd in ["mkt", "market", "市场", "行情", "市价"]:
        handle_market(uid_str, gid_str, arg)
    elif subcmd in ["owners", "owner", "持有", "榜单", "find"]:
        handle_owners(uid_str, gid_str, arg)
    elif subcmd in ["bind", "绑定", "unbind", "解绑", "on", "start", "开启", "off", "stop", "关闭", "pull", "抽", "开包", "card", "卡片", "卡面"]:
        msg = (
            "⚠️ 【功能调整通知】\n"
            "为全面响应 osu!gacha 1.0 反作弊升级并杜绝封号风险，账号绑定与自动挂机开包已永久下线。\n"
            "💡 请前往官方网站手动开包，珍爱账号！\n"
            "现在你可以安全使用官方只读查询功能：\n"
            "• `>gacha stats <玩家名>` : 查询主页战力与爬塔/深渊进度\n"
            "• `>gacha mkt [-c|-m|-i] [关键词]` : 实时集市行情与成交中位数\n"
            "• `>gacha owners <选手名>` : 查询选手卡片大藏家榜单"
        )
        send_qq_msg(uid_str, msg, gid=gid_str)
    else:
        send_qq_msg(uid_str, "未知指令，请发送 `>gacha help` 查看可用功能。", gid=gid_str)


def show_help(uid: str, gid: Optional[str]):
    text = (
        "🎮 【osu!gacha 助手使用指南】\n"
        "━━━━━━━━━━━━━━━\n"
        "⚡ 【可用指令】\n"
        "• >gacha stats [玩家名] : 查询公开个人信息 (含战力/爬塔/深渊/藏卡)\n"
        "• >gacha mkt : 查看集市最新上架卡片一口价\n"
        "• >gacha mkt -c [卡牌名] [--sig] [--auc] : 查询卡牌在售挂单 (加 --sig 查签名卡，加 --auc 查拍卖)\n"
        "• >gacha mkt --auc : 查看全服最新卡片拍卖\n"
        "• >gacha mkt -m [--auc] : 查看最新上架/拍卖 Mod\n"
        "• >gacha mkt -i [--auc] : 查看最新上架/拍卖物品\n"
        "• >gacha owners [选手名] : 查看该选手卡片的持有者巨佬榜单\n"
        "• >gacha help : 查看本帮助说明\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 在群内使用时，机器人的所有回复均会自动 @ 你，避免信息混乱。\n"
        "🔴 友情提示：osu!gacha 1.0 版本已全面升级反作弊监测，严禁使用任何连点器、外挂或自动化脚本。自动挂机开包功能已永久下线。"
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


def handle_market(uid: str, gid: Optional[str], arg: Optional[str] = None):
    """
    处理 >gacha mkt 市场行情查询
    - >gacha mkt 或 >gacha mkt -c : 最新 8 个卡片挂单
    - >gacha mkt -c [卡片名] [--sig] [--auc] : 查询卡牌在售挂单或拍卖及成交均价/中位数
    - >gacha mkt --auc : 最新 8 个卡片拍卖
    - >gacha mkt -m [--auc] : 最新 8 个 Mod 挂单或拍卖
    - >gacha mkt -i [--auc] : 最新 8 个物品挂单或拍卖
    """
    kind = "card"
    is_sig = False
    is_auction = False
    tokens = arg.strip().split() if arg else []

    # 检查是否包含 --sig 与 --auc
    filtered_tokens = []
    for tok in tokens:
        low = tok.lower()
        if low in ["--sig", "-sig", "--signature", "-signature"]:
            is_sig = True
        elif low in ["--auc", "-auc", "--auction", "-auction", "-拍卖", "拍卖"]:
            is_auction = True
        else:
            filtered_tokens.append(tok)

    query = None
    if filtered_tokens:
        first = filtered_tokens[0].lower()
        if first in ["-m", "/m", "-mod", "mod"]:
            kind = "mod"
            query = " ".join(filtered_tokens[1:]).strip() if len(filtered_tokens) > 1 else None
        elif first in ["-i", "/i", "-item", "item", "-物品", "物品"]:
            kind = "item"
            query = " ".join(filtered_tokens[1:]).strip() if len(filtered_tokens) > 1 else None
        elif first in ["-c", "/c", "-card", "card", "-卡片", "卡片"]:
            kind = "card"
            query = " ".join(filtered_tokens[1:]).strip() if len(filtered_tokens) > 1 else None
        else:
            kind = "card"
            query = " ".join(filtered_tokens).strip()

    # --sig 必须配合指定卡牌名称查询，不提供单独全服签名卡浏览
    if is_sig and not query:
        send_qq_msg(
            uid,
            "❌ 请输入要查询签名卡的选手名称！\n示例：`>gacha mkt Camo --sig`",
            gid=gid,
        )
        return

    rarity = "signature" if (is_sig and kind == "card") else None
    mode = "auction" if is_auction else None

    guide_data = None
    if kind == "card" and query:
        # 查询特定卡片 (支持普通/限定签名卡，一口价或拍卖)
        ok, data, msg = OsugachaClient.search_market(kind="card", query=query, rarity=rarity, mode=mode, limit=8)
        if not ok or not data:
            action_desc = "拍卖" if is_auction else "市场卡片"
            send_qq_msg(uid, f"❌ 查询{action_desc}失败：{msg}", gid=gid)
            return

        items = data.get("items", [])
        if items:
            first_card_id = items[0].get("card", {}).get("id")
            if first_card_id:
                ok_g, g_data, _ = OsugachaClient.get_market_guide(card_id=first_card_id)
                if ok_g and g_data:
                    guide_data = g_data

        reply = format_market_listings(
            data, kind="card", query=query, guide=guide_data, is_sig=is_sig, is_auction=is_auction
        )
        send_qq_msg(uid, reply, gid=gid)
    else:
        # 查询最新列表 (card, mod, item，支持 --auc 拍卖)
        ok, data, msg = OsugachaClient.search_market(kind=kind, rarity=rarity, mode=mode, limit=8)
        if not ok or not data:
            action_desc = "拍卖" if is_auction else "市场挂单"
            send_qq_msg(uid, f"❌ 查询{action_desc}失败：{msg}", gid=gid)
            return

        reply = format_market_listings(data, kind=kind, is_sig=is_sig, is_auction=is_auction)
        send_qq_msg(uid, reply, gid=gid)


def handle_owners(uid: str, gid: Optional[str], target_player: Optional[str] = None):
    """
    查询选手卡片的持有者榜单
    """
    if not target_player:
        send_qq_msg(
            uid,
            "❌ 请输入要查询持有榜的选手名称！\n示例：`>gacha owners BTMC`",
            gid=gid,
        )
        return

    display_name = html.unescape(target_player).strip()
    ok, p_data, msg = OsugachaClient.search_players(target_player, limit=5)
    if not ok or not p_data or not p_data.get("items"):
        send_qq_msg(uid, f"❌ 未能找到选手 [{display_name}]：{msg}", gid=gid)
        return

    items = p_data["items"]
    matched = next((p for p in items if p.get("username", "").lower() == display_name.lower()), items[0])
    pid = matched.get("id")
    pname = matched.get("username", display_name)

    ok_owners, owners_data, msg_owners = OsugachaClient.get_player_owners(pid)
    if not ok_owners or owners_data is None:
        send_qq_msg(uid, f"❌ 获取 [{pname}] 的持有者榜单失败：{msg_owners}", gid=gid)
        return

    reply = format_player_owners(owners_data, pname)
    send_qq_msg(uid, reply, gid=gid)


