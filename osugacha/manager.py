import html
from typing import Optional

from .client import OsugachaClient
from .scheduler import send_qq_msg
from .formatter import (
    format_user_profile,
    format_market_listings,
    format_item_book_summary,
    format_item_book_detail,
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
    elif subcmd in ["itemname", "itemnames", "items", "物品名", "物品表"]:
        show_item_names(uid_str, gid_str)
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
        "【osu!gacha 助手使用指南】\n"
        "━━━━━━━━━━━━━━━\n"
        ">gacha stats [玩家名] : 查询公开个人信息 (含战力/爬塔/深渊/藏卡)\n"
        ">gacha mkt [-c] [卡牌名] [--sig] [--auc] : 查询卡片挂单/拍卖与成交中位数\n"
        ">gacha mkt -m [Mod类型] [1-5星] [--auc] : 查 Mod 行情 (如 -m hr 5)\n"
        ">gacha mkt -i [物品名] [--auc] : 查询物品挂单信息 (如 -i fuel / replay3)\n"
        ">gacha mkt -d [形态] [1-5级] [--auc] : 查询外设行情 (如 -d 4 / -d tablet 5)\n"
        ">gacha mkt -st [sharp|gem] [--auc] : 查询强化石行情 (锐石/模组石)\n"
        ">gacha itemname : 显示物品名称表，供查询市场时使用\n"
        ">gacha owners [选手名] : 查看该选手卡片的最多持有者榜单\n"
        ">gacha help : 查看本帮助说明\n"
        "━━━━━━━━━━━━━━━\n"
        "🔴 友情提示：osu!gacha 1.0 版本已全面升级反作弊监测，严禁使用任何连点器、外挂或自动化脚本。自动挂机开包功能已永久下线。"
    )
    send_qq_msg(uid, text, gid=gid)


def show_item_names(uid: str, gid: Optional[str]):
    """
    显示物品名称与查询码对照表，供 >gacha mkt -i 查询时使用
    """
    text = (
        "📋 【osu!gacha 物品名称对照表】\n"
        "━━━━━━━━━━━━━━━\n"
        "🔹 【消耗品】\n"
        "• fuel ：⛽ 燃料 (别名: 燃料/油)\n"
        "• key ：🗝️ 卡池钥匙 (别名: banner_key/钥匙)\n"
        "• fragment ：🧩 Mod碎片 (别名: 碎片)\n"
        "🔹 【回放】\n"
        "• replay1 ：📼 铜回放 (1级)\n"
        "• replay2 ：📼 银回放 (2级)\n"
        "• replay3 ：📼 金回放 (3级)\n"
        "🔹 【奖杯】\n"
        "• trophy1 ：🏆 金奖杯 (别名: boss)\n"
        "• trophy2 ：🏆 白金奖杯 (别名: platinum)\n"
        "• trophy3 ：💎 钻石奖杯 (别名: diamond)\n"
        "• trophy4 ：🟢 翡翠奖杯 (别名: emerald)\n"
        "🔹 【职业徽章 (I ~ IV 级)】\n"
        "• dps1 ~ dps4 ：⚔️ 输出 I~IV 徽章\n"
        "• tank1 ~ tank4 ：🛡️ 坦克 I~IV 徽章\n"
        "• support1 ~ support4 ：💚 辅助 I~IV 徽章\n"
        "• cc1 ~ cc4 ：🌀 控制 I~IV 徽章\n"
        "🔹 【外设形态】\n"
        "• tablet ：🖊️ 数位板 (别名: 板/数位板)\n"
        "• mouse ：🖱️ 鼠标 (别名: 鼠/鼠标)\n"
        "• keyboard ：⌨️ 键盘 (别名: kb/键/键盘)\n"
        "• touchscreen ：📱 触屏 (别名: touch/触屏/触摸屏)\n"
        "• editor ：🎛️ 编辑器 (别名: 编辑/编辑器)\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 直接发送 `>gacha mkt -i` 可查看全服核心物品实时信息。"
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


ITEM_ALIASES = {
    "fuel": "fuel", "燃料": "fuel", "油": "fuel", "电池": "fuel",
    "key": "banner_key", "banner_key": "banner_key", "bannerkey": "banner_key", "钥匙": "banner_key", "卡池钥匙": "banner_key",
    "replay1": "replay_1", "replay_1": "replay_1", "铜回放": "replay_1", "回放1": "replay_1",
    "replay2": "replay_2", "replay_2": "replay_2", "银回放": "replay_2", "回放2": "replay_2",
    "replay3": "replay_3", "replay_3": "replay_3", "金回放": "replay_3", "回放3": "replay_3",
    "trophy1": "boss_trophy", "trophy_1": "boss_trophy", "奖杯1": "boss_trophy", "trophy": "boss_trophy", "boss_trophy": "boss_trophy", "金奖杯": "boss_trophy", "boss奖杯": "boss_trophy", "杯子": "boss_trophy",
    "trophy2": "platinum_trophy", "trophy_2": "platinum_trophy", "奖杯2": "platinum_trophy", "platinum": "platinum_trophy", "platinum_trophy": "platinum_trophy", "白金": "platinum_trophy", "白金奖杯": "platinum_trophy", "银奖杯": "platinum_trophy",
    "trophy3": "diamond_trophy", "trophy_3": "diamond_trophy", "奖杯3": "diamond_trophy", "diamond": "diamond_trophy", "diamond_trophy": "diamond_trophy", "钻石": "diamond_trophy", "钻石奖杯": "diamond_trophy",
    "trophy4": "emerald_trophy", "trophy_4": "emerald_trophy", "奖杯4": "emerald_trophy", "emerald": "emerald_trophy", "emerald_trophy": "emerald_trophy", "翡翠": "emerald_trophy", "翡翠奖杯": "emerald_trophy",
    "fragment": "mod_fragment", "mod_fragment": "mod_fragment", "碎片": "mod_fragment", "mod碎片": "mod_fragment",
}
for _cls, _cn in [("tank", "坦克"), ("dps", "输出"), ("support", "辅助"), ("cc", "控制")]:
    for _lvl in ["1", "2", "3", "4"]:
        _iid = f"insignia_{_cls}_{_lvl}"
        ITEM_ALIASES[_iid] = _iid
        ITEM_ALIASES[f"{_cls}{_lvl}"] = _iid
        ITEM_ALIASES[f"{_cls}_{_lvl}"] = _iid
        ITEM_ALIASES[f"{_cn}{_lvl}"] = _iid

VALID_MOD_TYPES = {"hr", "dt", "hd", "ht", "ez", "so", "fl", "nc", "sd", "pf", "nf", "rx", "ap"}

DEVICE_TIER_MAP = {
    "1": ("11", "1级"), "1级": ("11", "1级"), "lv1": ("11", "1级"), "11": ("11", "1级"),
    "2": ("21", "2级"), "2级": ("21", "2级"), "lv2": ("21", "2级"), "21": ("21", "2级"),
    "3": ("31,22", "3级"), "3级": ("31,22", "3级"), "lv3": ("31,22", "3级"), "22": ("22", "3级(II/II)"), "31": ("31", "3级(III/I)"),
    "4": ("32", "4级"), "4级": ("32", "4级"), "lv4": ("32", "4级"), "32": ("32", "4级"),
    "5": ("33", "5级"), "5级": ("33", "5级"), "lv5": ("33", "5级"), "33": ("33", "5级"),
}

DEVICE_KIND_ALIASES = {
    "tablet": "tablet", "板": "tablet", "数位板": "tablet",
    "mouse": "mouse", "鼠": "mouse", "鼠标": "mouse",
    "keyboard": "keyboard", "kb": "keyboard", "键": "keyboard", "键盘": "keyboard",
    "touchscreen": "touchscreen", "touch": "touchscreen", "触屏": "touchscreen", "触摸屏": "touchscreen",
    "editor": "editor", "编辑": "editor", "编辑器": "editor",
}

STONE_KIND_ALIASES = {
    "sharp": "sharp", "锐石": "sharp",
    "gem": "gem", "宝石": "gem", "模组石": "gem",
}


def handle_market(uid: str, gid: Optional[str], arg: Optional[str] = None):
    """
    处理 >gacha mkt 市场行情查询
    - >gacha mkt [-c] [卡片名] [--sig] [--auc]
    - >gacha mkt -m [Mod类型] [1-5星] [--auc]
    - >gacha mkt -i [物品名] [--auc]
    - >gacha mkt -d [形态/大招] [1-5级] [--auc]
    - >gacha mkt -st [sharp|gem] [--auc]
    """
    kind = "card"
    is_sig = False
    is_auction = False
    tokens = arg.strip().split() if arg else []

    filtered_tokens = []
    for tok in tokens:
        low = tok.lower()
        if low in ["--sig", "-sig", "--signature", "-signature"]:
            is_sig = True
        elif low in ["--auc", "-auc", "--auction", "-auction", "-拍卖", "拍卖"]:
            is_auction = True
        else:
            filtered_tokens.append(tok)

    sub_tokens = []
    if filtered_tokens:
        first = filtered_tokens[0].lower()
        if first in ["-m", "/m", "-mod", "mod"]:
            kind = "mod"
            sub_tokens = filtered_tokens[1:]
        elif first in ["-i", "/i", "-item", "item", "-物品", "物品"]:
            kind = "item"
            sub_tokens = filtered_tokens[1:]
        elif first in ["-d", "/d", "-device", "device", "-s", "/s", "-setup", "setup", "-外设", "外设"]:
            kind = "setup"
            sub_tokens = filtered_tokens[1:]
        elif first in ["-st", "/st", "-stone", "stone", "-石", "-强化石", "强化石"]:
            kind = "stone"
            sub_tokens = filtered_tokens[1:]
        elif first in ["-c", "/c", "-card", "card", "-卡片", "卡片"]:
            kind = "card"
            sub_tokens = filtered_tokens[1:]
        else:
            kind = "card"
            sub_tokens = filtered_tokens

    query = " ".join(sub_tokens).strip() if sub_tokens else None

    # --sig 必须配合指定卡牌名称查询
    if is_sig and (kind != "card" or not query):
        send_qq_msg(
            uid,
            "❌ 请输入要查询签名卡的选手名称！\n示例：`>gacha mkt Camo --sig`",
            gid=gid,
        )
        return

    mode = "auction" if is_auction else None

    # 1. 物品 (Item) —— 非拍卖模式下使用官方交易所实时盘口 API
    if kind == "item":
        if not is_auction:
            if not query:
                ok, book_data, msg = OsugachaClient.get_market_book()
                if not ok or not book_data:
                    send_qq_msg(uid, f"❌ 获取物品实时盘口失败：{msg}", gid=gid)
                    return
                send_qq_msg(uid, format_item_book_summary(book_data), gid=gid)
                return

            key_clean = query.lower().replace(" ", "")
            resolved_id = ITEM_ALIASES.get(key_clean) or ITEM_ALIASES.get(query.lower())
            if not resolved_id:
                send_qq_msg(
                    uid,
                    f"❌ 未识别的物品名 [{query}]。\n"
                    "💡 支持：`fuel`(燃料)、`replay1`~`3`(回放)、`trophy1`~`4`(奖杯)、"
                    "`dps1`~`4`/`tank1`~`4`/`support1`~`4`/`cc1`~`4`(徽章)、`key`(钥匙)、`fragment`(碎片)。",
                    gid=gid,
                )
                return

            ok_b, book_detail, msg_b = OsugachaClient.get_item_book(resolved_id)
            if not ok_b or not book_detail:
                send_qq_msg(uid, f"❌ 获取物品盘口详情失败：{msg_b}", gid=gid)
                return
            ok_d, days_data, _ = OsugachaClient.get_item_book_days(resolved_id)
            reply = format_item_book_detail(resolved_id, book_detail, days_data if ok_d else None)
            send_qq_msg(uid, reply, gid=gid)
            return
        else:
            resolved_id = None
            if query:
                key_clean = query.lower().replace(" ", "")
                resolved_id = ITEM_ALIASES.get(key_clean) or ITEM_ALIASES.get(query.lower())
                if not resolved_id:
                    send_qq_msg(uid, f"❌ 未识别的物品名 [{query}]，无法筛选拍卖。", gid=gid)
                    return
            ok, data, msg = OsugachaClient.search_market(kind="item", item_id=resolved_id, mode="auction", limit=8)
            if not ok or not data:
                send_qq_msg(uid, f"❌ 查询物品拍卖失败：{msg}", gid=gid)
                return
            send_qq_msg(uid, format_market_listings(data, kind="item", query=resolved_id, is_auction=True), gid=gid)
            return

    # 2. Mod —— 支持 Mod 类型 (hr/dt/...) 与星级 (1-5)，不做词条筛选
    if kind == "mod":
        mod_type = None
        mod_rarity = None
        label_parts = []
        for tok in sub_tokens:
            low = tok.lower().replace("星", "").replace("*", "")
            if low in VALID_MOD_TYPES:
                mod_type = low
                label_parts.append(low.upper())
            elif low in ["1", "2", "3", "4", "5"]:
                mod_rarity = int(low)
                label_parts.append(f"{mod_rarity}星")
            else:
                send_qq_msg(
                    uid,
                    f"❌ 无法识别的 Mod 参数 [{tok}]。\n"
                    "💡 示例：`>gacha mkt -m hr 5` 或 `>gacha mkt -m dt` (支持 hr/dt/hd/ht/ez/so/fl/nc/sd/pf + 1~5星)",
                    gid=gid,
                )
                return

        has_filter = bool(mod_type or mod_rarity)
        sort_by = ("ending" if is_auction else "price_asc") if has_filter else None
        ok, data, msg = OsugachaClient.search_market(
            kind="mod", mod_type=mod_type, mod_rarity=mod_rarity, mode=mode, sort=sort_by, limit=8
        )
        if not ok or not data:
            send_qq_msg(uid, f"❌ 查询 Mod 行情失败：{msg}", gid=gid)
            return

        guide_data = None
        items = data.get("items", [])
        if has_filter and items:
            first_mod_id = (items[0].get("mod") or {}).get("id")
            if first_mod_id:
                ok_g, g_data, _ = OsugachaClient.get_market_guide(mod_id=first_mod_id)
                if ok_g and g_data:
                    guide_data = g_data

        label = " ".join(label_parts) if label_parts else None
        send_qq_msg(
            uid,
            format_market_listings(data, kind="mod", query=label, guide=guide_data, is_auction=is_auction),
            gid=gid,
        )
        return

    # 3. 外设 Device (setup) —— 只按形态与品阶 1-5 筛选
    if kind == "setup":
        setup_kind = None
        setup_grades = None
        label_parts = []
        for tok in sub_tokens:
            low = tok.lower()
            if low in DEVICE_TIER_MAP:
                setup_grades, tier_label = DEVICE_TIER_MAP[low]
                label_parts.append(tier_label)
            elif low in DEVICE_KIND_ALIASES:
                setup_kind = DEVICE_KIND_ALIASES[low]
                label_parts.append(setup_kind)
            else:
                send_qq_msg(
                    uid,
                    f"❌ 无法识别的外设参数 [{tok}]。\n"
                    "💡 示例：`>gacha mkt -d 4` / `>gacha mkt -d 5` / `>gacha mkt -d tablet 4`\n"
                    "支持品阶 `1`~`5`，形态 `tablet/mouse/keyboard/touchscreen/editor`。",
                    gid=gid,
                )
                return

        has_filter = bool(setup_kind or setup_grades)
        sort_by = ("ending" if is_auction else "price_asc") if has_filter else None
        ok, data, msg = OsugachaClient.search_market(
            kind="setup",
            setup_kind=setup_kind,
            setup_grades=setup_grades,
            mode=mode,
            sort=sort_by,
            limit=8,
        )
        if not ok or not data:
            send_qq_msg(uid, f"❌ 查询外设行情失败：{msg}", gid=gid)
            return

        guide_data = None
        items = data.get("items", [])
        if has_filter and items:
            first_setup_id = (items[0].get("setup") or {}).get("id")
            if first_setup_id:
                ok_g, g_data, _ = OsugachaClient.get_market_guide(setup_id=first_setup_id)
                if ok_g and g_data:
                    guide_data = g_data

        label = " ".join(label_parts) if label_parts else None
        send_qq_msg(
            uid,
            format_market_listings(data, kind="setup", query=label, guide=guide_data, is_auction=is_auction),
            gid=gid,
        )
        return

    # 4. 强化石 Stone —— sharp / gem
    if kind == "stone":
        stone_kind = None
        label = None
        if sub_tokens:
            low = sub_tokens[0].lower()
            stone_kind = STONE_KIND_ALIASES.get(low)
            if not stone_kind:
                send_qq_msg(
                    uid,
                    f"❌ 无法识别的强化石类型 [{sub_tokens[0]}]。\n"
                    "💡 示例：`>gacha mkt -st sharp` (锐石) 或 `>gacha mkt -st gem` (宝石)",
                    gid=gid,
                )
                return
            label = "Sharp 锐石" if stone_kind == "sharp" else "Gem 宝石"

        sort_by = ("ending" if is_auction else "price_asc") if stone_kind else None
        ok, data, msg = OsugachaClient.search_market(
            kind="stone", stone_kind=stone_kind, mode=mode, sort=sort_by, limit=8
        )
        if not ok or not data:
            send_qq_msg(uid, f"❌ 查询强化石行情失败：{msg}", gid=gid)
            return

        guide_data = None
        items = data.get("items", [])
        if stone_kind and items:
            first_stone_id = (items[0].get("stone") or {}).get("id")
            if first_stone_id:
                ok_g, g_data, _ = OsugachaClient.get_market_guide(stone_id=first_stone_id)
                if ok_g and g_data:
                    guide_data = g_data

        send_qq_msg(
            uid,
            format_market_listings(data, kind="stone", query=label, guide=guide_data, is_auction=is_auction),
            gid=gid,
        )
        return

    # 5. 默认：卡片 (Card)
    rarity = "signature" if is_sig else None
    guide_data = None
    if query:
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
        ok, data, msg = OsugachaClient.search_market(kind="card", rarity=rarity, mode=mode, limit=8)
        if not ok or not data:
            action_desc = "拍卖" if is_auction else "市场挂单"
            send_qq_msg(uid, f"❌ 查询{action_desc}失败：{msg}", gid=gid)
            return

        reply = format_market_listings(data, kind="card", is_sig=is_sig, is_auction=is_auction)
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


