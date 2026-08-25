"""
Deletes all bot-authored messages from one or more channels — clears out
test clutter before a real demo. Only deletes messages this bot itself
posted (via bot_id match), never anything a human typed.

Usage:
    ./venv/Scripts/python.exe clear_channel.py channel-name-1 channel-name-2 ...
    ./venv/Scripts/python.exe clear_channel.py --all
"""
import sys
import time

from slack_client import api_call, find_channel_id

ALL_CHANNELS = [
    "branch-support-escalations",
    "collections-bucket2",
    "collections-bucket3",
    "collections-npa",
    "legal-escalations",
    "credit-deviation-approvals",
    "lead-warming",
    "field-collections-intake",
]


def clear_channel(channel_id, channel_name):
    deleted = 0
    cursor = None
    while True:
        params = {"channel": channel_id, "limit": 200}
        if cursor:
            params["cursor"] = cursor
        history = api_call("conversations.history", params)
        if not history.get("ok"):
            print(f"  FAILED to read history for #{channel_name}: {history.get('error')}")
            return deleted

        for msg in history.get("messages", []):
            if msg.get("bot_id"):
                result = api_call("chat.delete", {"channel": channel_id, "ts": msg["ts"]})
                if result.get("ok"):
                    deleted += 1
                time.sleep(0.3)  # stay well under rate limits

        cursor = history.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    print(f"  #{channel_name}: deleted {deleted} bot messages")
    return deleted


if __name__ == "__main__":
    args = sys.argv[1:]
    channels = ALL_CHANNELS if (not args or args[0] == "--all") else args

    print(f"Clearing {len(channels)} channel(s)...")
    total = 0
    for name in channels:
        ch_id = find_channel_id(name)
        if ch_id:
            total += clear_channel(ch_id, name)
        else:
            print(f"  #{name}: not found")
    print(f"Done. {total} messages deleted total.")
