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

    @patch("agents.threads_rss_poster.threads_client.requests.post")
    def test_publish_text_creates_then_publishes_container(self, mock_post):
        mock_post.side_effect = [
            _mock_response(200, {"id": "creation-1"}),
            _mock_response(200, {"id": "published-1"}),
        ]

        published_id = self.client.publish_text("hello world")

        self.assertEqual(published_id, "published-1")
        self.assertEqual(mock_post.call_count, 2)

        create_call, publish_call = mock_post.call_args_list
        self.assertIn("/123/threads", create_call.args[0])
        self.assertEqual(create_call.kwargs["data"]["text"], "hello world")
        self.assertIn("/123/threads_publish", publish_call.args[0])
        self.assertEqual(publish_call.kwargs["data"]["creation_id"], "creation-1")

    @patch("agents.threads_rss_poster.threads_client.requests.post")
    def test_publish_text_truncates_to_max_length(self, mock_post):
        mock_post.side_effect = [
            _mock_response(200, {"id": "creation-1"}),
            _mock_response(200, {"id": "published-1"}),
        ]

        long_text = "x" * 600
        self.client.publish_text(long_text)

        create_call = mock_post.call_args_list[0]
        self.assertEqual(len(create_call.kwargs["data"]["text"]), 500)

    @patch("agents.threads_rss_poster.threads_client.requests.post")
    def test_create_container_error_raises(self, mock_post):
        mock_post.return_value = _mock_response(400, {"error": "bad request"})

        with self.assertRaises(ThreadsAPIError):
            self.client.publish_text("hello")

    @patch("agents.threads_rss_poster.threads_client.requests.post")
    def test_missing_creation_id_raises(self, mock_post):
        mock_post.return_value = _mock_response(200, {})

        with self.assertRaises(ThreadsAPIError):
            self.client.publish_text("hello")


if __name__ == "__main__":
    unittest.main()
