"""
Put the workspace back to a clean starting position before a demo.

  1. deletes every message this bot posted in the journey channels
  2. cancels any reminders it had scheduled
  3. clears the local day state (progress, nudges sent, card positions)
  4. re-posts the opening cards

    ./venv/bin/python reset_demo.py            # full reset and re-post
    ./venv/bin/python reset_demo.py --keep-cards   # clear state only, post nothing
"""
import sys
import time

import channels
import journey_state
from app_config import require_tokens
from slack_client import api_call, find_channel_id

require_tokens(need_app_token=False)


def clear_messages(channel_id, name):
    deleted = 0
    cursor = None
    while True:
        params = {"channel": channel_id, "limit": 200}
        if cursor:
            params["cursor"] = cursor
        history = api_call("conversations.history", params)
        if not history.get("ok"):
            print(f"  #{name}: cannot read history — {history.get('error')}")
            return deleted
        for message in history.get("messages", []):
            if message.get("bot_id"):
                if api_call("chat.delete", {"channel": channel_id, "ts": message["ts"]}).get("ok"):
                    deleted += 1
                time.sleep(0.3)
        cursor = history.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return deleted


def cancel_scheduled(channel_id, name):
    listing = api_call("chat.scheduledMessages.list", {"channel": channel_id, "limit": 200})
    cancelled = 0
    for message in listing.get("scheduled_messages", []):
        if api_call("chat.deleteScheduledMessage",
                    {"channel": channel_id, "scheduled_message_id": message["id"]}).get("ok"):
            cancelled += 1
    return cancelled


if __name__ == "__main__":
    print("Resetting the journey channels…")
    for channel in channels.JOURNEY_CHANNELS:
        channel_id = find_channel_id(channel["name"])
        if not channel_id:
            print(f"  #{channel['name']}: not created yet")
            continue
        deleted = clear_messages(channel_id, channel["name"])
        cancelled = cancel_scheduled(channel_id, channel["name"])
        print(f"  #{channel['name']}: {deleted} messages deleted"
              + (f", {cancelled} scheduled reminders cancelled" if cancelled else ""))

    journey_state.reset()
    print("Local day state cleared.")

    if "--keep-cards" not in sys.argv:
        import setup_journey
        setup_journey.post_agent_day_cards()
        setup_journey.post_manager_board()
        setup_journey.post_cpa_requests()
        setup_journey.post_consoles()

    print("\nReady. Start the bot with:  ./venv/bin/python app.py")
