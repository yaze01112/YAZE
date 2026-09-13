"""CLI for posting to Threads, either a single post now or a scheduled queue.

Usage:
    python autopost.py post "Hello from my script!"
    python autopost.py post "Check this out" --image-url https://example.com/pic.jpg
    python autopost.py run-queue queue.json --state posted.json
    python autopost.py generate-post "today's dev update" --post-now
    python autopost.py generate-batch topics.txt --queue queue.json --interval-hours 24
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
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


def cmd_generate(args: argparse.Namespace) -> None:
    from content_generator import generate_post

    text = generate_post(args.topic, args.style or "")
    print(f"Generated ({len(text)} chars):\n{text}\n")

    if args.post_now:
        user_id, token = _credentials()
        post_id = tc.post_text(user_id, token, text)
        print(f"Published: https://www.threads.net/@me/post/{post_id}")
    elif args.add_to_queue:
        queue_path = Path(args.add_to_queue)
        queue = _load_json(queue_path, [])
        entry_id = args.id or f"gen-{int(datetime.now(timezone.utc).timestamp())}"
        publish_at = args.publish_at or datetime.now(timezone.utc).isoformat()
        queue.append({"id": entry_id, "text": text, "publish_at": publish_at})
        _save_json(queue_path, queue)
        print(f"Added to queue as '{entry_id}' (publish_at={publish_at})")
    else:
        print("Not published or queued (pass --post-now or --add-to-queue).")


def cmd_generate_batch(args: argparse.Namespace) -> None:
    """Generate one post per line in a topics file and schedule them into a queue."""
    from content_generator import generate_post

    topics = [
        line.strip()
        for line in Path(args.topics_file).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not topics:
        sys.exit(f"No topics found in {args.topics_file}")

    start = (
        datetime.fromisoformat(args.start)
        if args.start
        else datetime.now(timezone.utc)
    )
    interval = timedelta(hours=args.interval_hours)

    queue_path = Path(args.queue)
    queue = _load_json(queue_path, [])
    existing_ids = {entry["id"] for entry in queue}

    for i, topic in enumerate(topics):
        text = generate_post(topic, args.style or "")
        publish_at = start + i * interval
        entry_id = f"gen-{publish_at.strftime('%Y%m%dT%H%M%S')}-{i}"
        if entry_id in existing_ids:
            continue
        queue.append({"id": entry_id, "text": text, "publish_at": publish_at.isoformat()})
        print(f"[{entry_id}] {publish_at.isoformat()} <- {topic!r}\n  {text}\n")

    _save_json(queue_path, queue)
    print(f"Wrote {len(topics)} posts into {queue_path}")


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

    p_gen = sub.add_parser(
        "generate-post", help="Generate post text with Claude, then publish or queue it"
    )
    p_gen.add_argument("topic", help="Topic or brief for the post")
    p_gen.add_argument("--style", help="Optional tone/style guidance")
    p_gen.add_argument("--post-now", action="store_true", help="Publish immediately after generating")
    p_gen.add_argument("--add-to-queue", help="Path to a queue JSON file to append the generated post to")
    p_gen.add_argument("--publish-at", help="ISO-8601 UTC timestamp for the queued post (default: now)")
    p_gen.add_argument("--id", help="Custom id for the queued post entry")
    p_gen.set_defaults(func=cmd_generate)

    p_batch = sub.add_parser(
        "generate-batch",
        help="Generate one post per topic (one per line in a file) and schedule them into a queue",
    )
    p_batch.add_argument("topics_file", help="Text file with one topic per line")
    p_batch.add_argument("--queue", required=True, help="Path to the queue JSON file to append to")
    p_batch.add_argument("--style", help="Optional tone/style guidance applied to every post")
    p_batch.add_argument(
        "--interval-hours", type=float, default=24.0, help="Hours between each scheduled post"
    )
    p_batch.add_argument(
        "--start", help="ISO-8601 UTC timestamp for the first post (default: now)"
    )
    p_batch.set_defaults(func=cmd_generate_batch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
