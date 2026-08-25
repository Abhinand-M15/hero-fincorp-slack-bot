"""
Shared Slack app credentials. Kept in one place so app.py, slack_client.py,
and standalone scripts don't duplicate them or create circular imports.

Loaded from environment variables (via a local .env file, never committed)
so this file itself is safe to publish. See .env.example for what's needed.
"""
import os
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
