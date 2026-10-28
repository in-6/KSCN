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
        handle_gacha_command(">gacha status", test_uid, gid=test_gid)

        # 开启挂机 3 小时
        handle_gacha_command(">gacha on 3", test_uid, gid=test_gid)

        # 再次查看状态（应为运行中）
        handle_gacha_command(">gacha status", test_uid, gid=test_gid)

        # 停止挂机
        handle_gacha_command(">gacha off", test_uid, gid=test_gid)

        # 清理测试用户
        storage.delete_user(str(test_uid))

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

