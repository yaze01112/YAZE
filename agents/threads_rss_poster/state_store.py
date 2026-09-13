from __future__ import annotations

import json
import os
from threading import Lock


class StateStore:
    """Tracks which feed entries have already been posted, persisted to disk
    so restarts don't repost old items."""

    def __init__(self, path: str):
        self._path = path
        self._lock = Lock()
        self._posted_ids: set[str] = self._load()

    def _load(self) -> set[str]:
        if not os.path.exists(self._path):
            return set()
        with open(self._path, "r", encoding="utf-8") as state_file:
            data = json.load(state_file)
        return set(data.get("posted_ids", []))

    def is_posted(self, entry_id: str) -> bool:
        return entry_id in self._posted_ids

    def mark_posted(self, entry_id: str) -> None:
        with self._lock:
            self._posted_ids.add(entry_id)
            self._save()

    def _save(self) -> None:
        # Write to a temp file then rename so a crash mid-write can't corrupt state.json.
        tmp_path = f"{self._path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as state_file:
            json.dump({"posted_ids": sorted(self._posted_ids)}, state_file, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self._path)
