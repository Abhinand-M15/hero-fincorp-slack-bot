"""
Thin wrapper around Slack Web API calls used by the bot and by
setup/simulation scripts. Uses the bot token already configured in app_config.py.
"""
import requests

from app_config import SLACK_BOT_TOKEN

BASE = "https://slack.com/api"


def _headers():
    return {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }


def api_call(method, payload=None, files=None):
    if files:
        headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        r = requests.post(f"{BASE}/{method}", headers=headers, data=payload, files=files)
    else:
        r = requests.post(f"{BASE}/{method}", headers=_headers(), json=payload or {})
    result = r.json()
    if not result.get("ok"):
        print(f"SLACK API ERROR [{method}]: {result.get('error')} | {result}")
    return result


def find_channel_id(name):
    """Look up an existing channel's ID by name (without '#')."""
    cursor = None
    while True:
        params = {"types": "public_channel,private_channel", "limit": 200}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(f"{BASE}/conversations.list", headers=_headers(), params=params)
        data = r.json()
        if not data.get("ok"):
            print("SLACK API ERROR [conversations.list]:", data.get("error"))
            return None
        for ch in data.get("channels", []):
            if ch["name"] == name:
                return ch["id"]
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            return None


def create_channel(name, is_private=False):
    existing = find_channel_id(name)
    if existing:
        print(f"SKIP  #{name} (already exists: {existing})")
        return existing
    result = api_call("conversations.create", {"name": name, "is_private": is_private})
    if result.get("ok"):
        channel_id = result["channel"]["id"]
        print(f"OK    #{name} -> {channel_id}")
        return channel_id
    return None


def post_message(channel, text=None, blocks=None, thread_ts=None):
    payload = {"channel": channel}
    if text:
        payload["text"] = text
    if blocks:
        payload["blocks"] = blocks
    if thread_ts:
        payload["thread_ts"] = thread_ts
    return api_call("chat.postMessage", payload)


def update_message(channel, ts, text=None, blocks=None):
    payload = {"channel": channel, "ts": ts}
    if text:
        payload["text"] = text
    if blocks:
        payload["blocks"] = blocks
    return api_call("chat.update", payload)


def invite_to_channel(channel_id, user_ids):
    user_ids = [u for u in user_ids if u]
    if not user_ids:
        return None
    return api_call("conversations.invite", {"channel": channel_id, "users": ",".join(user_ids)})


def lookup_user_by_email(email):
    if not email:
        return None
    r = requests.get(f"{BASE}/users.lookupByEmail", headers=_headers(), params={"email": email})
    data = r.json()
    if data.get("ok"):
        return data["user"]["id"]
    return None


if __name__ == "__main__":
    result = api_call("auth.test")
    if result.get("ok"):
        print("AUTH SUCCESS")
        print("team:", result.get("team"))
        print("bot user:", result.get("user"))
        print("bot id:", result.get("user_id"))
    else:
        print("AUTH FAILED:", result.get("error"))
