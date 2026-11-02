import requests
from typing import Optional

ONEBOT_API_URL = "http://127.0.0.1:5700"

HIGHLIGHT_RARITIES = {
    "mythic": "Mythic",
    "divine": "Divine",
}


def send_qq_msg(uid: str, message: str, gid: Optional[str] = None):
    """
    通过 OneBot / go-cqhttp 发送 QQ 消息
    在群聊中会自动 @ 该用户，并换行展示内容，防止群聊信息混淆
    """
    try:
        if gid:
            url = f"{ONEBOT_API_URL}/send_group_msg"
            payload = {
                "group_id": int(gid),
                "message": f"[CQ:at,qq={uid}]\n{message}",
            }
        else:
            url = f"{ONEBOT_API_URL}/send_private_msg"
            payload = {
                "user_id": int(uid),
                "message": message,
            }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[AutoGacha] 发送 QQ 消息失败: {e}")


class GachaScheduler:
    """
    原定时自动开包调度器。
    已全面下线后台自动开包逻辑，保留此类接口以保证项目生命周期调用的向下兼容。
    """
    def __init__(self):
        pass

    def start(self):
        print("[AutoGacha] 自动挂机开包已全面下线，调度器保持静默。")


scheduler = GachaScheduler()
