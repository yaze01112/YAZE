# Threads Auto-Post

Scripts for posting to [Threads](https://threads.net) using Meta's official
Threads Graph API. This does **not** create a Threads account for you and
does not automate the Threads app/website — it calls the real API that Meta
publishes for developers, using credentials you generate yourself.

## 1. One-time setup (you do this in your browser)

1. Create a Threads account normally in the app if you don't have one.
2. Go to [developers.facebook.com](https://developers.facebook.com/) and
   create a Meta Developer app (type: "Other" -> add the "Threads Use Case").
3. In the app's Threads API settings, add your Threads account as a tester
   and accept the invite from your Threads account (Settings ->
   Website permissions, on mobile).
4. Generate a short-lived user access token for your account with the
   `threads_basic` and `threads_content_publish` scopes (the Threads API
   settings page has a "Generate Access Token" button for this).
5. Exchange it for a long-lived token (valid ~60 days, refreshable):

   ```bash
   python -c "
   import threads_client as tc
   print(tc.exchange_long_lived_token('YOUR_APP_SECRET', 'YOUR_SHORT_LIVED_TOKEN'))
   "
   ```

   This returns `{"access_token": "...", "expires_in": ...}`. Also note your
   Threads user id, returned by `GET https://graph.threads.net/v1.0/me?access_token=...`.

6. Copy `.env.example` to `.env` and fill in `THREADS_USER_ID` and
   `THREADS_ACCESS_TOKEN`.

Before the token expires (every ~55 days), refresh it:

```bash
python -c "
import threads_client as tc
print(tc.refresh_long_lived_token('YOUR_CURRENT_LONG_LIVED_TOKEN'))
"
```

and update `.env` with the new token.

## 2. Install

```bash
cd threads-autopost
pip install -r requirements.txt
```

## 3. Post immediately

```bash
python autopost.py post "Hello from my script!"
python autopost.py post "Look at this" --image-url https://example.com/pic.jpg
```

## 4. Scheduled auto-posting

Write posts into a queue file (see `queue.example.json`), each with a unique
`id`, the `text`, an optional `image_url`, and `publish_at` (ISO-8601, UTC).
Then run:

```bash
python autopost.py run-queue queue.json --state posted.json
```

This publishes any entries whose `publish_at` has passed and haven't been
posted yet (tracked in `posted.json`), and skips the rest. To make posting
actually happen on schedule, invoke this command periodically, e.g. via cron:

```cron
*/15 * * * * cd /path/to/threads-autopost && python autopost.py run-queue queue.json --state posted.json >> autopost.log 2>&1
```

## Notes

- Rate limits: Meta currently allows up to 250 posts per 24 hours per user
  via this API (subject to change — check the official docs).
- Keep `.env`, `queue.json`, and `posted.json` out of version control if
  they contain real tokens or unpublished content — they're already covered
  by `.gitignore` in this folder.
- Official docs: https://developers.facebook.com/docs/threads
