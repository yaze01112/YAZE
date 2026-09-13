from __future__ import annotations

import requests

THREADS_API_BASE = "https://graph.threads.net/v1.0"
MAX_POST_LENGTH = 500


class ThreadsAPIError(RuntimeError):
    pass


class ThreadsClient:
    """Minimal client for the Threads publishing flow: create a media
    container, then publish it. See Meta's Threads API docs for details."""

    def __init__(self, user_id: str, access_token: str, timeout_seconds: float = 15.0):
        self._user_id = user_id
        self._access_token = access_token
        self._timeout_seconds = timeout_seconds

    def publish_text(self, text: str) -> str:
        text = text[:MAX_POST_LENGTH]
        creation_id = self._create_container(text)
        return self._publish_container(creation_id)

    def _create_container(self, text: str) -> str:
        response = requests.post(
            f"{THREADS_API_BASE}/{self._user_id}/threads",
            data={
                "media_type": "TEXT",
                "text": text,
                "access_token": self._access_token,
            },
            timeout=self._timeout_seconds,
        )
        payload = self._parse_response(response)
        creation_id = payload.get("id")
        if not creation_id:
            raise ThreadsAPIError(f"Threads API did not return a creation id: {payload}")
        return creation_id

    def _publish_container(self, creation_id: str) -> str:
        response = requests.post(
            f"{THREADS_API_BASE}/{self._user_id}/threads_publish",
            data={
                "creation_id": creation_id,
                "access_token": self._access_token,
            },
            timeout=self._timeout_seconds,
        )
        payload = self._parse_response(response)
        published_id = payload.get("id")
        if not published_id:
            raise ThreadsAPIError(f"Threads API did not return a published id: {payload}")
        return published_id

    @staticmethod
    def _parse_response(response: requests.Response) -> dict:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ThreadsAPIError(f"Invalid JSON from Threads API: {response.text}") from exc
        if response.status_code >= 400:
            raise ThreadsAPIError(f"Threads API error {response.status_code}: {payload}")
        return payload
