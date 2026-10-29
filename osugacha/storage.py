import os
import json
import threading
import datetime
from typing import Dict, Any, Optional, Tuple

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

_lock = threading.Lock()


def ensure_daily_stats(stats: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    检查并维护用户的每日统计数据（按本地自然日 00:00 重置）
    返回 (更新后的stats, 是否发生了跨天重置)
    """
    today = datetime.date.today().isoformat()
    reset = False
    if stats.get("date") != today:
        stats["date"] = today
        stats["today_opened"] = 0
        stats["today_best"] = "暂无"
        stats["today_best_level"] = 0
        reset = True
    else:
        if "today_opened" not in stats:
            stats["today_opened"] = stats.get("total_opened", 0)
        if "today_best" not in stats:
            stats["today_best"] = stats.get("best_pull", "暂无")
        if "today_best_level" not in stats:
            stats["today_best_level"] = 0
    return stats, reset


class Storage:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _read(self) -> Dict[str, Any]:
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write(self, data: Dict[str, Any]):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        with _lock:
            data = self._read()
            return data.get(str(uid))

    def save_user(self, uid: str, user_dict: Dict[str, Any]):
        with _lock:
            data = self._read()
            data[str(uid)] = user_dict
            self._write(data)

    def delete_user(self, uid: str) -> bool:
        with _lock:
            data = self._read()
            uid = str(uid)
            if uid in data:
                del data[uid]
                self._write(data)
                return True
            return False

    def get_all_users(self) -> Dict[str, Any]:
        with _lock:
            return self._read()

    def update_user_fields(self, uid: str, **kwargs):
        with _lock:
            data = self._read()
            uid = str(uid)
            if uid in data:
                data[uid].update(kwargs)
                self._write(data)


storage = Storage()

