import re
import time
import random
import requests
from typing import Optional, Dict, Any, Tuple

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
CLIENT_BUILD = "1793166449902"
BASE_URL = "https://osugacha.com/api"


def extract_cookie_from_text(raw_text: str) -> Optional[str]:
    """
    智能解析用户私聊发来的各种内容：
    1. 浏览器 Copy as cURL 的整段命令 (支持 bash/cmd/powershell 格式)
    2. 复制的 Request Headers
    3. 直接发送的 Cookie 字符串
    """
    if not raw_text:
        return None

    raw_text = raw_text.strip()

    # 1. 匹配 cURL 中的 -H 'cookie: ...' 或 -H "cookie: ..."
    curl_match = re.search(r"-H\s+['\"]cookie:\s*([^'\"]+)['\"]", raw_text, re.IGNORECASE)
    if curl_match:
        return curl_match.group(1).strip()

    # 2. 匹配 cURL 中的 -b 或 --cookie
    b_match = re.search(r"(?:-b|--cookie)\s+['\"]([^'\"]+)['\"]", raw_text, re.IGNORECASE)
    if b_match:
        return b_match.group(1).strip()

    # 3. 匹配原始请求头 "cookie: ..."
    header_match = re.search(r"^cookie:\s*(.+)$", raw_text, re.IGNORECASE | re.MULTILINE)
    if header_match:
        return header_match.group(1).strip()

    # 4. 如果内容本身包含 osugacha 常见凭据 (例如 session 或 osu_oauth)
    if "=" in raw_text and ("session" in raw_text or "osu" in raw_text or "connect.sid" in raw_text):
        # 截掉可能混入的无关前缀
        clean_text = raw_text.splitlines()[0]
        return clean_text.strip()

    # 兜底：如果就是一条 key=value 格式的纯字符串
    if "=" in raw_text and len(raw_text) > 15:
        return raw_text.strip()

    return None


class OsugachaClient:
    def __init__(self, cookie: str):
        self.cookie = cookie.strip()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
            "x-client-build": CLIENT_BUILD,
            "Origin": "https://osugacha.com",
            "Referer": "https://osugacha.com/packs",
            "Cookie": self.cookie,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

    def _build_fake_telemetry(self) -> Dict[str, Any]:
        """
        伪造完美的人类开包行为探针 (对应前端逆向出的 Af() 函数)
        """
        return {
            "input": {
                "via": "mouse",
                "trusted": True,
                "hidden": False,
                "x": random.randint(450, 1050),
                "y": random.randint(350, 700),
                "moves": random.randint(22, 68),
            }
        }

    def verify(self) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        测试 Cookie 是否有效并获取当前登录用户信息
        返回: (是否成功, 用户信息字典, 提示消息)
        """
        url = f"{BASE_URL}/auth/me"
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                user = data.get("user")
                if user:
                    return True, user, "验证成功"
                return False, None, "未登录状态 (user 为空)"
            elif resp.status_code == 401 or resp.status_code == 403:
                return False, None, f"Cookie 已失效 (HTTP {resp.status_code})"
            else:
                return False, None, f"接口返回异常 HTTP {resp.status_code}"
        except Exception as e:
            return False, None, f"网络请求失败: {str(e)}"

    def get_inventory(self) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        获取玩家当前拥有的卡包信息
        """
        url = f"{BASE_URL}/packs/inventory"
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                return True, resp.json(), "获取成功"
            return False, None, f"获取卡包失败 HTTP {resp.status_code}"
        except Exception as e:
            return False, None, f"网络错误: {str(e)}"

    def open_pack(self, pack_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        开包请求
        返回: (是否成功, 出货数据, 消息或错误码)
        注意: 如果遇到 challenge_required, 消息将返回 'challenge_required'
        """
        url = f"{BASE_URL}/packs/inventory/{pack_id}/open"
        payload = self._build_fake_telemetry()

        try:
            resp = self.session.post(url, json=payload, timeout=15)
            data = resp.json() if resp.content else {}

            if resp.status_code == 200:
                return True, data, "开包成功"

            # 检查风控挑战拦截
            err = data.get("error", {})
            err_code = err.get("code")
            err_msg = err.get("message", resp.statusText if hasattr(resp, 'statusText') else "")

            if err_code == "challenge_required" or resp.status_code == 403:
                return False, None, "challenge_required"

            return False, data, f"开包失败 [{err_code}]: {err_msg}"
        except Exception as e:
            return False, None, f"网络异常: {str(e)}"

    @staticmethod
    def fetch_public_profile(username: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        公开接口：查询任意玩家的公开主页档案 (无需 Cookie 登录态)
        """
        import urllib.parse
        url = f"{BASE_URL}/users/{urllib.parse.quote(username)}/profile"
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "x-client-build": CLIENT_BUILD,
            "Accept": "application/json, text/plain, */*",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return True, resp.json(), "获取成功"
            elif resp.status_code == 404:
                return False, None, "未找到该玩家"
            return False, None, f"请求失败 HTTP {resp.status_code}"
        except Exception as e:
            return False, None, f"网络异常: {str(e)}"


