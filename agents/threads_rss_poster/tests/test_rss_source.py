import unittest
from unittest.mock import patch

from agents.threads_rss_poster.rss_source import fetch_entries


class FakeEntry(dict):
    """feedparser entries behave like dicts with .get()."""


class FakeParsedFeed:
    def __init__(self, entries, bozo=False, bozo_exception=None):
        self.entries = entries
        self.bozo = bozo
        self.bozo_exception = bozo_exception


class FetchEntriesTest(unittest.TestCase):
    @patch("agents.threads_rss_poster.rss_source.feedparser.parse")
    def test_maps_entry_fields(self, mock_parse):
        mock_parse.return_value = FakeParsedFeed(
            [FakeEntry(id="guid-1", title="Title", link="https://x/1", summary="Summary")]
        )

        entries = fetch_entries("my-feed", "https://x/feed.xml")

        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.title, "Title")
        self.assertEqual(entry.link, "https://x/1")
        self.assertEqual(entry.summary, "Summary")
        self.assertEqual(entry.source_name, "my-feed")

    @patch("agents.threads_rss_poster.rss_source.feedparser.parse")
    def test_same_guid_produces_same_id(self, mock_parse):
        mock_parse.return_value = FakeParsedFeed(
            [
                FakeEntry(id="guid-1", title="A", link="https://x/1", summary=""),
                FakeEntry(id="guid-1", title="A changed title", link="https://x/1", summary=""),
            ]
        )

        entries = fetch_entries("my-feed", "https://x/feed.xml")

        self.assertEqual(entries[0].id, entries[1].id)

    @patch("agents.threads_rss_poster.rss_source.feedparser.parse")
    def test_different_entries_produce_different_ids(self, mock_parse):
        mock_parse.return_value = FakeParsedFeed(
            [
                FakeEntry(id="guid-1", title="A", link="https://x/1", summary=""),
                FakeEntry(id="guid-2", title="B", link="https://x/2", summary=""),
            ]
        )

        entries = fetch_entries("my-feed", "https://x/feed.xml")

        self.assertNotEqual(entries[0].id, entries[1].id)

    @patch("agents.threads_rss_poster.rss_source.feedparser.parse")
    def test_bozo_with_no_entries_raises(self, mock_parse):
        mock_parse.return_value = FakeParsedFeed([], bozo=True, bozo_exception=Exception("parse error"))

        with self.assertRaises(ValueError):
            fetch_entries("my-feed", "https://x/feed.xml")


if __name__ == "__main__":
    unittest.main()
