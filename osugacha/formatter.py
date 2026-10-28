from typing import Dict, Any, List

RARITY_CONFIG = {
    "common":    {"name": "Common",    "icon": "⚪", "level": 1},
    "uncommon":  {"name": "Uncommon",  "icon": "🟢", "level": 2},
    "rare":      {"name": "Rare",      "icon": "🔵", "level": 3},
    "epic":      {"name": "Epic",      "icon": "🟣", "level": 4},
    "legendary": {"name": "Legendary", "icon": "🟡", "level": 5},
    "mythic":    {"name": "Mythic",    "icon": "🔴", "level": 6},
    "divine":    {"name": "Divine",    "icon": "🌟", "level": 7},
    "signature": {"name": "Signature", "icon": "👑", "level": 8},
}

CLASS_MAP = {
    "dps": "⚔️输出",
    "tank": "🛡️坦克",
    "support": "💚辅助",
    "cc": "🌀控制",
}


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
    raw_rarity = str(card.get("rarity", "common")).lower()
    r_cfg = RARITY_CONFIG.get(raw_rarity, {"name": raw_rarity.capitalize(), "icon": "▫️", "level": 0})

    country = player.get("countryCode", "").upper()
    global_rank = player.get("globalRank")
    cls_raw = player.get("cls", "").lower()
    cls_name = CLASS_MAP.get(cls_raw, cls_raw)

    return {
        "username": username,
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


def format_pack_results(pulled_cards: List[Dict[str, Any]]) -> str:
    """
    纯文本格式化卡包展示信息，无图片干扰，排版整洁
    """
    if not pulled_cards:
        return "📦 本次开包未获得卡片或返回为空。"

    parsed_list = [parse_card_info(c) for c in pulled_cards]
    lines = [format_card_line(info, index=i) for i, info in enumerate(parsed_list, start=1)]

    return (
        "📦 【osu!gacha 开包结果】\n"
        "━━━━━━━━━━━━━━━\n"
        + "\n".join(lines)
    )
