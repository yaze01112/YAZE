"""Minimal client for Meta's official Threads Graph API.

Docs: https://developers.facebook.com/docs/threads
"""
from __future__ import annotations

import time

import requests

API_BASE = "https://graph.threads.net/v1.0"


class ThreadsAPIError(RuntimeError):
    def __init__(self, response: requests.Response):
        self.response = response
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        super().__init__(f"Threads API error {response.status_code}: {detail}")


def _check(response: requests.Response) -> dict:
    if not response.ok:
        raise ThreadsAPIError(response)
    return response.json()


def exchange_long_lived_token(app_secret: str, short_lived_token: str) -> dict:
    """Exchange a short-lived user token for a long-lived one (~60 days)."""
    response = requests.get(
        f"{API_BASE}/access_token",
        params={
            "grant_type": "th_exchange_token",
            "client_secret": app_secret,
            "access_token": short_lived_token,
        },
        timeout=30,
    )
    return _check(response)


def refresh_long_lived_token(long_lived_token: str) -> dict:
    """Refresh a long-lived token before it expires (must be >24h old, <60 days)."""
    response = requests.get(
        f"{API_BASE}/refresh_access_token",
        params={
            "grant_type": "th_refresh_token",
            "access_token": long_lived_token,
        },
        timeout=30,
    )
    return _check(response)


def create_text_container(
    threads_user_id: str, access_token: str, text: str
) -> str:
    """Create a text media container and return its creation id."""
    response = requests.post(
        f"{API_BASE}/{threads_user_id}/threads",
        params={
            "media_type": "TEXT",
            "text": text,
            "access_token": access_token,
        },
        timeout=30,
    )
    return _check(response)["id"]


def create_image_container(
    threads_user_id: str, access_token: str, image_url: str, text: str = ""
) -> str:
    """Create an image media container and return its creation id.

    image_url must be a publicly reachable URL to the image.
    """
    params = {
        "media_type": "IMAGE",
        "image_url": image_url,
        "access_token": access_token,
    }
    if text:
        params["text"] = text
    response = requests.post(
        f"{API_BASE}/{threads_user_id}/threads", params=params, timeout=30
    )
    return _check(response)["id"]


def wait_until_container_ready(
    creation_id: str, access_token: str, timeout_s: float = 60.0, poll_s: float = 2.0
) -> None:
    """Poll a container's status until it's FINISHED, raising on ERROR or timeout."""
    deadline = time.monotonic() + timeout_s
    while True:
        response = requests.get(
            f"{API_BASE}/{creation_id}",
            params={"fields": "status,error_message", "access_token": access_token},
            timeout=30,
        )
        data = _check(response)
        status = data.get("status")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise ThreadsAPIError(response)
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Container {creation_id} not ready after {timeout_s}s")
        time.sleep(poll_s)


def publish_container(threads_user_id: str, access_token: str, creation_id: str) -> str:
    """Publish a previously created media container. Returns the published post id."""
    response = requests.post(
        f"{API_BASE}/{threads_user_id}/threads_publish",
        params={"creation_id": creation_id, "access_token": access_token},
        timeout=30,
    )
    return _check(response)["id"]


def post_text(threads_user_id: str, access_token: str, text: str) -> str:
    """Create and publish a plain text Threads post. Returns the published post id."""
    creation_id = create_text_container(threads_user_id, access_token, text)
    return publish_container(threads_user_id, access_token, creation_id)


def post_image(
    threads_user_id: str, access_token: str, image_url: str, text: str = ""
) -> str:
    """Create and publish an image Threads post. Returns the published post id."""
    creation_id = create_image_container(threads_user_id, access_token, image_url, text)
    wait_until_container_ready(creation_id, access_token)
    return publish_container(threads_user_id, access_token, creation_id)
