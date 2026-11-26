import os
import json
import threading
import datetime
from typing import Dict, Any, Optional, Tuple, List

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
WATCHES_FILE = os.path.join(DATA_DIR, "watches.json")

_lock = threading.Lock()
_watch_lock = threading.Lock()
_UNSET = object()


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


class WatchStorage:
    """
    集市低价盯盘规则持久化存储 (osugacha/data/watches.json)
    """
    def __init__(self, file_path: str = WATCHES_FILE):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({"next_id": 1, "watches": []}, f)

    def _read(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("watches"), list):
                    data.setdefault("next_id", 1)
                    return data
        except Exception:
            pass
        return {"next_id": 1, "watches": []}

    def _write(self, data: Dict[str, Any]):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_watch(
        self,
        uid: str,
        gid: Optional[str],
        kind: str,
        params: Dict[str, Any],
        label: str,
        max_price: int,
        max_per_user: int = 10,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        uid_s = str(uid)
        gid_s = str(gid) if gid else None
        with _watch_lock:
            data = self._read()
            user_watches = [w for w in data["watches"] if str(w.get("uid")) == uid_s]
            if len(user_watches) >= max_per_user:
                return False, None, f"每人最多同时设置 {max_per_user} 条盯盘规则，请先用 `>gacha watch del <编号>` 删除旧规则。"

            wid = int(data.get("next_id", 1))
            data["next_id"] = wid + 1
            entry = {
                "id": wid,
                "uid": uid_s,
                "gid": gid_s,
                "kind": kind,
                "params": params,
                "label": label,
                "max_price": int(max_price),
                "last_notified_ids": [],
                "last_notified_price": None,
                "last_notified_at": 0,
                "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
            }
            data["watches"].append(entry)
            self._write(data)
            return True, entry, "添加成功"

    def list_watches(self, uid: Optional[str] = None) -> List[Dict[str, Any]]:
        with _watch_lock:
            data = self._read()
            watches = data.get("watches", [])
            if uid is None:
                return list(watches)
            uid_s = str(uid)
            return [w for w in watches if str(w.get("uid")) == uid_s]

    def delete_watch(self, uid: str, watch_id: int) -> bool:
        uid_s = str(uid)
        with _watch_lock:
            data = self._read()
            before = len(data["watches"])
            data["watches"] = [
                w for w in data["watches"]
                if not (int(w.get("id", -1)) == int(watch_id) and str(w.get("uid")) == uid_s)
            ]
            if len(data["watches"]) < before:
                self._write(data)
                return True
            return False

    def clear_watches(self, uid: str) -> int:
        uid_s = str(uid)
        with _watch_lock:
            data = self._read()
            before = len(data["watches"])
            data["watches"] = [w for w in data["watches"] if str(w.get("uid")) != uid_s]
            removed = before - len(data["watches"])
            if removed > 0:
                self._write(data)
            return removed

    def update_watch_state(
        self,
        watch_id: int,
        last_notified_ids: Optional[List[str]] = None,
        last_notified_price: Any = _UNSET,
        last_notified_at: Optional[float] = None,
    ):
        with _watch_lock:
            data = self._read()
            changed = False
            for w in data["watches"]:
                if int(w.get("id", -1)) == int(watch_id):
                    if last_notified_ids is not None:
                        w["last_notified_ids"] = last_notified_ids[-30:]
                        changed = True
                    if last_notified_price is not _UNSET:
                        w["last_notified_price"] = last_notified_price
                        changed = True
                    if last_notified_at is not None:
                        w["last_notified_at"] = last_notified_at
                        changed = True
                    break
            if changed:
                self._write(data)


watch_storage = WatchStorage()

