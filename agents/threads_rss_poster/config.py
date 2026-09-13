from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml


@dataclass
class FeedConfig:
    name: str
    url: str


@dataclass
class AgentConfig:
    feeds: list[FeedConfig] = field(default_factory=list)
    poll_interval_seconds: int = 900
    max_posts_per_cycle: int = 3
    state_file: str = "state.json"
    log_file: str = "agent.log"
    post_template: str = "{title}\n\n{link}"
    dry_run: bool = True
    threads_user_id: str | None = None
    threads_access_token: str | None = None


def _clean_env(name: str) -> str | None:
    """Read an env var and strip stray whitespace/newlines a copy-paste into
    GitHub Secrets can easily introduce - a trailing newline would otherwise
    silently corrupt every URL built from it."""
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def load_config(path: str) -> AgentConfig:
    """Load agent configuration from a YAML file.

    Threads credentials are intentionally read from environment variables
    (THREADS_USER_ID / THREADS_ACCESS_TOKEN) rather than the YAML file, so
    secrets never need to be committed alongside the feed configuration.
    """
    with open(path, "r", encoding="utf-8") as config_file:
        raw = yaml.safe_load(config_file) or {}

    feeds = [
        FeedConfig(name=item["name"], url=item["url"])
        for item in raw.get("feeds", [])
    ]

    return AgentConfig(
        feeds=feeds,
        poll_interval_seconds=int(raw.get("poll_interval_seconds", 900)),
        max_posts_per_cycle=int(raw.get("max_posts_per_cycle", 3)),
        state_file=raw.get("state_file", "state.json"),
        log_file=raw.get("log_file", "agent.log"),
        post_template=raw.get("post_template", "{title}\n\n{link}"),
        dry_run=bool(raw.get("dry_run", True)),
        threads_user_id=_clean_env("THREADS_USER_ID"),
        threads_access_token=_clean_env("THREADS_ACCESS_TOKEN"),
    )
