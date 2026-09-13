# Threads RSS Poster Agent

Polls one or more RSS feeds, and posts new entries to Threads via Meta's
Threads API. Already-posted entries are tracked in a local state file so
restarts don't repost old items. Every action (fetch, skip, post, error) is
written to a local log file.

## Setup

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
# edit config.yaml: set your feed(s), keep dry_run: true until you have
# Threads API credentials
```

## Threads API credentials

Not required to try the agent — it runs in dry-run mode without them and
just logs what it would have posted. When you're ready to actually post:

1. Create a Meta app with Threads API access and complete the OAuth flow
   for your account to get a user id and a long-lived access token.
   See: https://developers.facebook.com/docs/threads
2. Export the credentials as environment variables (never commit them to
   `config.yaml` or anywhere in the repo):
   ```bash
   export THREADS_USER_ID=...
   export THREADS_ACCESS_TOKEN=...
   ```
3. Set `dry_run: false` in `config.yaml`.

If `dry_run: false` is set but the environment variables are missing, the
agent logs a warning and falls back to dry-run automatically rather than
failing to post.

## Running

From the repository root:

```bash
# single cycle, useful for testing
python -m agents.threads_rss_poster.main --config agents/threads_rss_poster/config.yaml --once

# run continuously, polling every poll_interval_seconds
python -m agents.threads_rss_poster.main --config agents/threads_rss_poster/config.yaml

# force dry-run regardless of config.yaml
python -m agents.threads_rss_poster.main --config agents/threads_rss_poster/config.yaml --once --dry-run
```

## Configuration (`config.yaml`)

| Key | Description |
| --- | --- |
| `feeds` | List of `{name, url}` RSS/Atom feeds to poll |
| `poll_interval_seconds` | Delay between cycles in continuous mode |
| `max_posts_per_cycle` | Safety cap on posts per cycle, across all feeds |
| `state_file` | Path to the JSON file tracking posted entry ids |
| `log_file` | Path to the log file all actions are written to |
| `dry_run` | When true, logs intended posts instead of calling Threads |
| `post_template` | Post text template; supports `{title} {link} {summary} {source}` |

## Tests

```bash
python -m unittest discover -s agents/threads_rss_poster/tests
```
