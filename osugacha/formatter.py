from typing import Dict, Any, List, Optional

RARITY_CONFIG = {
    "common":    {"name": "Common",    "icon": "⚪", "level": 1},
    "uncommon":  {"name": "Uncommon",  "icon": "🟢", "level": 2},
    "rare":      {"name": "Rare",      "icon": "🔵", "level": 3},
    "epic":      {"name": "Epic",      "icon": "🟣", "level": 4},
    "legendary": {"name": "Legendary", "icon": "🟡", "level": 5},
    "mythic":    {"name": "Mythic",    "icon": "🔴", "level": 6},
    "divine":    {"name": "Divine",    "icon": "🌟", "level": 7},
}

CLASS_MAP = {
    "dps": "⚔️输出",
    "tank": "🛡️坦克",
    "support": "💚辅助",
    "cc": "🌀控制",
}

PACK_TYPE_MAP = {
    "basic": "基础卡包",
    "golden": "🟨 黄金卡包",
    "radiant": "💎 璀璨卡包",
    "celestial": "🌌 天穹卡包",
    "prismatic": "🌈 棱彩卡包",
}


def get_pack_name(pack: Dict[str, Any]) -> str:
    """
    根据卡包对象的 slug / type 解析中文名称与图标
    """
    slug = (
        pack.get("slug")
        or pack.get("type")
        or (pack.get("pack", {}).get("slug") if isinstance(pack.get("pack"), dict) else None)
        or "basic"
    ).lower()
    return PACK_TYPE_MAP.get(slug, f"{slug.capitalize()}卡包")


def parse_card_info(card: Dict[str, Any]) -> Dict[str, Any]:
    """
    统一解析 osugacha 卡片数据结构
    """
    player = card.get("player") if isinstance(card.get("player"), dict) else {}
    username = (
        player.get("username")
        or card.get("username")
        or (card.get("name") if isinstance(card.get("name"), str) else None)
        or "未知选手"
    )
    avatar = (
        player.get("avatarUrl")
        or card.get("avatarUrl")
        or card.get("image")
        or ""
    )
    raw_rarity = str(card.get("rarity", "common")).lower()
    r_cfg = RARITY_CONFIG.get(raw_rarity, {"name": raw_rarity.capitalize(), "icon": "▫️", "level": 0})

    country = player.get("countryCode", "").upper()
    global_rank = player.get("globalRank")
    cls_raw = player.get("cls", "").lower()
    cls_name = CLASS_MAP.get(cls_raw, cls_raw)

    return {
        "username": username,
        "avatar": avatar,
        "rarity_key": raw_rarity,
        "rarity_name": r_cfg["name"],
        "rarity_icon": r_cfg["icon"],
        "rarity_level": r_cfg["level"],
        "country": country,
        "global_rank": global_rank,
        "cls_name": cls_name,
        "skill": player.get("skill", ""),
        "passive": player.get("passive", ""),
    }


def format_card_line(info: Dict[str, Any], index: int = 0) -> str:
    """
    将单张卡片格式化为纯文本的一行
    例如: 1. ⚪ [Common] PLAYAPEXLEGENDS [PH] (#94,052 · ⚔️输出)
    """
    prefix = f"{index}. " if index > 0 else ""
    r_tag = f"{info['rarity_icon']} [{info['rarity_name']}]"
    country_tag = f" [{info['country']}]" if info["country"] else ""

    extra_parts = []
    if info["global_rank"]:
        extra_parts.append(f"#{info['global_rank']:,}")
    if info["cls_name"]:
        extra_parts.append(info["cls_name"])

    extra_str = f" ({' · '.join(extra_parts)})" if extra_parts else ""

    return f"{prefix}{r_tag} {info['username']}{country_tag}{extra_str}"


def format_pack_results(pulled_cards: List[Dict[str, Any]], pack_name: Optional[str] = None) -> str:
    """
    纯文本格式化卡包展示信息，无图片干扰，排版整洁
    支持标明卡包的品质类型（如 基础 / 黄金 / 璀璨 / 天穹 / 棱彩）
    """
    if not pulled_cards:
        return "📦 本次开包未获得卡片或返回为空。"

    parsed_list = [parse_card_info(c) for c in pulled_cards]
    lines = [format_card_line(info, index=i) for i, info in enumerate(parsed_list, start=1)]

    title_part = f" · {pack_name}" if pack_name else ""
    header = f"📦 【osu!gacha 开包结果{title_part}】"

    return (
        f"{header}\n"
        "━━━━━━━━━━━━━━━\n"
        + "\n".join(lines)
    )


def format_user_profile(
    profile_data: Dict[str, Any],
    pack_info_str: Optional[str] = None,
    pity_info_str: Optional[str] = None,
    bot_stats: Optional[Dict[str, Any]] = None,
) -> str:
    """
    格式化用户个人信息面板
    - pack_info_str 和 bot_stats 存在时为“查自己”，否则为“查他人”
    """
    user = profile_data.get("user", {})
    stats = profile_data.get("stats", {})

    username = user.get("username", "未知")
    country = user.get("countryCode", "").upper()
    osu_id = user.get("osuUserId") or user.get("id", "")
    country_tag = f" [{country}]" if country else ""
    id_tag = f" (ID: {osu_id})" if osu_id else ""

    # 公会
    guild = user.get("guild")
    if guild and isinstance(guild, dict):
        tag = guild.get("tag", "")
        name = guild.get("name", "")
        guild_str = f"[{tag}] {name}" if tag else name
    else:
        guild_str = "无"

    # 等级与战力
    level = stats.get("level", {}).get("level", 1)
    power = stats.get("team", {}).get("power", 0)

    # 爬塔
    floor = stats.get("tower", {}).get("floor", 0)

    # 天梯 PVP
    pvp = stats.get("pvp") or {}
    rating = pvp.get("rating", 0)
    wins = pvp.get("wins", 0)
    losses = pvp.get("losses", 0)

    # 资产与藏卡
    value = stats.get("collection", {}).get("value", 0)
    cards_count = stats.get("collection", {}).get("cards", 0)

    # 图鉴
    dex = stats.get("dex") or {}
    caught = dex.get("caught", 0)
    total = dex.get("total", 0)
    pct = (caught / total * 100) if total else 0.0

    lines = [
        "👤 【osu!gacha 个人信息】",
        "━━━━━━━━━━━━━━━",
        f"• 玩家：{username}{country_tag}{id_tag}",
        f"• 公会：{guild_str}",
        f"• 等级：Lv.{level}",
        f"• 战力：⚔️ {power:,}",
        f"• 爬塔：🗼 第 {floor} 层",
        f"• 天梯：🏆 {rating} 分 ({wins}胜 {losses}负)",
        f"• 资产：⭐ {value:,}",
        f"• 藏卡：📦 {cards_count:,} 张",
        f"• 图鉴：📚 {caught:,} / {total:,} ({pct:.2f}%)",
    ]

    # 如果有自动开卡状态信息 (查自己)
    if bot_stats:
        lines.append("━━━━━━━━━━━━━━━")
        lines.append("⚙️ 【自动开卡】")
        lines.append(f"• 挂机状态：{bot_stats.get('status_str', '🔴 已停止')}")
        if pack_info_str:
            lines.append(f"• 可用卡包：{pack_info_str}")
        if pity_info_str:
            lines.append(f"• 传说保底：{pity_info_str}")
        if bot_stats.get("is_running"):
            lines.append(f"• 下次开包：{bot_stats.get('next_in_str', '--')}")
        lines.append(f"• 今日开包：{bot_stats.get('today_opened', bot_stats.get('total_opened', 0))} 包")
        lines.append(f"• 今日最佳：{bot_stats.get('today_best', bot_stats.get('best_pull', '暂无'))}")

    return "\n".join(lines)
