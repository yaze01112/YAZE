import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from agents.threads_rss_poster.config import AgentConfig, FeedConfig
from agents.threads_rss_poster.poster_agent import PosterAgent, format_post
from agents.threads_rss_poster.rss_source import FeedEntry
from agents.threads_rss_poster.state_store import StateStore
from agents.threads_rss_poster.threads_client import ThreadsAPIError


def _make_entry(entry_id: str = "id-1") -> FeedEntry:
    return FeedEntry(
        id=entry_id,
        title="Example title",
        link="https://example.com/post",
        summary="Example summary",
        source_name="example-feed",
    )


class FormatPostTest(unittest.TestCase):
    def test_formats_all_fields(self):
        text = format_post("{title} - {link} - {summary} - {source}", _make_entry())
        self.assertEqual(text, "Example title - https://example.com/post - Example summary - example-feed")


class PosterAgentTest(unittest.TestCase):
    def _make_agent(self, config: AgentConfig, threads_client=None) -> tuple[PosterAgent, StateStore, str]:
        tmp_dir = tempfile.mkdtemp()
        state_path = os.path.join(tmp_dir, "state.json")
        config.state_file = state_path
        state = StateStore(state_path)
        return PosterAgent(config, state, threads_client), state, tmp_dir

    def _base_config(self) -> AgentConfig:
        return AgentConfig(
            feeds=[FeedConfig(name="example-feed", url="https://example.com/feed.xml")],
            max_posts_per_cycle=3,
            dry_run=True,
        )

    @patch("agents.threads_rss_poster.poster_agent.fetch_entries")
    def test_dry_run_marks_entry_posted_without_calling_threads(self, mock_fetch):
        mock_fetch.return_value = [_make_entry("id-1")]
        config = self._base_config()
        agent, state, _ = self._make_agent(config)

        posted = agent.run_once()

        self.assertEqual(posted, 1)
        self.assertTrue(state.is_posted("id-1"))

    @patch("agents.threads_rss_poster.poster_agent.fetch_entries")
    def test_skips_already_posted_entries(self, mock_fetch):
        mock_fetch.return_value = [_make_entry("id-1")]
        config = self._base_config()
        agent, state, _ = self._make_agent(config)

        agent.run_once()
        posted_second_cycle = agent.run_once()

        self.assertEqual(posted_second_cycle, 0)

    @patch("agents.threads_rss_poster.poster_agent.fetch_entries")
    def test_respects_max_posts_per_cycle(self, mock_fetch):
        mock_fetch.return_value = [_make_entry("id-1"), _make_entry("id-2"), _make_entry("id-3")]
        config = self._base_config()
        config.max_posts_per_cycle = 2
        agent, state, _ = self._make_agent(config)

        posted = agent.run_once()

        self.assertEqual(posted, 2)

    @patch("agents.threads_rss_poster.poster_agent.fetch_entries")
    def test_live_mode_calls_threads_client_and_marks_posted_on_success(self, mock_fetch):
        mock_fetch.return_value = [_make_entry("id-1")]
        config = self._base_config()
        config.dry_run = False
        threads_client = Mock()
        threads_client.publish_text.return_value = "published-1"
        agent, state, _ = self._make_agent(config, threads_client)

        posted = agent.run_once()

        self.assertEqual(posted, 1)
        threads_client.publish_text.assert_called_once()
        self.assertTrue(state.is_posted("id-1"))

    @patch("agents.threads_rss_poster.poster_agent.fetch_entries")
    def test_failed_publish_does_not_mark_entry_posted(self, mock_fetch):
        mock_fetch.return_value = [_make_entry("id-1")]
        config = self._base_config()
        config.dry_run = False
        threads_client = Mock()
        threads_client.publish_text.side_effect = ThreadsAPIError("boom")
        agent, state, _ = self._make_agent(config, threads_client)

        agent.run_once()

        self.assertFalse(state.is_posted("id-1"))

    @patch("agents.threads_rss_poster.poster_agent.fetch_entries")
    def test_feed_fetch_failure_is_skipped_without_crashing(self, mock_fetch):
        mock_fetch.side_effect = ValueError("bad feed")
        config = self._base_config()
        agent, _, _ = self._make_agent(config)

        posted = agent.run_once()

        self.assertEqual(posted, 0)


if __name__ == "__main__":
    unittest.main()
