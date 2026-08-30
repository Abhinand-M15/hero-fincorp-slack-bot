"""
Shared Slack app credentials. Kept in one place so app.py, slack_client.py,
and standalone scripts don't duplicate them or create circular imports.

Loaded from environment variables (via a local .env file, never committed)
so this file itself is safe to publish. See .env.example for what's needed.

Missing values are not fatal at import time — offline tools (selftest.py,
demo_assets.py) import modules that reach this file but never call Slack.
Anything that does talk to Slack calls require_tokens() first, so the failure
message says what is missing instead of a bare KeyError.
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")


def require_tokens(need_app_token=True):
    missing = []
    if not SLACK_BOT_TOKEN:
        missing.append("SLACK_BOT_TOKEN")
    if need_app_token and not SLACK_APP_TOKEN:
        missing.append("SLACK_APP_TOKEN")
    if missing:
        print(f"Missing {', '.join(missing)} — copy .env.example to .env and fill in the values "
              f"you were given, then try again.")
        sys.exit(1)
