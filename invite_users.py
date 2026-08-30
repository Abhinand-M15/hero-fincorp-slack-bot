"""
Invite people to channels.

Two different things happen here, and the difference is the whole security
story:

  * the legacy public channels get every human in the workspace, as before;
  * the connected-journey channels get exactly the people the registry in
    channels.py says belong in them — an external partner agent is invited to
    their own channel and to nothing else.

Set the persona Slack IDs in .env first (see .env.example). Anyone without an
ID configured is skipped rather than guessed at.
"""
import channels
import personas
from slack_client import find_channel_id, invite_to_channel

# Everyone in the workspace who should see the original four use cases.
HUMAN_USER_IDS = ["U095ER557AQ", "U0BD8Q8MKJQ", "U09S0DD7M16"]


def _slack_ids(member_keys):
    """The personas the registry allows, plus whoever is presenting."""
    ids = list(personas.PRESENTER_SLACK_IDS)
    for key in member_keys:
        person = personas.PARTNER_AGENTS.get(key) or personas.INTERNAL_STAFF.get(key)
        if person and person.get("slack_id") and person["slack_id"] not in ids:
            ids.append(person["slack_id"])
    return ids


def _invite(name, user_ids, note=""):
    channel_id = find_channel_id(name)
    if not channel_id:
        print(f"  {name}: channel not found")
        return
    if not user_ids:
        print(f"  {name}: nobody to invite {note}")
        return
    result = invite_to_channel(channel_id, user_ids)
    if result and result.get("ok"):
        print(f"  {name}: invited {len(user_ids)} {note}")
    else:
        error = result.get("error") if result else "no response"
        print(f"  {name}: {error} {note}")


if __name__ == "__main__":
    print("Legacy public channels — everyone")
    for channel in channels.LEGACY_CHANNELS:
        _invite(channel["name"], HUMAN_USER_IDS)

    print("\nJourney channels — only the people the registry allows")
    for channel in channels.JOURNEY_CHANNELS:
        member_ids = _slack_ids(channel["members"])
        note = "(set HFC_PRESENTER_SLACK_IDS in .env)" if not member_ids else ""
        _invite(channel["name"], member_ids, note)

    print("\nCheck the result with:  ./venv/bin/python access_review.py")
