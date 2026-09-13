from __future__ import annotations

import time

import requests

THREADS_API_BASE = "https://graph.threads.net/v1.0"
MAX_POST_LENGTH = 500

# Container creation is asynchronous: publishing immediately after creating
# one can 400 with "Media Not Found" before Threads finishes processing it.
CONTAINER_POLL_INTERVAL_SECONDS = 2.0
CONTAINER_POLL_MAX_ATTEMPTS = 5

# Meta occasionally returns a transient 5xx on publish; one retry clears it.
PUBLISH_RETRY_DELAY_SECONDS = 2.0


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
        self._wait_until_container_ready(creation_id)
        return self._publish_container(creation_id)

    def _wait_until_container_ready(self, creation_id: str) -> None:
        for _ in range(CONTAINER_POLL_MAX_ATTEMPTS):
            response = requests.get(
                f"{THREADS_API_BASE}/{creation_id}",
                params={"fields": "status", "access_token": self._access_token},
                timeout=self._timeout_seconds,
            )
            payload = self._parse_response(response)
            status = payload.get("status")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise ThreadsAPIError(f"Threads container {creation_id} failed to process: {payload}")
            time.sleep(CONTAINER_POLL_INTERVAL_SECONDS)
        # Status never confirmed FINISHED within the poll budget; still try
        # to publish since Threads may just be slow to update the field.

    def _create_container(self, text: str) -> str:
        # Meta's documented examples pass these as query-string params, not a
        # POST body, and the API is inconsistent about accepting the latter.
        response = requests.post(
            f"{THREADS_API_BASE}/{self._user_id}/threads",
            params={
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
        response = self._post_publish(creation_id)
        if response.status_code >= 500:
            # Transient server-side error; one retry after a short delay clears it.
            time.sleep(PUBLISH_RETRY_DELAY_SECONDS)
            response = self._post_publish(creation_id)

        payload = self._parse_response(response)
        published_id = payload.get("id")
        if not published_id:
            raise ThreadsAPIError(f"Threads API did not return a published id: {payload}")
        return published_id

    def _post_publish(self, creation_id: str) -> requests.Response:
        return requests.post(
            f"{THREADS_API_BASE}/{self._user_id}/threads_publish",
            params={
                "creation_id": creation_id,
                "access_token": self._access_token,
            },
            timeout=self._timeout_seconds,
        )

    @staticmethod
    def _parse_response(response: requests.Response) -> dict:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ThreadsAPIError(f"Invalid JSON from Threads API: {response.text}") from exc
        if response.status_code >= 400:
            raise ThreadsAPIError(f"Threads API error {response.status_code}: {payload}")
        return payload
