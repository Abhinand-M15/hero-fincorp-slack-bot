"""
One-time setup: create the channels used by the original 4 Hero FinCorp use
cases. The connected-journey channels (per-agent private channels, the manager
control room, the CPA approval queues and the security console) are created by
setup_journey.py instead, because they are private and need membership.

Safe to re-run — create_channel() skips channels that already exist.
"""
import channels
from slack_client import create_channel

if __name__ == "__main__":
    for channel in channels.LEGACY_CHANNELS:
        create_channel(channel["name"], is_private=channel["private"])

    print("\nFor the connected journeys (private channels), run:  ./venv/bin/python setup_journey.py")
