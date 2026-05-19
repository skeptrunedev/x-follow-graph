# x-follow-graph

Pull your X following / followers list via the X API v2, enriched with affiliation, location, `connection_status` (mutuals), and last-tweet activity.

## Output

JSON array of users, one per row, with these fields:

```
id, username, name, description, verified, verified_type, affiliation,
public_metrics, verified_followers_count, created_at, location, entities,
most_recent_tweet_id, pinned_tweet_id, connection_status
```

`connection_status` is what makes this useful — values include `"following"`, `"followed_by"`, `"muting"`, `"blocking"`. Intersecting gives you mutuals in one pass.

## Requirements

- Python 3.10+
- `pip install requests`
- A paid X API tier (Basic or higher) — the `/2/users/:id/following` and `/2/users/:id/followers` endpoints are not available on the free tier.

## X API app setup

X funnels everyone to OAuth 2.0 PKCE now; OAuth 1.0a still works for some apps but the new portal hides it.

1. **Sign in to https://console.x.com** with the X account you want to query.
2. **Create a Project + App** if you don't have one. The App is what gets API credentials.
3. **App → User authentication settings → Set up**:
   - **App permissions**: `Read` (sufficient for reading followers/following). Pick `Read and write` only if you want to extend the script to actually unfollow.
   - **Type of App**: `Native App` or `Automated App or bot` — *not* Web App. This keeps confidential-client auth simple.
   - **Callback URI**: any localhost URL with a high ephemeral port works, e.g. `http://localhost:51847/callback`. It is never actually hit when you use portal-generated tokens.
   - Website / Org / TOS / Privacy URLs: any valid URLs (they're not user-facing for a personal script).
4. **App → Keys and tokens**:
   - Note your **OAuth 2.0 Client ID** and **Client Secret**.
   - Under **Authentication Tokens**, generate **Access Token and Refresh Token** (OAuth 2.0). Copy them immediately — they only show once.

If you regenerate the access token *after* changing app permissions, regenerate again; tokens are bound to the permissions in effect when they were issued.

## Environment variables

Add to `~/.bashrc` (or your shell equivalent):

```bash
export X_CLIENT_ID="..."
export X_CLIENT_SECRET="..."
export X_ACCESS_TOKEN="..."
export X_REFRESH_TOKEN="..."
```

`source ~/.bashrc` to load.

## Run

```bash
./x-following.py following > following.json    # who you follow
./x-following.py followers > followers.json    # who follows you
```

Progress goes to stderr; the JSON array is on stdout. The script paginates 1000 users per page and sleeps on `429` until the `x-rate-limit-reset` header.

## Token refresh

OAuth 2.0 access tokens expire after ~2 hours. On `401` the script automatically refreshes using `X_REFRESH_TOKEN` and prints the new pair to stderr:

```
refreshed tokens — update ~/.bashrc:
  export X_ACCESS_TOKEN="..."
  export X_REFRESH_TOKEN="..."
```

Paste those over the old values. X rotates refresh tokens on each refresh, so the old refresh token will stop working once you've used it.

## Tips

- Decode `most_recent_tweet_id` as a Twitter snowflake to get the exact last-tweet timestamp without burning more API calls:
  ```python
  timestamp_ms = (int(tweet_id) >> 22) + 1288834974657
  ```
- The `/followers` endpoint has a tighter rate limit than `/following` on most tiers; expect a wait partway through a large pull.
