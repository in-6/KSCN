import time
import threading
import requests
from typing import Optional, Dict, Any, Tuple, List

from .client import OsugachaClient
from .storage import watch_storage
from .formatter import format_watch_alert

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
        print(f"[Osugacha] 发送 QQ 消息失败: {e}")


class GachaScheduler:
    """
    只读集市低价盯盘轮询调度器 (安全合规，仅查询公开/API Key 只读市场数据)
    """
    POLL_INTERVAL_SECONDS = 300
    ITEM_ALERT_COOLDOWN_SECONDS = 1800

    def __init__(self):
        self._started = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self):
        if self._started:
            return
        self._started = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"[Osugacha] 集市低价盯盘调度器已启动 (轮询间隔 {self.POLL_INTERVAL_SECONDS}s)。")

    def stop(self):
        self._stop_event.set()
        self._started = False

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self.check_once()
            except Exception as e:
                print(f"[Osugacha] 盯盘轮询异常: {e}")
            self._stop_event.wait(self.POLL_INTERVAL_SECONDS)

    def check_once(self):
        """执行单轮盯盘扫描（可由后台线程调用，也便于单元测试直接调用）"""
        watches = watch_storage.list_watches()
        if not watches:
            return

        now = time.time()
        item_watches = [w for w in watches if w.get("kind") == "item"]
        listing_watches = [w for w in watches if w.get("kind") != "item"]

        # 1. 物品盘口：每轮只调用 1 次 GET /api/market/book
        if item_watches:
            try:
                ok_b, book_data, _ = OsugachaClient.get_market_book()
                if ok_b and book_data:
                    book_map = {it.get("itemId"): it for it in book_data.get("items", [])}
                    for w in item_watches:
                        try:
                            self._check_item_watch(w, book_map, now)
                        except Exception as e:
                            print(f"[Osugacha] 物品盯盘 #{w.get('id')} 异常: {e}")
            except Exception as e:
                print(f"[Osugacha] 拉取物品盘口失败: {e}")

        # 2. 挂单类 (card / mod / setup / stone)：按相同查询参数在单轮内做缓存复用
        listing_cache: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
        first_req = True
        for w in listing_watches:
            try:
                kind = w.get("kind", "card")
                params = w.get("params") or {}
                cache_key = (kind, tuple(sorted((k, str(v)) for k, v in params.items() if v is not None)))

                if cache_key not in listing_cache:
                    if not first_req:
                        time.sleep(0.3)
                    first_req = False
                    ok_s, data, _ = OsugachaClient.search_market(
                        kind=kind,
                        query=params.get("query"),
                        rarity=params.get("rarity"),
                        mod_type=params.get("mod_type"),
                        mod_rarity=params.get("mod_rarity"),
                        setup_kind=params.get("setup_kind"),
                        setup_grades=params.get("setup_grades"),
                        stone_kind=params.get("stone_kind"),
                        sort="price_asc",
                        limit=5,
                    )
                    if not ok_s or not data:
                        continue
                    listing_cache[cache_key] = data.get("items", [])

                self._check_listing_watch(w, listing_cache[cache_key], now)
            except Exception as e:
                print(f"[Osugacha] 挂单盯盘 #{w.get('id')} 异常: {e}")

    def _check_item_watch(self, w: Dict[str, Any], book_map: Dict[str, Dict[str, Any]], now: float):
        wid = int(w["id"])
        item_id = (w.get("params") or {}).get("item_id")
        max_price = int(w.get("max_price", 0))
        entry = book_map.get(item_id)
        buy_price = entry.get("buy") if entry else None

        last_price = w.get("last_notified_price")
        last_at = float(w.get("last_notified_at") or 0)

        if buy_price is not None and buy_price <= max_price:
            should_alert = (
                last_price is None
                or buy_price < last_price
                or (now - last_at >= self.ITEM_ALERT_COOLDOWN_SECONDS)
            )
            if should_alert:
                msg = format_watch_alert(w, [], book_entry=entry)
                send_qq_msg(str(w["uid"]), msg, gid=w.get("gid"))
                watch_storage.update_watch_state(wid, last_notified_price=buy_price, last_notified_at=now)
        else:
            if last_price is not None:
                watch_storage.update_watch_state(wid, last_notified_price=None)

    def _check_listing_watch(self, w: Dict[str, Any], items: List[Dict[str, Any]], now: float):
        wid = int(w["id"])
        max_price = int(w.get("max_price", 0))
        seen_ids = list(w.get("last_notified_ids") or [])
        seen_set = set(seen_ids)

        new_matches = []
        for it in items:
            price = it.get("price", 0)
            lid = it.get("id")
            if price <= max_price and lid and lid not in seen_set:
                new_matches.append(it)

        if new_matches:
            msg = format_watch_alert(w, new_matches)
            send_qq_msg(str(w["uid"]), msg, gid=w.get("gid"))
            for it in new_matches:
                lid = it.get("id")
                if lid and lid not in seen_set:
                    seen_ids.append(lid)
                    seen_set.add(lid)
            watch_storage.update_watch_state(wid, last_notified_ids=seen_ids, last_notified_at=now)


scheduler = GachaScheduler()
