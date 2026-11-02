import re
import os
import json
import time
import random
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import requests

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
CLIENT_BUILD = "1793582738377"
BASE_URL = "https://osugacha.com/api"


def get_api_key() -> Optional[str]:
    """
    获取 osugacha 官方 API Key (只读查询权限):
    1. 优先读取环境变量 GACHA_API_KEY / OSUGACHA_API_KEY
    2. 读取项目根目录或当前工作目录下的 kscnconfig.json (键名: gacha_apikey 或 osugacha_api_key)
    3. 读取 config.json
    """
    env_key = os.environ.get("GACHA_API_KEY") or os.environ.get("OSUGACHA_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    search_dirs = [
        Path.cwd(),
        Path(__file__).resolve().parent,
        Path(__file__).resolve().parent.parent,
    ]
    for d in search_dirs:
        for fname in ["kscnconfig.json", "config.json"]:
            fpath = d / fname
            if fpath.is_file():
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        key = cfg.get("gacha_apikey") or cfg.get("osugacha_api_key")
                        if key and isinstance(key, str) and key.strip():
                            return key.strip()
                except Exception:
                    pass
    return None


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
    def _get_api_headers(api_key: Optional[str] = None) -> Dict[str, str]:
        """构造带有官方 API Key 的只读请求头"""
        if not api_key:
            api_key = get_api_key()
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "x-client-build": CLIENT_BUILD,
            "Accept": "application/json, text/plain, */*",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    @staticmethod
    def fetch_public_profile(username: str, api_key: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        公开接口：查询任意玩家的公开主页档案 (使用官方 API Key 或只读权限)
        支持特殊字符、OneBot HTML实体反转义、空格/下划线互通容错与外层语法中括号容错
        """
        import html
        import urllib.parse

        # 1. HTML 实体反转义 (NapCat 会把 [ 转为 &#91;，] 转为 &#93;，& 转为 &amp;)
        raw_name = html.unescape(username).strip()
        # 去除外层可能包裹的引号（如 "Aether Realm" 或 'Silence_Suzuka_'）
        if (raw_name.startswith('"') and raw_name.endswith('"')) or (raw_name.startswith("'") and raw_name.endswith("'")):
            raw_name = raw_name[1:-1].strip()

        if not raw_name:
            return False, None, "用户名不能为空"

        # 2. 生成多级候选名称
        candidates = [raw_name]

        # 容错：如果用户被指令说明误导，整体用中括号包裹（如 [noraneko] 或 【noraneko】），
        # 且剥离后仍有内容，则加入剥离外层括号后的候选名
        if (raw_name.startswith('[') and raw_name.endswith(']')) and len(raw_name) > 2:
            no_brackets = raw_name[1:-1].strip()
            if no_brackets and no_brackets not in candidates:
                candidates.append(no_brackets)
        elif (raw_name.startswith('【') and raw_name.endswith('】')) and len(raw_name) > 2:
            no_brackets = raw_name[1:-1].strip()
            if no_brackets and no_brackets not in candidates:
                candidates.append(no_brackets)

        # 容错：osu! 规则中空格与下划线 _ 等价互通
        for cand in list(candidates):
            if "_" in cand:
                spaced = cand.replace("_", " ")
                if spaced not in candidates:
                    candidates.append(spaced)
            if " " in cand:
                underscored = cand.replace(" ", "_")
                if underscored not in candidates:
                    candidates.append(underscored)

        headers = OsugachaClient._get_api_headers(api_key)

        last_err = "未找到该玩家"
        for name in candidates:
            url = f"{BASE_URL}/users/{urllib.parse.quote(name)}/profile"
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    return True, resp.json(), "获取成功"
                elif resp.status_code == 404:
                    last_err = "未找到该玩家"
                elif resp.status_code == 401:
                    last_err = "未授权或 API Key 无效"
                else:
                    last_err = f"请求失败 HTTP {resp.status_code}"
            except Exception as e:
                last_err = f"网络异常: {str(e)}"
                continue

        return False, None, last_err

    @staticmethod
    def search_players(query: str, limit: int = 10, api_key: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        在全服卡池中搜索选手/卡片信息
        GET /api/players?q=...&limit=...
        """
        import html
        q = html.unescape(query).strip()
        if not q:
            return False, None, "搜索关键词不能为空"

        headers = OsugachaClient._get_api_headers(api_key)
        url = f"{BASE_URL}/players"
        params = {"q": q, "limit": limit}

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                return True, resp.json(), "获取成功"
            elif resp.status_code == 401:
                return False, None, "API Key 无效或未授权"
            return False, None, f"搜索失败 HTTP {resp.status_code}"
        except Exception as e:
            return False, None, f"网络异常: {str(e)}"

    @staticmethod
    def get_player_by_id(player_id: int, api_key: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        按选手 osu! ID 获取选手卡片详细数据
        GET /api/players/{id}
        """
        headers = OsugachaClient._get_api_headers(api_key)
        url = f"{BASE_URL}/players/{player_id}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return True, resp.json(), "获取成功"
            return False, None, f"获取失败 HTTP {resp.status_code}"
        except Exception as e:
            return False, None, f"网络异常: {str(e)}"

    @staticmethod
    def get_player_owners(player_id: int, api_key: Optional[str] = None) -> Tuple[bool, Optional[List[Dict[str, Any]]], str]:
        """
        获取持有该选手卡片的藏家排行榜
        GET /api/players/{id}/owners
        """
        headers = OsugachaClient._get_api_headers(api_key)
        url = f"{BASE_URL}/players/{player_id}/owners"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return True, resp.json(), "获取成功"
            return False, None, f"获取失败 HTTP {resp.status_code}"
        except Exception as e:
            return False, None, f"网络异常: {str(e)}"

    @staticmethod
    def search_market(
        kind: str = "card",
        query: Optional[str] = None,
        rarity: Optional[str] = None,
        limit: int = 8,
        mode: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        查询市场挂单行情 (支持 card, mod, item，支持 mode='auction' 拍卖)
        GET /api/market/listings?kind=...&q=...&rarity=...&mode=...
        """
        headers = OsugachaClient._get_api_headers(api_key)
        url = f"{BASE_URL}/market/listings"
        params: Dict[str, Any] = {"kind": kind, "limit": limit}
        if mode:
            params["mode"] = mode
        if query and kind == "card":
            import html
            params["q"] = html.unescape(query).strip()
        if rarity:
            params["rarity"] = rarity.strip().lower()

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                return True, resp.json(), "获取成功"
            return False, None, f"获取失败 HTTP {resp.status_code}"
        except Exception as e:
            return False, None, f"网络异常: {str(e)}"

    @staticmethod
    def get_market_guide(
        card_id: Optional[str] = None,
        mod_id: Optional[str] = None,
        item_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        查询市场价格指导与历史成交数据 (近30天成交次数、中位数、最低最高)
        GET /api/market/guide?cardId=... / ?modId=... / ?itemId=...
        """
        headers = OsugachaClient._get_api_headers(api_key)
        url = f"{BASE_URL}/market/guide"
        params: Dict[str, Any] = {}
        if card_id:
            params["cardId"] = card_id
        elif mod_id:
            params["modId"] = mod_id
        elif item_id:
            params["itemId"] = item_id
        else:
            return False, None, "缺少查询参数 (需 cardId / modId / itemId)"

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                return True, resp.json(), "获取成功"
            return False, None, f"获取指导价失败 HTTP {resp.status_code}"
        except Exception as e:
            return False, None, f"网络异常: {str(e)}"

    @staticmethod
    def get_card_sale_price(
        card_id: str,
        api_key: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        查询单张卡片参考售价与近期中位数
        GET /api/market/cards/{cardId}/sale-price
        """
        headers = OsugachaClient._get_api_headers(api_key)
        url = f"{BASE_URL}/market/cards/{card_id}/sale-price"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return True, resp.json(), "获取成功"
            return False, None, f"获取售价参考失败 HTTP {resp.status_code}"
        except Exception as e:
            return False, None, f"网络异常: {str(e)}"



