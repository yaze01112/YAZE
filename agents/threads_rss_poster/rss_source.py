from __future__ import annotations

import hashlib
from dataclasses import dataclass

import feedparser


@dataclass
class FeedEntry:
    id: str
    title: str
    link: str
    summary: str
    source_name: str


def _entry_id(entry) -> str:
    """Build a stable dedup key for a feed entry.

    Falls back through guid/id -> link -> title since not every feed sets
    every field, and the same value must be produced on every fetch so the
    state store can recognize an already-posted entry.
    """
    raw_id = entry.get("id") or entry.get("guid") or entry.get("link") or entry.get("title", "")
    return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()


def fetch_entries(feed_name: str, feed_url: str) -> list[FeedEntry]:
    parsed = feedparser.parse(feed_url)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"Failed to parse feed {feed_name} ({feed_url}): {parsed.bozo_exception}")

    return [
        FeedEntry(
            id=_entry_id(entry),
            title=entry.get("title", "").strip(),
            link=entry.get("link", "").strip(),
            summary=entry.get("summary", "").strip(),
            source_name=feed_name,
        )
        for entry in parsed.entries
    ]
