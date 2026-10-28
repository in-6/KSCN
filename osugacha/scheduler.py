import time
import random
import threading
import requests
from typing import Dict, Any, Optional

from .client import OsugachaClient
from .storage import storage
from .formatter import parse_card_info, format_card_line, RARITY_CONFIG

ONEBOT_API_URL = "http://127.0.0.1:5700"

# 高稀有度列表，抽到将主动推送 QQ 提醒
HIGHLIGHT_RARITIES = {
    "epic": "Epic",
    "legendary": "Legendary",
    "mythic": "Mythic",
    "divine": "Divine",
    "signature": "Signature",
}


def send_qq_msg(uid: str, message: str, gid: Optional[str] = None):
    """
    通过 OneBot / go-cqhttp 发送 QQ 消息
    在群聊中会自动 @ 该用户，并换行展示内容，防止群聊信息混淆
    """
    try:
        if gid:
            # 群聊发送并 @ 该用户 (加换行排版更清晰)
            url = f"{ONEBOT_API_URL}/send_group_msg"
            payload = {
                "group_id": int(gid),
                "message": f"[CQ:at,qq={uid}]\n{message}",
            }
        else:
            # 私聊发送
            url = f"{ONEBOT_API_URL}/send_private_msg"
            payload = {
                "user_id": int(uid),
                "message": message,
            }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[AutoGacha] 发送 QQ 消息失败: {e}")


class GachaScheduler:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="OsugachaScheduler")
        self._thread.start()
        print("[AutoGacha] 拟人化开包调度器后台线程已启动")

    def _loop(self):
        while self._running:
            try:
                self._tick()
            except Exception as e:
                print(f"[AutoGacha] 调度异常: {e}")
            time.sleep(10)

    def _tick(self):
        now = time.time()
        users = storage.get_all_users()

        for uid, user in users.items():
            if not user.get("is_running", False):
                continue

            gid = user.get("gid")
            cookie = user.get("cookie", "")
            stop_time = user.get("stop_timestamp", 0)
            next_time = user.get("next_pull_time", 0)
            stats = user.get("stats", {})

            # 1. 检查是否到达预设的停止时间 (防通宵挂机保护)
            if now >= stop_time:
                storage.update_user_fields(uid, is_running=False)
                session_opened = stats.get("session_opened", 0)
                send_qq_msg(
                    uid,
                    f"🔴 [AutoGacha] 挂机已到达设定时间，已自动停止。\n本次挂机共开包: {session_opened} 个",
                    gid=gid,
                )
                continue

            # 2. 检查是否到达下一次开包时间
            if now < next_time:
                continue

            # 3. 执行开包
            self._do_open_pack(uid, user, cookie, gid)

    def _do_open_pack(self, uid: str, user: Dict[str, Any], cookie: str, gid: Optional[str]):
        client = OsugachaClient(cookie)
        now = time.time()
        min_sec = user.get("min_interval", 360)
        max_sec = user.get("max_interval", 1080)
        stats = user.get("stats", {"session_opened": 0, "total_opened": 0, "best_pull": "无"})

        # 先查询当前是否有可用卡包
        ok, inv_data, msg = client.get_inventory()
        if not ok or not inv_data:
            # 如果请求失败且是鉴权失效
            if "失效" in msg or "401" in msg or "403" in msg:
                storage.update_user_fields(uid, is_running=False)
                send_qq_msg(uid, "❌ [AutoGacha] 登录态已失效，自动开包已暂停，请重新绑定凭据。", gid=gid)
                return

            # 其他网络波动，稍等 3 分钟后重试
            next_time = now + random.randint(150, 240)
            storage.update_user_fields(uid, next_pull_time=next_time)
            return

        # 解析背包中的卡包列表
        # 兼容数组或字典包裹
        packs = inv_data if isinstance(inv_data, list) else inv_data.get("packs", inv_data.get("items", []))
        if not packs:
            # 暂无可开卡包，等待 4~6 分钟自然回复
            next_time = now + random.randint(240, 360)
            storage.update_user_fields(uid, next_pull_time=next_time)
            return

        # 遍历开完当前背包里积攒的所有卡包
        opened_this_batch = 0
        rare_findings = []

        for p in packs:
            pack_id = p.get("id") or p.get("inventoryId") or p.get("packId")
            if not pack_id:
                continue

            # 发起开包
            open_ok, open_data, open_msg = client.open_pack(pack_id)

            # 触发了风控安全拦截 (熔断机制)
            if open_msg == "challenge_required":
                storage.update_user_fields(uid, is_running=False)
                send_qq_msg(
                    uid,
                    "⚠️ [AutoGacha 紧急告警] 检测到账号触发了人机验证挑战 (challenge_required)！\n"
                    "为保护账号安全，自动开包已【紧急关停】！\n"
                    "请前往电脑浏览器手动登录游戏开一包以解除验证。",
                    gid=gid,
                )
                return

            if not open_ok:
                print(f"[AutoGacha] 用户 {uid} 开包异常: {open_msg}")
                break

            opened_this_batch += 1

            # 解析抽出的卡片列表
            pulled_cards = (
                open_data.get("cards", [])
                if isinstance(open_data, dict)
                else (open_data if isinstance(open_data, list) else [])
            )

            for card in pulled_cards:
                info = parse_card_info(card)
                if info["rarity_key"] in HIGHLIGHT_RARITIES:
                    rare_findings.append(info)
                    # 记录最高出货
                    stats["best_pull"] = f"{info['rarity_icon']} [{info['rarity_name']}] {info['username']}"

            # 关键拟人化安全间隔：连开多包时，模拟真实玩家看牌停顿 1.8 ~ 3.5 秒，绝不秒点下一包
            time.sleep(random.uniform(1.8, 3.5))

        # 开包成功，更新统计
        stats["session_opened"] = stats.get("session_opened", 0) + opened_this_batch
        stats["total_opened"] = stats.get("total_opened", 0) + opened_this_batch

        # 下一次大轮询延时：随机 6 ~ 18 分钟 (拟人化波动)
        next_delay = random.randint(min_sec, max_sec)
        next_time = now + next_delay

        storage.update_user_fields(uid, stats=stats, next_pull_time=next_time)

        # 如果抽到稀有卡，立即发 QQ 提醒 (纯文本干净排版)
        for info in rare_findings:
            line = format_card_line(info)
            notice = (
                f"🎉 【osu!gacha 欧气爆发】\n"
                f"恭喜抽到稀有卡片：\n"
                f"{line}"
            )
            send_qq_msg(uid, notice, gid=gid)


scheduler = GachaScheduler()

