from typing import Dict, Any, List, Optional, Tuple

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
    "legendary": "💎 璀璨卡包",  # 对应官方 slug: "legendary"
    "radiant": "💎 璀璨卡包",    # 对应别名 radiant
    "mythic": "🌌 天穹卡包",     # 对应官方 slug: "mythic"
    "celestial": "🌌 天穹卡包",  # 对应别名 celestial
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


def format_user_profile(profile_data: Dict[str, Any]) -> str:
    """
    格式化玩家公开个人信息面板
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

    # 爬塔 (Tower / Climb - 向上探索) 与 深渊 (Depths - 向下探索)
    climb = stats.get("climb") or stats.get("tower") or {}
    tower_floor = climb.get("best", climb.get("floor", 0))
    depths = stats.get("depths") or {}
    depths_floor = depths.get("best", 0)

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
        f"• 爬塔：🗼 第 {tower_floor} 层",
        f"• 深渊：🌀 第 {depths_floor} 层",
        f"• 天梯：🏆 {rating} 分 ({wins}胜 {losses}负)",
        f"• 藏卡：📦 {cards_count:,} 张 (价值：⭐{value:,})",
        f"• 图鉴：📚 {caught:,} / {total:,} ({pct:.2f}%)",
    ]

    return "\n".join(lines)


# 词条与物品映射
MOD_RARITY_ICONS = {
    1: ("⚪", "1星"),
    2: ("🟢", "2星"),
    3: ("🔵", "3星"),
    4: ("🟣", "4星"),
    5: ("🟡", "5星"),
    6: ("🔴", "6星"),
    7: ("🌟", "7星"),
}

STAT_NAMES = {
    "atk": "攻击",
    "atkPct": "攻击",
    "hp": "生命",
    "hpPct": "生命",
    "def": "防御",
    "defPct": "防御",
    "spd": "速度",
    "speed": "速度",
    "critRate": "暴击率",
    "critDmg": "暴击伤害",
    "guardDmg": "削韧",
    "guard": "韧性",
    "outHeal": "治疗加成",
    "healing": "治疗",
    "maxHp": "最大生命",
}

ITEM_NAMES = {
    "fuel": "⛽ 燃料",
    "stamina_potion": "🧪 体力药水",
    "banner_key": "🗝️ 卡池钥匙",
    "replay_1": "📼 铜回放",
    "replay_2": "📼 银回放",
    "replay_3": "📼 金回放",
    "insignia_tank_1": "🛡️ 坦克I徽章",
    "insignia_tank_2": "🛡️ 坦克II徽章",
    "insignia_tank_3": "🛡️ 坦克III徽章",
    "insignia_tank_4": "🛡️ 坦克IV徽章",
    "insignia_dps_1": "⚔️ 输出I徽章",
    "insignia_dps_2": "⚔️ 输出II徽章",
    "insignia_dps_3": "⚔️ 输出III徽章",
    "insignia_dps_4": "⚔️ 输出IV徽章",
    "insignia_support_1": "💚 辅助I徽章",
    "insignia_support_2": "💚 辅助II徽章",
    "insignia_support_3": "💚 辅助III徽章",
    "insignia_support_4": "💚 辅助IV徽章",
    "insignia_cc_1": "🌀 控制I徽章",
    "insignia_cc_2": "🌀 控制II徽章",
    "insignia_cc_3": "🌀 控制III徽章",
    "insignia_cc_4": "🌀 控制IV徽章",
    "boss_trophy": "🏆 Boss奖杯",
    "platinum_trophy": "🏆 白金奖杯",
    "diamond_trophy": "💎 钻石奖杯",
    "emerald_trophy": "🟢 翡翠奖杯",
    "mod_fragment": "🧩 Mod碎片",
}

SETUP_KIND_NAMES = {
    "tablet": "🖊️数位板",
    "mouse": "🖱️鼠标",
    "keyboard": "⌨️键盘",
    "touchscreen": "📱触屏",
    "editor": "🎛️编辑器",
}

SETUP_TIER_INFO = {
    2: ("⚪", "1级"),
    3: ("🟢", "2级"),
    4: ("🔵", "3级"),
    5: ("🟡", "4级"),
    6: ("🔴", "5级"),
}

STONE_KIND_NAMES = {
    "sharp": "🔪 锐石 (Sharp)",
    "gem": "💎 宝石 (Gem)",
}

ROMAN_GRADES = {1: "I", 2: "II", 3: "III"}


def format_mod_main_stat(main: Optional[Dict[str, Any]]) -> str:
    """格式化 Mod 主词条"""
    if not main:
        return "无属性"
    stat_key = main.get("stat", "")
    val = main.get("value", 0)
    name = STAT_NAMES.get(stat_key, stat_key)
    if "pct" in stat_key.lower() or stat_key in ["critRate", "critDmg", "guardDmg", "outHeal"]:
        val_str = f"+{val * 100:.1f}%"
    else:
        val_str = f"+{val:.0f}" if isinstance(val, (int, float)) and val == int(val) else f"+{val}"
    return f"{name} {val_str}"


def format_item_name(item_obj: Optional[Dict[str, Any]]) -> Tuple[str, int]:
    """格式化物品名称与数量"""
    if not item_obj:
        return "未知物品", 1
    item_id = item_obj.get("id", "")
    qty = item_obj.get("qty", 1)
    name = ITEM_NAMES.get(item_id)
    if not name:
        parts = item_id.split("_")
        if parts[0] == "insignia" and len(parts) >= 3:
            cls_cn = {"tank": "🛡️ 坦克", "dps": "⚔️ 输出", "support": "💚 辅助", "cc": "🌀 控制"}.get(parts[1], parts[1])
            tier_cn = {"1": "铜", "2": "银", "3": "金"}.get(parts[2], parts[2])
            name = f"{cls_cn}{tier_cn}徽章"
        else:
            name = f"📦 {item_id}"
    return name, qty


def format_time_remaining(ends_at_str: Optional[str]) -> str:
    """计算拍卖剩余时间友好描述"""
    if not ends_at_str:
        return ""
    try:
        from datetime import datetime, timezone
        ends_dt = datetime.fromisoformat(ends_at_str.replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        diff = (ends_dt - now_dt).total_seconds()
        if diff <= 0:
            return "已结束"
        hours = int(diff // 3600)
        minutes = int((diff % 3600) // 60)
        if hours >= 24:
            days = hours // 24
            rem_hours = hours % 24
            return f"剩{days}天{rem_hours}小时"
        elif hours > 0:
            return f"剩{hours}小时{minutes}分"
        else:
            return f"剩{max(1, minutes)}分钟"
    except Exception:
        return ""


def _format_guide_block(
    guide: Dict[str, Any],
    total: int,
    type_desc: str = "卡牌",
    unit_label: str = "张",
) -> List[str]:
    """统一格式化近 30 天官方成交指导价统计块"""
    sales = guide.get("sales", 0)
    days = guide.get("days", 30)
    median = guide.get("median")
    highest = guide.get("highest")
    lowest_guide = guide.get("lowest")
    listed = guide.get("listed", total)

    median_str = f"⭐{median:,.0f}" if isinstance(median, (int, float)) else (f"⭐{median}" if median is not None else "暂无")
    highest_str = f"⭐{highest:,}" if isinstance(highest, (int, float)) else (f"⭐{highest}" if highest is not None else "暂无")
    lowest_str = f"⭐{lowest_guide:,}" if isinstance(lowest_guide, (int, float)) else (f"⭐{lowest_guide}" if lowest_guide is not None else "暂无")

    return [
        f"📊 【近 {days} 天{type_desc}成交统计】",
        f"• 成交频次：累计成交 {sales:,} 次",
        f"• 中位售价：{median_str}",
        f"• 历史最高：{highest_str}",
        f"• 当前在售：{listed:,} {unit_label} (最低在售: {lowest_str})",
        "━━━━━━━━━━━━━━━",
    ]


def format_item_book_summary(book_data: Dict[str, Any]) -> str:
    """
    格式化全服物品实时盘口总览 (GET /api/market/book)
    """
    items = book_data.get("items", [])
    header = "🛒 【osu!gacha 物品实时盘口总览】"
    if not items:
        return f"{header}\n━━━━━━━━━━━━━━━\n暂无物品盘口数据。"

    # 精选常用核心物品顺序展示，附带查询短码避免黑箱
    priority_items = [
        ("fuel", "fuel"),
        ("banner_key", "key"),
        ("replay_1", "replay1"),
        ("replay_2", "replay2"),
        ("replay_3", "replay3"),
        ("boss_trophy", "trophy1"),
        ("platinum_trophy", "trophy2"),
        ("diamond_trophy", "trophy3"),
        ("emerald_trophy", "trophy4"),
        ("insignia_dps_3", "dps3"),
        ("insignia_dps_4", "dps4"),
        ("insignia_tank_3", "tank3"),
        ("insignia_tank_4", "tank4"),
        ("insignia_support_3", "support3"),
        ("insignia_support_4", "support4"),
        ("insignia_cc_3", "cc3"),
        ("insignia_cc_4", "cc4"),
        ("mod_fragment", "fragment"),
    ]
    item_map = {it.get("itemId"): it for it in items}

    lines = [
        header,
        "━━━━━━━━━━━━━━━",
        "格式：物品 [查询码]：最低卖价 / 最高买价",
        "━━━━━━━━━━━━━━━",
    ]
    for iid, short_code in priority_items:
        it = item_map.get(iid)
        if not it:
            continue
        name = ITEM_NAMES.get(iid, iid)
        buy_p = it.get("buy")
        sell_p = it.get("sell")
        offered = it.get("offered", 0)
        buy_str = f"⭐{buy_p:,}" if buy_p is not None else "无货"
        sell_str = f"⭐{sell_p:,}" if sell_p is not None else "无求购"
        lines.append(f"• {name} [{short_code}]：{buy_str} / {sell_str} (在售 {offered:,})")

    lines.append("━━━━━━━━━━━━━━━")
    lines.append("💡 查单品详细盘口与均价：`>gacha mkt -i <查询码>` (徽章还支持 dps1/2、tank1/2 等)")
    return "\n".join(lines)


def format_item_book_detail(
    item_id: str,
    book_detail: Dict[str, Any],
    days_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    格式化单个物品的实时买卖单盘口与近期成交中位价趋势
    """
    name = ITEM_NAMES.get(item_id, f"📦 {item_id}")
    sells = book_detail.get("sells", [])
    buys = book_detail.get("buys", [])
    offered = book_detail.get("offered", 0)
    wanted = book_detail.get("wanted", 0)

    lines = [
        f"🛒 【osu!gacha 物品行情 · {name}】",
        "━━━━━━━━━━━━━━━",
    ]

    # 近 30 天与近 7 天成交统计
    if days_data and days_data.get("days"):
        days_list = days_data.get("days", [])
        total_sales_30 = sum(d.get("sales", 0) for d in days_list)
        total_units_30 = sum(d.get("units", 0) for d in days_list)
        recent_7 = days_list[-7:]
        medians_7 = [d.get("median") for d in recent_7 if isinstance(d.get("median"), (int, float))]
        avg_med_7 = (sum(medians_7) / len(medians_7)) if medians_7 else None
        latest_day = days_list[-1]
        latest_med = latest_day.get("median")

        lines.append("📊 【近期成交趋势】")
        lines.append(f"• 近30天成交：{total_sales_30:,} 笔 (共 {total_units_30:,} 个)")
        if latest_med is not None:
            lines.append(f"• 最新日均中位：⭐{latest_med:,.1f} ({latest_day.get('day', '')})")
        if avg_med_7 is not None:
            lines.append(f"• 近7日中位均值：⭐{avg_med_7:,.1f}")
        lines.append("━━━━━━━━━━━━━━━")

    lines.append(f"📤 【最低卖单 (总在售 {offered:,})】")
    if sells:
        for idx, s in enumerate(sells[:5], 1):
            lines.append(f"  {idx}. ⭐{s.get('price', 0):,} × {s.get('qty', 0):,}")
    else:
        lines.append("  暂无在售卖单")

    lines.append(f"📥 【最高求购 (总求购 {wanted:,})】")
    if buys:
        for idx, b in enumerate(buys[:5], 1):
            lines.append(f"  {idx}. ⭐{b.get('price', 0):,} × {b.get('qty', 0):,}")
    else:
        lines.append("  暂无求购订单")

    return "\n".join(lines)


def format_market_listings(
    data: Dict[str, Any],
    kind: str = "card",
    query: Optional[str] = None,
    guide: Optional[Dict[str, Any]] = None,
    is_sig: bool = False,
    is_auction: bool = False,
) -> str:
    """
    格式化市场挂单列表 (支持 -c 卡片, -m Mod, -i 物品, -d 外设, -st 强化石, --sig 签名卡, --auc 拍卖, 以及近30天成交指导价)
    """
    total = data.get("total", 0)
    items = data.get("items", [])
    mode_icon = "🔨" if is_auction else "🛒"
    mode_name = "市场拍卖" if is_auction else "市场行情"

    if kind == "mod":
        title_part = f" · Mod ({query})" if query else " · 最新 Mod"
        header = f"{mode_icon} 【osu!gacha {mode_name}{title_part}】"
        lines = [header, "━━━━━━━━━━━━━━━"]
        if query and guide:
            lines.extend(_format_guide_block(guide, total, type_desc="同类 Mod", unit_label="个"))
        if not items:
            lines.append(f"暂无{('拍卖中的' if is_auction else '在售')} Mod。")
            return "\n".join(lines)
        list_desc = (
            f"🏷️ 【当前正在拍卖 (前 {len(items)} 个)】"
            if is_auction
            else (f"🏷️ 【当前最低在售 (共 {total:,} 个，前 {len(items)} 个)】" if query else f"在售总量：{total:,} 个 (展示最新 {len(items)} 个)")
        )
        lines.append(list_desc)
        for idx, item in enumerate(items, 1):
            price = item.get("price", 0)
            seller = item.get("seller", {}).get("username", "神秘卖家")
            m = item.get("mod", {}) or {}
            m_type = str(m.get("type", "MOD")).upper()
            rarity_num = m.get("rarity", 1)
            icon, r_name = MOD_RARITY_ICONS.get(rarity_num, ("▫️", f"{rarity_num}星"))
            level = m.get("level", 0)
            main_stat = format_mod_main_stat(m.get("main"))

            if is_auction:
                auc = item.get("auction") or {}
                bids = auc.get("bids", 0)
                leader = auc.get("leader", {}).get("username") if auc.get("leader") else None
                rem_str = format_time_remaining(auc.get("endsAt"))
                rem_tag = f" ({rem_str})" if rem_str else ""
                bid_status = f"当前⭐{price:,} ({bids}次出价) | 领先: {leader}{rem_tag}" if (bids > 0 and leader) else f"起拍⭐{price:,} (暂无出价) | 发起: {seller}{rem_tag}"
                lines.append(f"{idx}. 🔨 {bid_status}\n   {icon} {m_type}+{level} [{r_name}] ({main_stat})")
            else:
                lines.append(f"{idx}. ⭐{price:,} | 卖家: {seller}\n   {icon} {m_type}+{level} [{r_name}] ({main_stat})")
        return "\n".join(lines)

    elif kind == "setup":
        title_part = f" · 外设 ({query})" if query else " · 最新外设"
        header = f"{mode_icon} 【osu!gacha {mode_name}{title_part}】"
        lines = [header, "━━━━━━━━━━━━━━━"]
        if query and guide:
            lines.extend(_format_guide_block(guide, total, type_desc="同类外设", unit_label="件"))
        if not items:
            lines.append(f"暂无{('拍卖中的' if is_auction else '在售')}外设。")
            return "\n".join(lines)
        list_desc = (
            f"🏷️ 【当前正在拍卖 (前 {len(items)} 件)】"
            if is_auction
            else (f"🏷️ 【当前最低在售 (共 {total:,} 件，前 {len(items)} 件)】" if query else f"在售总量：{total:,} 件 (展示最新 {len(items)} 件)")
        )
        lines.append(list_desc)
        for idx, item in enumerate(items, 1):
            price = item.get("price", 0)
            seller = item.get("seller", {}).get("username", "神秘卖家")
            s = item.get("setup", {}) or {}
            s_kind = SETUP_KIND_NAMES.get(s.get("kind", ""), s.get("kind", "外设"))
            ult = s.get("ultimate", "")
            g_sum = s.get("gradeSum", 2)
            t_icon, t_name = SETUP_TIER_INFO.get(g_sum, ("▫️", f"总阶{g_sum}"))
            attrs = s.get("attrs") or []
            attr_str = " / ".join(f"{a.get('id', '')} {ROMAN_GRADES.get(a.get('grade', 1), str(a.get('grade', 1)))}" for a in attrs)

            if is_auction:
                auc = item.get("auction") or {}
                bids = auc.get("bids", 0)
                leader = auc.get("leader", {}).get("username") if auc.get("leader") else None
                rem_str = format_time_remaining(auc.get("endsAt"))
                rem_tag = f" ({rem_str})" if rem_str else ""
                bid_status = f"当前⭐{price:,} ({bids}次出价) | 领先: {leader}{rem_tag}" if (bids > 0 and leader) else f"起拍⭐{price:,} (暂无出价) | 发起: {seller}{rem_tag}"
                lines.append(f"{idx}. 🔨 {bid_status}\n   {t_icon} [{t_name}] {s_kind} · {ult} ({attr_str})")
            else:
                lines.append(f"{idx}. ⭐{price:,} | 卖家: {seller}\n   {t_icon} [{t_name}] {s_kind} · {ult} ({attr_str})")
        return "\n".join(lines)

    elif kind == "stone":
        title_part = f" · 强化石 ({query})" if query else " · 最新强化石"
        header = f"{mode_icon} 【osu!gacha {mode_name}{title_part}】"
        lines = [header, "━━━━━━━━━━━━━━━"]
        if query and guide:
            lines.extend(_format_guide_block(guide, total, type_desc="同类强化石", unit_label="颗"))
        if not items:
            lines.append(f"暂无{('拍卖中的' if is_auction else '在售')}强化石。")
            return "\n".join(lines)
        list_desc = (
            f"🏷️ 【当前正在拍卖 (前 {len(items)} 颗)】"
            if is_auction
            else (f"🏷️ 【当前最低在售 (共 {total:,} 颗，前 {len(items)} 颗)】" if query else f"在售总量：{total:,} 颗 (展示最新 {len(items)} 颗)")
        )
        lines.append(list_desc)
        for idx, item in enumerate(items, 1):
            price = item.get("price", 0)
            seller = item.get("seller", {}).get("username", "神秘卖家")
            st = item.get("stone", {}) or {}
            st_kind = STONE_KIND_NAMES.get(st.get("kind", ""), st.get("kind", "强化石"))
            stat_str = format_mod_main_stat({"stat": st.get("stat", ""), "value": st.get("value", 0)})

            if is_auction:
                auc = item.get("auction") or {}
                bids = auc.get("bids", 0)
                leader = auc.get("leader", {}).get("username") if auc.get("leader") else None
                rem_str = format_time_remaining(auc.get("endsAt"))
                rem_tag = f" ({rem_str})" if rem_str else ""
                bid_status = f"当前⭐{price:,} ({bids}次出价) | 领先: {leader}{rem_tag}" if (bids > 0 and leader) else f"起拍⭐{price:,} (暂无出价) | 发起: {seller}{rem_tag}"
                lines.append(f"{idx}. 🔨 {bid_status}\n   {st_kind} ({stat_str})")
            else:
                lines.append(f"{idx}. ⭐{price:,} | 卖家: {seller}\n   {st_kind} ({stat_str})")
        return "\n".join(lines)

    elif kind == "item":
        title_part = f" · 物品 ({query})" if query else " · 最新物品"
        header = f"{mode_icon} 【osu!gacha {mode_name}{title_part}】"
        if not items:
            return f"{header}\n━━━━━━━━━━━━━━━\n暂无{('拍卖中的' if is_auction else '在售')}物品。"
        lines = [
            header,
            "━━━━━━━━━━━━━━━",
            f"{('拍卖总量' if is_auction else '在售总量')}：{total:,} 组 (展示前 {len(items)} 组)",
            "━━━━━━━━━━━━━━━",
        ]
        for idx, item in enumerate(items, 1):
            price = item.get("price", 0)
            seller = item.get("seller", {}).get("username", "神秘卖家")
            item_info = item.get("item", {}) or {}
            item_name, qty = format_item_name(item_info)

            if is_auction:
                auc = item.get("auction") or {}
                bids = auc.get("bids", 0)
                leader = auc.get("leader", {}).get("username") if auc.get("leader") else None
                rem_str = format_time_remaining(auc.get("endsAt"))
                rem_tag = f" ({rem_str})" if rem_str else ""
                bid_status = f"当前⭐{price:,} ({bids}次出价) | 领先: {leader}{rem_tag}" if (bids > 0 and leader) else f"起拍⭐{price:,} (暂无出价) | 发起: {seller}{rem_tag}"
                lines.append(f"{idx}. 🔨 {bid_status}\n   {item_name} x{qty}")
            else:
                if qty > 1:
                    unit_price = price / qty
                    unit_str = f" (单价: ⭐{unit_price:,.1f})" if unit_price != int(unit_price) else f" (单价: ⭐{int(unit_price):,})"
                    lines.append(f"{idx}. ⭐{price:,} | 卖家: {seller} | {item_name} x{qty}{unit_str}")
                else:
                    lines.append(f"{idx}. ⭐{price:,} | 卖家: {seller} | {item_name}")
        return "\n".join(lines)

    # 默认卡片 (kind == "card")
    sig_tag = " (✍️签名卡)" if is_sig else ""
    title_part = f" · {query}{sig_tag}" if query else " · 最新卡片"
    header = f"{mode_icon} 【osu!gacha {mode_name}{title_part}】"

    lines = [header, "━━━━━━━━━━━━━━━"]

    # 若查询了具体卡牌且获取到了近 30 天官方成交指导价
    if query and guide:
        card_type_desc = "签名卡" if is_sig else "卡牌"
        lines.extend(_format_guide_block(guide, total, type_desc=card_type_desc, unit_label="张"))

    if not items:
        lines.append(f"暂无相关{('正在拍卖的' if is_auction else '在售')}{('签名卡' if is_sig else '卡片')}。")
        return "\n".join(lines)

    list_title = (
        f"🏷️ 【当前正在拍卖 (前 {len(items)} 件)】"
        if is_auction
        else (f"🏷️ 【当前在售挂单 (前 {len(items)} 件)】" if (query and guide) else f"在售总量：{total:,} 件 (展示最新 {len(items)} 件)")
    )
    lines.append(list_title)

    for idx, item in enumerate(items, 1):
        price = item.get("price", 0)
        seller = item.get("seller", {}).get("username", "神秘卖家")
        card = item.get("card", {}) or {}
        player = card.get("player", {}) or {}
        pname = player.get("username") or "未知选手"
        rarity = str(card.get("rarity", "common")).lower()
        r_cfg = RARITY_CONFIG.get(rarity, {"name": rarity.capitalize(), "icon": "▫️"})
        serial = card.get("serialNo")
        sn_str = f" #{serial}" if serial else ""

        sig = card.get("sig")
        sig_str = ""
        if sig and isinstance(sig, dict):
            tier = sig.get("tier", "").upper()
            sig_str = f" ✍️[{tier}]" if tier else " ✍️[签名]"

        if is_auction:
            auc = item.get("auction") or {}
            bids = auc.get("bids", 0)
            leader = auc.get("leader", {}).get("username") if auc.get("leader") else None
            rem_str = format_time_remaining(auc.get("endsAt"))
            rem_tag = f" ({rem_str})" if rem_str else ""
            bid_status = f"当前⭐{price:,} ({bids}次出价) | 领先: {leader}{rem_tag}" if (bids > 0 and leader) else f"起拍⭐{price:,} (暂无出价) | 发起: {seller}{rem_tag}"
            lines.append(f"{idx}. 🔨 {bid_status}\n   {r_cfg['icon']} {pname}{sig_str} [{r_cfg['name']}]{sn_str}")
        else:
            lines.append(f"{idx}. ⭐{price:,} | 卖家: {seller} | {r_cfg['icon']} {pname}{sig_str} [{r_cfg['name']}]{sn_str}")

    return "\n".join(lines)


def format_player_owners(owners: List[Dict[str, Any]], player_name: str) -> str:
    """
    格式化选手卡片持有者榜单
    """
    header = f"👑 【{player_name} · 卡片持有榜】"
    if not owners:
        return f"{header}\n━━━━━━━━━━━━━━━\n暂无持有者记录或该卡尚未被任何人抽取。"

    lines = [
        header,
        "━━━━━━━━━━━━━━━",
    ]
    for idx, o in enumerate(owners[:10], 1):
        uname = o.get("username", "神秘玩家")
        count = o.get("count", 0)
        best_r = str(o.get("bestRarity", "common")).lower()
        r_cfg = RARITY_CONFIG.get(best_r, {"name": best_r.capitalize(), "icon": "▫️"})
        lowest = o.get("lowest")
        sn_str = f"最低#{lowest}" if lowest else ""
        val = o.get("value", 0)

        details = [f"最高: {r_cfg['icon']}{r_cfg['name']}"]
        if sn_str:
            details.append(sn_str)
        if val:
            details.append(f"估值: ⭐{val:,}")

        lines.append(f"{idx}. {uname} · 拥有 {count} 张 ({' · '.join(details)})")

    return "\n".join(lines)


