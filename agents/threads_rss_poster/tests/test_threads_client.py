import unittest
from unittest.mock import Mock, patch

from agents.threads_rss_poster.threads_client import ThreadsAPIError, ThreadsClient


def _mock_response(status_code: int, payload: dict) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = str(payload)
    return response


class ThreadsClientTest(unittest.TestCase):
    def setUp(self):
        self.client = ThreadsClient(user_id="123", access_token="token")

    @patch("agents.threads_rss_poster.threads_client.requests.get")
    @patch("agents.threads_rss_poster.threads_client.requests.post")
    def test_publish_text_creates_waits_then_publishes_container(self, mock_post, mock_get):
        mock_post.side_effect = [
            _mock_response(200, {"id": "creation-1"}),
            _mock_response(200, {"id": "published-1"}),
        ]
        mock_get.return_value = _mock_response(200, {"status": "FINISHED"})

        published_id = self.client.publish_text("hello world")

        self.assertEqual(published_id, "published-1")
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(mock_get.call_count, 1)

        create_call, publish_call = mock_post.call_args_list
        self.assertIn("/123/threads", create_call.args[0])
        self.assertEqual(create_call.kwargs["params"]["text"], "hello world")
        self.assertIn("/123/threads_publish", publish_call.args[0])
        self.assertEqual(publish_call.kwargs["params"]["creation_id"], "creation-1")

        status_call = mock_get.call_args
        self.assertIn("/creation-1", status_call.args[0])

    @patch("agents.threads_rss_poster.threads_client.requests.get")
    @patch("agents.threads_rss_poster.threads_client.requests.post")
    def test_publish_text_truncates_to_max_length(self, mock_post, mock_get):
        mock_post.side_effect = [
            _mock_response(200, {"id": "creation-1"}),
            _mock_response(200, {"id": "published-1"}),
        ]
        mock_get.return_value = _mock_response(200, {"status": "FINISHED"})

        long_text = "x" * 600
        self.client.publish_text(long_text)

        create_call = mock_post.call_args_list[0]
        self.assertEqual(len(create_call.kwargs["params"]["text"]), 500)

    @patch("agents.threads_rss_poster.threads_client.requests.get")
    @patch("agents.threads_rss_poster.threads_client.requests.post")
    def test_create_container_error_raises(self, mock_post, mock_get):
        mock_post.return_value = _mock_response(400, {"error": "bad request"})

        with self.assertRaises(ThreadsAPIError):
            self.client.publish_text("hello")

        mock_get.assert_not_called()

    @patch("agents.threads_rss_poster.threads_client.requests.get")
    @patch("agents.threads_rss_poster.threads_client.requests.post")
    def test_missing_creation_id_raises(self, mock_post, mock_get):
        mock_post.return_value = _mock_response(200, {})

        with self.assertRaises(ThreadsAPIError):
            self.client.publish_text("hello")

    @patch("agents.threads_rss_poster.threads_client.time.sleep")
    @patch("agents.threads_rss_poster.threads_client.requests.get")
    @patch("agents.threads_rss_poster.threads_client.requests.post")
    def test_waits_for_container_status_before_publishing(self, mock_post, mock_get, mock_sleep):
        mock_post.side_effect = [
            _mock_response(200, {"id": "creation-1"}),
            _mock_response(200, {"id": "published-1"}),
        ]
        mock_get.side_effect = [
            _mock_response(200, {"status": "IN_PROGRESS"}),
            _mock_response(200, {"status": "FINISHED"}),
        ]

        published_id = self.client.publish_text("hello")

        self.assertEqual(published_id, "published-1")
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called()

    @patch("agents.threads_rss_poster.threads_client.time.sleep")
    @patch("agents.threads_rss_poster.threads_client.requests.get")
    @patch("agents.threads_rss_poster.threads_client.requests.post")
    def test_container_error_status_raises(self, mock_post, mock_get, mock_sleep):
        mock_post.return_value = _mock_response(200, {"id": "creation-1"})
        mock_get.return_value = _mock_response(200, {"status": "ERROR"})

        with self.assertRaises(ThreadsAPIError):
            self.client.publish_text("hello")

    @patch("agents.threads_rss_poster.threads_client.time.sleep")
    @patch("agents.threads_rss_poster.threads_client.requests.get")
    @patch("agents.threads_rss_poster.threads_client.requests.post")
    def test_transient_publish_error_is_retried_once(self, mock_post, mock_get, mock_sleep):
        mock_post.side_effect = [
            _mock_response(200, {"id": "creation-1"}),
            _mock_response(500, {"error": "transient"}),
            _mock_response(200, {"id": "published-1"}),
        ]
        mock_get.return_value = _mock_response(200, {"status": "FINISHED"})

        published_id = self.client.publish_text("hello")

        self.assertEqual(published_id, "published-1")
        self.assertEqual(mock_post.call_count, 3)

    @patch("agents.threads_rss_poster.threads_client.time.sleep")
    @patch("agents.threads_rss_poster.threads_client.requests.get")
    @patch("agents.threads_rss_poster.threads_client.requests.post")
    def test_persistent_publish_error_raises_after_one_retry(self, mock_post, mock_get, mock_sleep):
        mock_post.side_effect = [
            _mock_response(200, {"id": "creation-1"}),
            _mock_response(500, {"error": "transient"}),
            _mock_response(500, {"error": "still transient"}),
        ]
        mock_get.return_value = _mock_response(200, {"status": "FINISHED"})

        with self.assertRaises(ThreadsAPIError):
            self.client.publish_text("hello")

        self.assertEqual(mock_post.call_count, 3)


if __name__ == "__main__":
    unittest.main()
