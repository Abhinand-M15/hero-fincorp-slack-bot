"""
One-time (re-runnable) setup for the connected collections + nudge journey, the
CPA approval journey, and the security/data-ownership consoles.

    ./venv/bin/python setup_journey.py            # channels, members, canvases, cards
    ./venv/bin/python setup_journey.py --cards    # only re-post the cards
    ./venv/bin/python setup_journey.py --channels # only create channels and invite people

Safe to re-run: channels that exist are skipped, invites that already happened
are ignored, and canvases are only created when the channel has none.
"""
import sys

from slack_sdk import WebClient

import blocks_cpa as bc
import blocks_journey as bj
import blocks_security as bs
import channels as channel_registry
import collections_journey as journey
import cpa_approvals as cpa
import handlers_cpa
import journey_state
import personas
import slack_util as su
from app_config import SLACK_BOT_TOKEN, require_tokens
from canvas_content_architecture import ARCHITECTURE_CANVAS_MARKDOWN
from canvas_content_security import SECURITY_CANVAS_MARKDOWN
from slack_client import api_call, create_channel, find_channel_id, invite_to_channel

require_tokens(need_app_token=False)
client = WebClient(token=SLACK_BOT_TOKEN)


def _slack_ids(member_keys):
    """The personas the registry allows, plus whoever is presenting."""
    ids = list(personas.PRESENTER_SLACK_IDS)
    for key in member_keys:
        person = personas.PARTNER_AGENTS.get(key) or personas.INTERNAL_STAFF.get(key)
        if person and person.get("slack_id") and person["slack_id"] not in ids:
            ids.append(person["slack_id"])
    return ids


def create_channels_and_members():
    print("\n== Channels ==")
    for channel in channel_registry.JOURNEY_CHANNELS:
        channel_id = create_channel(channel["name"], is_private=channel["private"])
        if not channel_id:
            continue
        members = _slack_ids(channel["members"])
        if members:
            result = invite_to_channel(channel_id, members)
            if result and not result.get("ok") and result.get("error") != "already_in_channel":
                print(f"      invite -> {result.get('error')}")
        else:
            print(f"      ⚠️  nobody to invite to #{channel['name']} — set HFC_PRESENTER_SLACK_IDS in .env, "
                  f"or you will not be able to see this channel")


def create_canvases():
    print("\n== Canvases ==")
    admin_channel = find_channel_id("admin-security-console")
    sync_channel = find_channel_id("salesforce-sync-log")

    if admin_channel:
        result = api_call("canvases.create", {
            "title": "Access & Security — Who Can See What",
            "document_content": {"type": "markdown",
                                 "markdown": SECURITY_CANVAS_MARKDOWN.format(admin_channel=admin_channel)},
            "channel_id": admin_channel,
        })
        print("  security canvas:", result.get("canvas_id") if result.get("ok") else result.get("error"))

    if sync_channel:
        result = api_call("canvases.create", {
            "title": "Salesforce & Slack — Where the Data Lives",
            "document_content": {"type": "markdown",
                                 "markdown": ARCHITECTURE_CANVAS_MARKDOWN.format(sync_channel=sync_channel)},
            "channel_id": sync_channel,
        })
        print("  architecture canvas:", result.get("canvas_id") if result.get("ok") else result.get("error"))


def post_agent_day_cards():
    print("\n== Partner agent day cards ==")
    for agent in personas.PARTNER_AGENTS.values():
        assignments = journey.assignments_for(agent["agent_id"])
        progress = journey.progress(agent["agent_id"])
        text, blocks = bj.agent_day_card(agent, assignments, progress)
        result = su.post_to(client, agent["channel"], text, blocks)
        if result and result.get("ok"):
            journey_state.remember_card(f"day:{agent['agent_id']}", result["channel"], result["ts"])
            print(f"  #{agent['channel']}: {len(assignments)} visits for {agent['name']}")


def post_manager_board():
    print("\n== Manager control room ==")
    rows = [(agent, journey.progress(agent["agent_id"])) for agent in personas.PARTNER_AGENTS.values()]
    text, blocks = bj.activity_board(rows)
    result = su.post_to(client, "collections-control-room", text, blocks)
    if result and result.get("ok"):
        journey_state.remember_card("activity_board", result["channel"], result["ts"])
        print("  activity board posted")


def post_cpa_requests():
    print("\n== CPA approvals ==")
    for request in cpa.all_requests():
        if request.status != cpa.PENDING:
            continue
        handlers_cpa.announce_intake(client, request)
        handlers_cpa.post_request_to_approver(client, request)
        approver = request.current_approver()
        print(f"  {request.request_id} -> L{request.current_level()}/{request.total_levels()} "
              f"{approver['name']} (#{request.channel_for_current_level()})")

    for channel_name, person_key, levels in [
        ("cpa-approvals-l1", "CPA-L1", ["CPA-L1"]),
        ("cpa-approvals-l2", "CPA-L2", ["CPA-L2", "CPA-L3"]),
    ]:
        waiting = [r for r in cpa.pending_all()
                   if r.current_approver() and r.current_approver()["person_id"] in levels]
        text, blocks = bc.cpa_inbox_card(personas.INTERNAL_STAFF[person_key], waiting)
        su.post_to(client, channel_name, text, blocks)


def post_consoles():
    print("\n== Security & data ownership consoles ==")
    text, blocks = bs.access_matrix_card()
    su.post_to(client, "admin-security-console", text, blocks)

    text, blocks = bs.data_ownership_card()
    blocks.append({"type": "actions", "elements": [
        {"type": "button", "text": {"type": "plain_text", "text": "🔌  Check the Salesforce connection now"},
         "style": "primary", "action_id": "sf_probe_now"}]})
    su.post_to(client, "salesforce-sync-log", text, blocks)
    print("  consoles posted")


if __name__ == "__main__":
    args = set(sys.argv[1:])
    do_all = not args or "--all" in args

    if do_all or "--channels" in args:
        create_channels_and_members()
    if do_all or "--canvases" in args:
        create_canvases()
    if do_all or "--cards" in args:
        post_agent_day_cards()
        post_manager_board()
        post_cpa_requests()
        post_consoles()

    print("\nDone. Start the bot with:  ./venv/bin/python app.py")
