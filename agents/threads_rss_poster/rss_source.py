from __future__ import annotations

import hashlib
from dataclasses import dataclass

import feedparser

# Some sites block feedparser's default user agent (it identifies itself as
# a bot) and serve an HTML error/challenge page instead of the feed, which
# then fails to parse as XML. Requesting like an ordinary browser avoids that.
_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}


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
    parsed = feedparser.parse(feed_url, request_headers=_REQUEST_HEADERS)
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
