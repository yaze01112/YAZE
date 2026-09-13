import os
import tempfile
import unittest

from agents.threads_rss_poster.state_store import StateStore


class StateStoreTest(unittest.TestCase):
    def test_marks_and_persists_posted_ids(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = os.path.join(tmp_dir, "state.json")

            store = StateStore(state_path)
            self.assertFalse(store.is_posted("entry-1"))

            store.mark_posted("entry-1")
            self.assertTrue(store.is_posted("entry-1"))

            reloaded = StateStore(state_path)
            self.assertTrue(reloaded.is_posted("entry-1"))
            self.assertFalse(reloaded.is_posted("entry-2"))

    def test_missing_state_file_starts_empty(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = StateStore(os.path.join(tmp_dir, "does-not-exist.json"))
            self.assertFalse(store.is_posted("anything"))


if __name__ == "__main__":
    unittest.main()
