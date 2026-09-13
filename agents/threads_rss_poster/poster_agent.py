from __future__ import annotations

import logging
import time

from .config import AgentConfig
from .rss_source import FeedEntry, fetch_entries
from .state_store import StateStore
from .threads_client import ThreadsAPIError, ThreadsClient

logger = logging.getLogger("threads_rss_poster")


def format_post(template: str, entry: FeedEntry) -> str:
    return template.format(
        title=entry.title,
        link=entry.link,
        summary=entry.summary,
        source=entry.source_name,
    )


class PosterAgent:
    def __init__(self, config: AgentConfig, state: StateStore, threads_client: ThreadsClient | None):
        self._config = config
        self._state = state
        self._threads_client = threads_client

    def run_once(self) -> int:
        """Fetch every configured feed and post new entries, up to
        max_posts_per_cycle. Returns how many entries were posted."""
        posted_count = 0
        for feed in self._config.feeds:
            if posted_count >= self._config.max_posts_per_cycle:
                break
            try:
                entries = fetch_entries(feed.name, feed.url)
            except Exception:
                logger.exception("Failed to fetch feed %s (%s)", feed.name, feed.url)
                continue

            for entry in entries:
                if posted_count >= self._config.max_posts_per_cycle:
                    break
                if self._state.is_posted(entry.id):
                    continue
                self._handle_new_entry(entry)
                posted_count += 1
        return posted_count

    def _handle_new_entry(self, entry: FeedEntry) -> None:
        text = format_post(self._config.post_template, entry)

        if self._config.dry_run or self._threads_client is None:
            logger.info("[dry-run] would post from %s: %s", entry.source_name, text.replace("\n", " "))
            self._state.mark_posted(entry.id)
            return

        try:
            published_id = self._threads_client.publish_text(text)
        except ThreadsAPIError:
            logger.exception("Failed to publish entry %s from %s", entry.id, entry.source_name)
            return

        logger.info("Posted entry %s from %s as Threads post %s", entry.id, entry.source_name, published_id)
        self._state.mark_posted(entry.id)

    def run_forever(self) -> None:
        logger.info("Starting poster agent loop, interval=%ss", self._config.poll_interval_seconds)
        while True:
            try:
                posted = self.run_once()
                logger.info("Cycle complete, posted %d new item(s)", posted)
            except Exception:
                logger.exception("Unhandled error during poster cycle")
            time.sleep(self._config.poll_interval_seconds)
