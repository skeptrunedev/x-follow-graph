#!/usr/bin/env python3
"""Pull the authenticated user's following list via OAuth 2.0.

Env vars:
    X_CLIENT_ID, X_CLIENT_SECRET, X_ACCESS_TOKEN, X_REFRESH_TOKEN

Access tokens expire after ~2h. On 401 the script refreshes using
X_REFRESH_TOKEN and prints the new pair to stderr so you can update bashrc.

Usage:
    ./x-following.py [following|followers] > out.json
"""

import json
import os
import sys
import time

import requests


def env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"missing env var: {name}")
    return value


CLIENT_ID = env("X_CLIENT_ID")
CLIENT_SECRET = env("X_CLIENT_SECRET")
ACCESS_TOKEN = env("X_ACCESS_TOKEN")
REFRESH_TOKEN = env("X_REFRESH_TOKEN")

TOKEN_URL = "https://api.x.com/2/oauth2/token"
API = "https://api.x.com/2"
USER_FIELDS = (
    "id,username,name,description,verified,verified_type,affiliation,"
    "public_metrics,verified_followers_count,created_at,location,entities,"
    "most_recent_tweet_id,pinned_tweet_id,connection_status"
)


class Tokens:
    def __init__(self, access: str, refresh: str) -> None:
        self.access = access
        self.refresh = refresh

    def refresh_now(self) -> None:
        r = requests.post(
            TOKEN_URL,
            auth=(CLIENT_ID, CLIENT_SECRET),
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh,
                "client_id": CLIENT_ID,
            },
            timeout=30,
        )
        if not r.ok:
            sys.exit(f"refresh failed: {r.status_code}\n{r.text}")
        body = r.json()
        self.access = body["access_token"]
        self.refresh = body.get("refresh_token", self.refresh)
        print(
            "refreshed tokens — update ~/.bashrc:\n"
            f'  export X_ACCESS_TOKEN="{self.access}"\n'
            f'  export X_REFRESH_TOKEN="{self.refresh}"',
            file=sys.stderr,
        )


def api_get(session: requests.Session, tokens: Tokens, path: str, params: dict | None = None) -> dict:
    refreshed = False
    while True:
        r = session.get(
            f"{API}{path}",
            headers={"Authorization": f"Bearer {tokens.access}"},
            params=params,
            timeout=30,
        )
        if r.status_code == 401 and not refreshed:
            print("access token rejected; refreshing", file=sys.stderr)
            tokens.refresh_now()
            refreshed = True
            continue
        if r.status_code == 429:
            reset = int(r.headers.get("x-rate-limit-reset", "0"))
            wait = max(reset - int(time.time()), 15)
            print(f"rate limited; sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        if not r.ok:
            sys.exit(f"{r.status_code} {r.url}\n{r.text}")
        return r.json()


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "following"
    if mode not in ("following", "followers"):
        sys.exit(f"unknown mode {mode!r}; use 'following' or 'followers'")

    tokens = Tokens(ACCESS_TOKEN, REFRESH_TOKEN)
    session = requests.Session()

    me = api_get(session, tokens, "/users/me")["data"]
    print(f"authenticated as @{me['username']} (id={me['id']}); fetching {mode}", file=sys.stderr)

    out: list[dict] = []
    params: dict = {"max_results": 1000, "user.fields": USER_FIELDS}
    while True:
        resp = api_get(session, tokens, f"/users/{me['id']}/{mode}", params=params)
        out.extend(resp.get("data", []))
        print(f"  fetched {len(out)} so far", file=sys.stderr)
        next_token = resp.get("meta", {}).get("next_token")
        if not next_token:
            break
        params["pagination_token"] = next_token

    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    print(f"done: {len(out)} accounts", file=sys.stderr)


if __name__ == "__main__":
    main()
