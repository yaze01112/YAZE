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

## Running on a schedule with GitHub Actions

`.github/workflows/threads-rss-poster.yml` runs this agent automatically
once an hour (configurable via the cron expression in that file). It:

1. Checks out the repo and installs dependencies
2. Runs one cycle (`--once`) using `agents/threads_rss_poster/config.yaml`,
   with `THREADS_USER_ID` / `THREADS_ACCESS_TOKEN` supplied as GitHub
   Actions secrets (never stored in the repo)
3. Commits `state.json` back to the repo if it changed, so the next
   scheduled run (a fresh container with no memory of the last one) still
   knows what was already posted

Setup, once, in the GitHub web UI (no local machine needed):

1. Go to the repo on GitHub → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**
2. Add a secret named `THREADS_USER_ID` with your Threads user id
3. Add a secret named `THREADS_ACCESS_TOKEN` with your Threads access token
4. Edit `agents/threads_rss_poster/config.yaml` in the repo: replace the
   placeholder feed with the real RSS feed(s), and once you've confirmed
   the token works, set `dry_run: false`
5. Scheduled (`cron`) triggers only fire on the repo's default branch, but
   you can test immediately on any branch from the **Actions** tab: select
   "Threads RSS Poster" → **Run workflow**

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
