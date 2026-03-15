from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Set, Tuple

from .config import load_json_file, write_json_file


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StateManager:
    state_dir: Path

    def _path(self, name: str) -> Path:
        return self.state_dir / name

    def load_posts(self) -> Dict[str, Any]:
        return load_json_file(self._path("posts.json"), {"posts": {}, "latest_post_id": None})

    def save_posts(self, data: Dict[str, Any]) -> None:
        write_json_file(self._path("posts.json"), data)

    def load_handled_replies(self) -> Dict[str, Any]:
        return load_json_file(self._path("handled_replies.json"), {"reply_ids": [], "items": {}})

    def save_handled_replies(self, data: Dict[str, Any]) -> None:
        write_json_file(self._path("handled_replies.json"), data)

    def load_dm_sent(self) -> Dict[str, Any]:
        return load_json_file(self._path("dm_sent.json"), {"sent_keys": [], "items": {}})

    def save_dm_sent(self, data: Dict[str, Any]) -> None:
        write_json_file(self._path("dm_sent.json"), data)

    def load_pipeline_state(self) -> Dict[str, Any]:
        return load_json_file(
            self._path("pipeline_state.json"),
            {"stage": "idle", "last_run_id": None, "updated_at": None, "monitor": {}, "last_theme_index": 0},
        )

    def save_pipeline_state(self, data: Dict[str, Any]) -> None:
        data["updated_at"] = utc_now_iso()
        write_json_file(self._path("pipeline_state.json"), data)

    def is_reply_handled(self, reply_id: str) -> bool:
        data = self.load_handled_replies()
        return reply_id in set(data.get("reply_ids", []))

    def mark_reply_handled(self, reply_id: str, payload: Dict[str, Any]) -> None:
        data = self.load_handled_replies()
        ids: Set[str] = set(data.get("reply_ids", []))
        ids.add(reply_id)
        items = data.get("items", {})
        items[reply_id] = payload
        self.save_handled_replies({"reply_ids": sorted(ids), "items": items})

    def was_dm_sent(self, campaign_id: str, user_id: str) -> bool:
        data = self.load_dm_sent()
        key = f"{campaign_id}:{user_id}"
        return key in set(data.get("sent_keys", []))

    def mark_dm_sent(self, campaign_id: str, user_id: str, payload: Dict[str, Any]) -> None:
        data = self.load_dm_sent()
        key = f"{campaign_id}:{user_id}"
        keys: Set[str] = set(data.get("sent_keys", []))
        keys.add(key)
        items = data.get("items", {})
        items[key] = payload
        self.save_dm_sent({"sent_keys": sorted(keys), "items": items})

    def record_post(self, post_id: str, payload: Dict[str, Any]) -> None:
        data = self.load_posts()
        posts = data.get("posts", {})
        posts[post_id] = payload
        data["posts"] = posts
        data["latest_post_id"] = post_id
        self.save_posts(data)

