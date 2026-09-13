from __future__ import annotations

import argparse
import logging
import sys

from .config import load_config
from .poster_agent import PosterAgent
from .state_store import StateStore
from .threads_client import ThreadsClient


def _setup_logging(log_file: str) -> None:
    # Console handler makes runs visible in the GitHub Actions log without
    # needing to open the (gitignored, ephemeral-per-run) log file.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def build_agent(config_path: str, dry_run_override: bool | None = None) -> PosterAgent:
    config = load_config(config_path)
    if dry_run_override is not None:
        config.dry_run = dry_run_override

    _setup_logging(config.log_file)
    state = StateStore(config.state_file)

    threads_client = None
    if not config.dry_run:
        if not config.threads_user_id or not config.threads_access_token:
            logging.getLogger("threads_rss_poster").warning(
                "THREADS_USER_ID / THREADS_ACCESS_TOKEN not set; falling back to dry-run mode"
            )
            config.dry_run = True
        else:
            threads_client = ThreadsClient(config.threads_user_id, config.threads_access_token)

    return PosterAgent(config, state, threads_client)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch RSS feeds and post new items to Threads")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML file")
    parser.add_argument("--once", action="store_true", help="Run a single cycle instead of looping forever")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be posted without calling the Threads API",
    )
    args = parser.parse_args(argv)

    agent = build_agent(args.config, dry_run_override=True if args.dry_run else None)

    if args.once:
        posted = agent.run_once()
        print(f"Posted {posted} new item(s). See the log file for details.")
    else:
        agent.run_forever()

    return 0


if __name__ == "__main__":
    sys.exit(main())
