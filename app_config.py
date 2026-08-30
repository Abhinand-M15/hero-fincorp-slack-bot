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

# macOS python.org builds ship without a CA bundle wired into OpenSSL, so
# slack_sdk (which talks over urllib) fails certificate verification while
# requests, which carries its own bundle, works fine. Point OpenSSL at the
# same bundle rather than making anyone run Install Certificates.command.
# Harmless everywhere else, and never overrides a bundle already chosen.
if not os.environ.get("SSL_CERT_FILE"):
    try:
        import certifi

        os.environ["SSL_CERT_FILE"] = certifi.where()
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
    except ImportError:
        pass

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
