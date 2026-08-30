"""
Reads live membership out of Slack and checks it against the access matrix in
channels.py — so the security answer shown to the customer is observed, not
asserted.

    ./venv/bin/python access_review.py            # print the review
    ./venv/bin/python access_review.py --post     # also post it to #admin-security-console
"""
import sys

import channels
import personas
from slack_client import api_call, find_channel_id

_user_names = {}


def _user_label(user_id):
    if user_id in _user_names:
        return _user_names[user_id]

    label = user_id
    if personas.is_presenter(user_id):
        _user_names[user_id] = f"{user_id} (demo presenter)"
        return _user_names[user_id]

    for agent in personas.PARTNER_AGENTS.values():
        if agent["slack_id"] == user_id:
            label = f"{agent['name']} (EXTERNAL)"
            break
    else:
        for person in personas.INTERNAL_STAFF.values():
            if person["slack_id"] == user_id:
                label = person["name"]
                break
        else:
            info = api_call("users.info", {"user": user_id})
            if info.get("ok"):
                user = info["user"]
                if user.get("is_bot"):
                    label = f"{user.get('real_name') or user.get('name')} (bot)"
                else:
                    guest = " (guest)" if user.get("is_restricted") or user.get("is_ultra_restricted") else ""
                    label = f"{user.get('real_name') or user.get('name')}{guest}"

    _user_names[user_id] = label
    return label


def _expected_slack_ids(channel):
    """Slack IDs the registry says belong in this channel."""
    ids = set()
    for member in channel["members"]:
        if member in personas.PARTNER_AGENTS and personas.PARTNER_AGENTS[member]["slack_id"]:
            ids.add(personas.PARTNER_AGENTS[member]["slack_id"])
        elif member in personas.INTERNAL_STAFF and personas.INTERNAL_STAFF[member]["slack_id"]:
            ids.add(personas.INTERNAL_STAFF[member]["slack_id"])
    return ids


def review():
    """One row per journey channel: what Slack actually reports right now."""
    external_ids = {a["slack_id"] for a in personas.PARTNER_AGENTS.values() if a["slack_id"]}
    observations = []

    for channel in channels.JOURNEY_CHANNELS:
        channel_id = find_channel_id(channel["name"])
        row = {"channel": channel["name"], "exists": bool(channel_id), "private": channel["private"],
               "members": [], "member_ids": [], "unexpected": [], "missing": []}

        if not channel_id:
            observations.append(row)
            continue

        info = api_call("conversations.info", {"channel": channel_id})
        if info.get("ok"):
            row["private"] = info["channel"].get("is_private", channel["private"])

        members = api_call("conversations.members", {"channel": channel_id, "limit": 200})
        member_ids = members.get("members", []) if members.get("ok") else []
        row["member_ids"] = member_ids
        row["members"] = [_user_label(m) for m in member_ids]

        expected = _expected_slack_ids(channel)

        if channel["visibility"] == channels.INTERNAL:
            # The check that matters: no external partner agent inside an internal channel.
            row["unexpected"] = [_user_label(m) for m in member_ids if m in external_ids]
        elif channel["visibility"] == channels.AGENT_PRIVATE:
            owner = personas.agent_by_channel(channel["name"])
            other_agents = {a["slack_id"] for a in personas.PARTNER_AGENTS.values()
                            if a["slack_id"] and a["agent_id"] != owner["agent_id"]}
            row["unexpected"] = [_user_label(m) for m in member_ids if m in other_agents]

        row["missing"] = [_user_label(m) for m in expected if m not in member_ids]
        if not row["private"]:
            row["unexpected"].append("channel is PUBLIC — should be private")

        observations.append(row)

    return observations


def print_review(observations):
    print(f"{'channel':32} {'type':9} {'members':>7}  detail")
    print("-" * 100)
    for row in observations:
        if not row["exists"]:
            print(f"{row['channel']:32} {'—':9} {'—':>7}  not created yet — run setup_journey.py")
            continue
        kind = "private" if row["private"] else "PUBLIC"
        detail = ", ".join(row["members"]) or "bot only"
        print(f"{row['channel']:32} {kind:9} {len(row['members']):>7}  {detail}")
        if row["unexpected"]:
            print(f"{'':50}  ⚠️  unexpected: {', '.join(row['unexpected'])}")
        if row["missing"]:
            print(f"{'':50}  •  not yet invited: {', '.join(row['missing'])}")

    clean = all(r["exists"] and not r["unexpected"] for r in observations)
    print("-" * 100)
    print("RESULT:", "no external partner agent is in any internal channel"
          if clean else "review the flagged rows above")
    return clean


if __name__ == "__main__":
    observations = review()
    clean = print_review(observations)

    if "--post" in sys.argv:
        import blocks_security as bs
        from slack_client import post_message

        target = find_channel_id("admin-security-console")
        if target:
            text, blocks = bs.live_membership_card(observations)
            post_message(target, text=text, blocks=blocks)
            print("Posted to #admin-security-console")
        else:
            print("#admin-security-console not found — run setup_journey.py first")

    sys.exit(0 if clean else 1)
