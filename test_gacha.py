#!/usr/bin/env python3
"""
osu!gacha 功能本地测试与调试脚本
用法:
  1. 运行基础功能自测（模拟指令、测试群聊@排版、Cookie解析等）:
     python3 test_gacha.py

  2. 真实在线连接测试（如果你手头有 osugacha.com 的真实 Cookie 或 cURL）:
     python3 test_gacha.py --verify "你复制的cURL或Cookie"
"""

import sys
import os
import argparse
from unittest.mock import patch

# 确保能导入当前目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from osugacha.client import OsugachaClient, extract_cookie_from_text
from osugacha.manager import handle_gacha_command
from osugacha.storage import storage


def mock_send_qq(url, json=None, **kwargs):
    """拦截发送到 OneBot 5700 的请求并在终端美观打印"""
    if "send_group_msg" in url:
        gid = json.get("group_id")
        msg = json.get("message")
        print(f"\n📨 [Bot 发送到群 {gid}]:\n{msg}")
    elif "send_private_msg" in url:
        uid = json.get("user_id")
        msg = json.get("message")
        print(f"\n📨 [Bot 私聊发送给 QQ:{uid}]:\n{msg}")
    
    # 模拟 OneBot 成功返回
    class MockResp:
        status_code = 200
        def json(self):
            return {"status": "ok", "retcode": 0}
    return MockResp()


def run_unit_tests():
    print("=" * 60)
    print("🚀 开始运行 osu!gacha 本地逻辑自测")
    print("=" * 60)

    # 1. 测试 cURL 解析器
    print("\n[测试 1] 校验 cURL 正则解析器...")
    sample_curl = (
        "curl 'https://osugacha.com/api/packs/inventory' \\\n"
        "  -H 'accept: */*' \\\n"
        "  -H 'cookie: osu_session=abc12345; lang=zh' \\\n"
        "  -H 'user-agent: Chrome/130.0.0.0'"
    )
    cookie = extract_cookie_from_text(sample_curl)
    print(f"提取结果: {cookie}")
    assert cookie == "osu_session=abc12345; lang=zh", "cURL 解析失败！"
    print("✅ cURL 解析测试通过！")

    # 使用 mock 劫持网络发送，测试机器人应答
    with patch("requests.post", side_effect=mock_send_qq):
        test_uid = 10086
        test_gid = 987654321

        # 2. 测试 >gacha help（群聊触发，验证是否包含新手教程与 @ 提示）
        print("\n[测试 2] 测试群聊触发 >gacha help（检查是否有 @群友）...")
        handle_gacha_command(">gacha help", test_uid, gid=test_gid)

        # 3. 测试群聊中误发 >gacha bind（验证安全防泄露拦截）
        print("\n[测试 3] 测试群聊中误发 >gacha bind（应被拦截并提示私聊）...")
        handle_gacha_command(">gacha bind curl 'https://...'", test_uid, gid=test_gid)

        # 4. 模拟写入测试用户并测试状态查看
        print("\n[测试 4] 模拟用户状态查看与挂机开关...")
        storage.save_user(str(test_uid), {
            "cookie": "mock_cookie_for_test",
            "osu_username": "TestPlayer",
            "osu_id": 9999,
            "is_running": False,
            "stop_timestamp": 0,
            "next_pull_time": 0,
            "min_interval": 360,
            "max_interval": 1080,
            "gid": test_gid,
            "stats": {"session_opened": 0, "total_opened": 5, "best_pull": "[Epic] btmc"}
        })

        # 查看状态
        handle_gacha_command(">gacha stats", test_uid, gid=test_gid)

        # 开启挂机 3 小时
        handle_gacha_command(">gacha on 3", test_uid, gid=test_gid)

        # 再次查看状态（应为运行中）
        handle_gacha_command(">gacha stats", test_uid, gid=test_gid)

        # 停止挂机
        handle_gacha_command(">gacha off", test_uid, gid=test_gid)

        # 清理测试用户
        storage.delete_user(str(test_uid))

    # 5. 测试 format_user_profile 与 format_pack_results 样式
    print("\n[测试 5] 测试 format_user_profile 与品质卡包排版...")
    from osugacha.formatter import format_user_profile, format_pack_results
    sample_profile = {
        "user": {
            "username": "noraneko",
            "countryCode": "cn",
            "osuUserId": 17945067,
            "guild": {"tag": "KRA", "name": "云母之家"}
        },
        "stats": {
            "level": {"level": 12},
            "team": {"power": 27360},
            "tower": {"floor": 64},
            "pvp": {"rating": 955, "wins": 1, "losses": 5},
            "collection": {"value": 26891, "cards": 3207},
            "dex": {"caught": 6171, "total": 92440}
        }
    }
    bot_stats = {
        "is_running": True,
        "status_str": "🟢 运行中 (剩余 1小时15分)",
        "next_in_str": "约 7 分钟后",
        "total_opened": 36,
        "best_pull": "🟡 [Legendary] Cookiezi",
    }
    # 模拟自己查看个人主页
    profile_self = format_user_profile(
        sample_profile,
        pack_info_str="🎁 2 / 10 包 (自然回复中) · 🟨 黄金卡包 x1",
        pity_info_str="🟡 17 / 80 包 (还差 63 包)",
        bot_stats=bot_stats
    )
    print("\n【查自己个人信息效果展示】:\n" + profile_self)
    assert "⚙️ 【自动开卡】" in profile_self
    assert "• 挂机状态：🟢 运行中 (剩余 1小时15分)" in profile_self
    assert "• 可用卡包：🎁 2 / 10 包 (自然回复中) · 🟨 黄金卡包 x1" in profile_self
    assert "• 传说保底：🟡 17 / 80 包 (还差 63 包)" in profile_self
    assert "• 资产：⭐ 26,891" in profile_self
    # 确保 挂机状态 -> 可用卡包 -> 传说保底
    assert profile_self.index("• 挂机状态：") < profile_self.index("• 可用卡包：") < profile_self.index("• 传说保底：")

    # 模拟查他人个人主页 (不含自动开卡部分)
    profile_other = format_user_profile(sample_profile)
    print("\n【查他人个人信息效果展示】:\n" + profile_other)
    assert "⚙️ 【自动开卡】" not in profile_other

    # 模拟开包排版 (带品质显示)
    sample_pulled = [
        {"player": {"username": "Cookiezi", "countryCode": "KR", "globalRank": 1, "cls": "dps"}, "rarity": "legendary"},
        {"player": {"username": "Mrekk", "countryCode": "AU", "globalRank": 1, "cls": "dps"}, "rarity": "rare"}
    ]
    pull_res = format_pack_results(sample_pulled, pack_name="🟨 黄金卡包")
    print("\n【开包结果效果展示】:\n" + pull_res)
    assert "📦 【osu!gacha 开包结果 · 🟨 黄金卡包】" in pull_res

    # 6. 测试自然日 00:00 跨天重置逻辑 (ensure_daily_stats)
    print("\n[测试 6] 测试自然日 0 点自动重置逻辑...")
    from osugacha.storage import ensure_daily_stats
    import datetime

    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    old_stats = {
        "date": yesterday_str,
        "today_opened": 42,
        "today_best": "🟡 [Legendary] Cookiezi",
        "today_best_level": 5,
        "total_opened": 100,
    }
    new_stats, reset = ensure_daily_stats(old_stats)
    assert reset is True, "跨天时应返回 reset=True"
    assert new_stats["today_opened"] == 0, "跨天后今日开包应清零"
    assert new_stats["today_best"] == "暂无", "跨天后今日最佳应重置为'暂无'"
    assert new_stats["date"] == datetime.date.today().isoformat(), "跨天后日期应更新为今天"

    # 同一天内重复调用不应被重置
    same_stats, reset2 = ensure_daily_stats(new_stats)
    assert reset2 is False, "同一天内调用不应重置"
    print("✅ 自然日 0 点重置逻辑测试全部通过！")

    # 7. 测试用户名特殊字符解析与候选名容错 (如 [SHK]T_T, [noraneko], 下划线/空格)
    print("\n[测试 7] 测试特殊字符用户名与 OneBot 实体反转义解析...")
    import html
    test_raw = "&#91;SHK&#93;T_T"
    unescaped = html.unescape(test_raw).strip()
    assert unescaped == "[SHK]T_T", "HTML实体应正确还原为带括号的用户名"

    # 测试候选名逻辑
    def get_candidates(raw):
        import html
        clean = html.unescape(raw).strip()
        if (clean.startswith('"') and clean.endswith('"')) or (clean.startswith("'") and clean.endswith("'")):
            clean = clean[1:-1].strip()
        cands = [clean]
        if (clean.startswith('[') and clean.endswith(']')) and len(clean) > 2:
            no_b = clean[1:-1].strip()
            if no_b not in cands: cands.append(no_b)
        for c in list(cands):
            if "_" in c:
                sp = c.replace("_", " ")
                if sp not in cands: cands.append(sp)
            if " " in c:
                un = c.replace(" ", "_")
                if un not in cands: cands.append(un)
        return cands

    c1 = get_candidates("&#91;SHK&#93;T_T")
    assert "[SHK]T_T" in c1, "[SHK]T_T 应被正确解析在候选列表中"
    assert "[SHK]T T" in c1, "应自动包含下划线替换为空格的容错候选"

    c2 = get_candidates("[noraneko]")
    assert "noraneko" in c2, "外层包裹中括号时应自动剥除生成候选名"

    c3 = get_candidates("el_pato_leo")
    assert "el pato leo" in c3, "下划线用户名应包含空格版本候选"

    print("✅ 特殊字符解析与候选名生成测试全部通过！")

    print("\n" + "=" * 60)
    print("🎉 所有本地单元与排版测试全部通过！")
    print("=" * 60)


def run_live_verify(raw_credential: str):
    print("=" * 60)
    print("🌐 开始在线校验真实凭据并测试连接 osugacha.com")
    print("=" * 60)

    cookie = extract_cookie_from_text(raw_credential)
    if not cookie:
        print("❌ 无法从输入的内容中提取出有效 Cookie！")
        return

    print(f"提取出的 Cookie: {cookie[:35]}... (长度: {len(cookie)})")
    print("正在请求 https://osugacha.com/api/auth/me 进行身份校验...")

    client = OsugachaClient(cookie)
    ok, user_info, msg = client.verify()

    if not ok or not user_info:
        print(f"❌ 校验失败: {msg}")
        return

    username = user_info.get("username") or user_info.get("name")
    osu_id = user_info.get("osuUserId") or user_info.get("id")
    print(f"✅ 校验成功！当前登录账号: [{username}] (ID: {osu_id})")

    print("\n正在查询卡包背包 (GET /api/packs/inventory)...")
    inv_ok, inv_data, inv_msg = client.get_inventory()
    if inv_ok:
        packs = inv_data if isinstance(inv_data, list) else inv_data.get("packs", inv_data.get("items", []))
        print(f"✅ 成功查询到背包！当前可用卡包数量: {len(packs)} 个")
        for i, p in enumerate(packs[:3]):
            print(f"  • 卡包 #{i+1}: ID={p.get('id')} 类型={p.get('type', '普通卡包')}")
    else:
        print(f"⚠️ 查询卡包返回: {inv_msg}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="osu!gacha 本地测试脚本")
    parser.add_argument("--verify", type=str, help="传入真实的 cURL 或 Cookie 进行在线联调")
    args = parser.parse_args()

    if args.verify:
        run_live_verify(args.verify)
    else:
        run_unit_tests()

