"""
Invite the human users in the workspace to all 8 use-case channels,
so they actually show up in the sidebar.
"""
from slack_client import find_channel_id, invite_to_channel

HUMAN_USER_IDS = ["U095ER557AQ", "U0BD8Q8MKJQ", "U09S0DD7M16"]

CHANNEL_NAMES = [
    "branch-support-escalations",
    "collections-bucket2",
    "collections-bucket3",
    "collections-npa",
    "legal-escalations",
    "credit-deviation-approvals",
    "lead-swarming",
    "field-collections-intake",
]

if __name__ == "__main__":
    for name in CHANNEL_NAMES:
        ch_id = find_channel_id(name)
        if ch_id:
            result = invite_to_channel(ch_id, HUMAN_USER_IDS)
            status = "OK" if result and result.get("ok") else result.get("error") if result else "no channel"
            print(f"{name}: {status}")
        else:
            print(f"{name}: channel not found")
