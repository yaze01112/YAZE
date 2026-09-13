"""CLI for posting to Threads, either a single post now or a scheduled queue.

Usage:
    python autopost.py post "Hello from my script!"
    python autopost.py post "Check this out" --image-url https://example.com/pic.jpg
    python autopost.py run-queue queue.json --state posted.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import threads_client as tc

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _credentials() -> tuple[str, str]:
    user_id = os.environ.get("THREADS_USER_ID")
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    if not user_id or not token:
        sys.exit(
            "Missing THREADS_USER_ID and/or THREADS_ACCESS_TOKEN environment "
            "variables. See README.md for how to obtain them."
        )
    return user_id, token


def cmd_post(args: argparse.Namespace) -> None:
    user_id, token = _credentials()
    if args.image_url:
        post_id = tc.post_image(user_id, token, args.image_url, args.text or "")
    else:
        post_id = tc.post_text(user_id, token, args.text)
    print(f"Published: https://www.threads.net/@me/post/{post_id}")


def _load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cmd_run_queue(args: argparse.Namespace) -> None:
    """Publish due posts from a JSON queue file.

    Queue file format: a list of objects, each with:
      - "id": a unique string identifying this post
      - "text": the post text (required for TEXT posts)
      - "image_url": optional, makes it an IMAGE post
      - "publish_at": ISO-8601 timestamp (UTC); posts due at or before now are published

    Intended to be invoked periodically (e.g. via cron) so posts go out on schedule.
    Already-published post ids are recorded in the state file to avoid duplicates.
    """
    user_id, token = _credentials()
    queue_path = Path(args.queue)
    state_path = Path(args.state)

    queue = _load_json(queue_path, [])
    posted_ids: set[str] = set(_load_json(state_path, []))

    now = datetime.now(timezone.utc)
    published_any = False

    for entry in queue:
        post_id = entry["id"]
        if post_id in posted_ids:
            continue
        publish_at = datetime.fromisoformat(entry["publish_at"]).astimezone(timezone.utc)
        if publish_at > now:
            continue

        text = entry.get("text", "")
        image_url = entry.get("image_url")
        try:
            if image_url:
                remote_id = tc.post_image(user_id, token, image_url, text)
            else:
                remote_id = tc.post_text(user_id, token, text)
        except tc.ThreadsAPIError as exc:
            print(f"[{post_id}] failed: {exc}", file=sys.stderr)
            continue

        print(f"[{post_id}] published as https://www.threads.net/@me/post/{remote_id}")
        posted_ids.add(post_id)
        published_any = True

    if published_any:
        _save_json(state_path, sorted(posted_ids))
    else:
        print("No due posts.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Post to Threads via the official Graph API")
    sub = parser.add_subparsers(dest="command", required=True)

    p_post = sub.add_parser("post", help="Publish a single post immediately")
    p_post.add_argument("text", nargs="?", default="", help="Post text")
    p_post.add_argument("--image-url", help="Publicly reachable image URL for an image post")
    p_post.set_defaults(func=cmd_post)

    p_queue = sub.add_parser("run-queue", help="Publish due posts from a JSON queue file")
    p_queue.add_argument("queue", help="Path to the queue JSON file")
    p_queue.add_argument("--state", default="posted.json", help="Path to the state file tracking already-published ids")
    p_queue.set_defaults(func=cmd_run_queue)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
