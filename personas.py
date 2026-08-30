"""
Who is who in the Hero FinCorp demo.

The customer was explicit that a collections "agent" is an EXTERNAL PARTNER or
an EXTENDED HFCL WORKFORCE member — a person sitting in a dealership showroom
or attached to a partner collections firm — NOT the end customer and not a
full-time internal HFCL employee. Every label in this demo uses that wording.

Two sample partner agents exist on purpose: the security story is demonstrated
by showing that Agent A cannot see Agent B's accounts, rather than explained.

Slack user IDs are read from the environment so the same code runs against any
workspace. If an ID is missing the demo still works — the bot falls back to the
person's name instead of an @mention, and channel invites for that persona are
skipped.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _env(name):
    value = os.environ.get(name, "").strip()
    return value or None


# ---------- External partner / extended workforce (collections) ----------

PARTNER_AGENTS = {
    "AG-PUNE-01": {
        "agent_id": "AG-PUNE-01",
        "name": "Rakesh Sharma",
        "workforce_type": "External Partner",
        "employer": "Sai Recovery Services (HFCL empanelled partner)",
        "posting": "Kothrud two-wheeler showroom, Pune",
        "cluster": "Pune",
        "channel": "collections-agent-pune-01",
        "slack_id": _env("HFC_AGENT_A_SLACK_ID"),
    },
    "AG-LKO-02": {
        "agent_id": "AG-LKO-02",
        "name": "Imran Qureshi",
        "workforce_type": "Extended HFCL Workforce",
        "employer": "On-roll extended workforce, Lucknow cluster",
        "posting": "Aliganj branch counter, Lucknow",
        "cluster": "Lucknow",
        "channel": "collections-agent-lucknow-02",
        "slack_id": _env("HFC_AGENT_B_SLACK_ID"),
    },
}

# ---------- Whoever is presenting ----------
# The bot creates the journey channels, so without this nobody can see them:
# a private channel is invisible to anyone who is not a member, workspace
# admins included. Presenters are invited to every journey channel but are
# deliberately NOT mapped to a persona, so in relaxed access mode their
# identity follows the channel they are acting in — which is exactly what a
# one-person walkthrough needs. Map a persona instead when you want a real
# second account to be genuinely restricted (see PARTNER_AGENTS above).
PRESENTER_SLACK_IDS = [
    value.strip() for value in os.environ.get("HFC_PRESENTER_SLACK_IDS", "").split(",")
    if value.strip()
]


def is_presenter(slack_id):
    return bool(slack_id) and slack_id in PRESENTER_SLACK_IDS


# ---------- Internal HFCL staff ----------

INTERNAL_STAFF = {
    "MGR-COLL-01": {
        "person_id": "MGR-COLL-01",
        "name": "Priya Raghavan",
        "role": "Collections Manager (internal)",
        "slack_id": _env("HFC_MANAGER_SLACK_ID"),
    },
    "OPS-LEGAL-01": {
        "person_id": "OPS-LEGAL-01",
        "name": "Sandeep Kulkarni",
        "role": "Collections Legal & Ops (internal)",
        "slack_id": _env("HFC_LEGAL_SLACK_ID"),
    },
    "CPA-L1": {
        "person_id": "CPA-L1",
        "name": "Neha Sinha",
        "role": "Credit Manager — CPA Level 1",
        "slack_id": _env("HFC_APPROVER_L1_SLACK_ID"),
    },
    "CPA-L2": {
        "person_id": "CPA-L2",
        "name": "Vikas Bhatia",
        "role": "Credit Head — CPA Level 2",
        "slack_id": _env("HFC_APPROVER_L2_SLACK_ID"),
    },
    "CPA-L3": {
        "person_id": "CPA-L3",
        "name": "Meera Krishnan",
        "role": "Chief Risk Officer — CPA Level 3",
        "slack_id": _env("HFC_APPROVER_L3_SLACK_ID"),
    },
    "ADMIN-01": {
        "person_id": "ADMIN-01",
        "name": "Workspace Administrator",
        "role": "Slack Admin / Information Security",
        "slack_id": _env("HFC_ADMIN_SLACK_ID"),
    },
}

# The Collections Manager oversees every partner agent in this demo. Kept as a
# mapping so a larger rollout can hand different clusters to different managers.
AGENT_TO_MANAGER = {
    "AG-PUNE-01": "MGR-COLL-01",
    "AG-LKO-02": "MGR-COLL-01",
}


def agent_by_slack_id(slack_id):
    """Which partner agent is this Slack user, if any."""
    if not slack_id:
        return None
    for agent in PARTNER_AGENTS.values():
        if agent["slack_id"] and agent["slack_id"] == slack_id:
            return agent
    return None


def agent_by_channel(channel_name):
    for agent in PARTNER_AGENTS.values():
        if agent["channel"] == channel_name:
            return agent
    return None


def staff_by_slack_id(slack_id):
    if not slack_id:
        return None
    for person in INTERNAL_STAFF.values():
        if person["slack_id"] and person["slack_id"] == slack_id:
            return person
    return None


def is_internal(slack_id):
    """Internal HFCL staff — anyone in INTERNAL_STAFF and not a partner agent."""
    return staff_by_slack_id(slack_id) is not None and agent_by_slack_id(slack_id) is None


def mention(person):
    """@mention when we know the Slack ID, plain name when we don't."""
    if not person:
        return "someone"
    slack_id = person.get("slack_id")
    return f"<@{slack_id}>" if slack_id else f"*{person['name']}*"


def manager_for(agent_id):
    return INTERNAL_STAFF.get(AGENT_TO_MANAGER.get(agent_id, ""), INTERNAL_STAFF["MGR-COLL-01"])


def describe(agent):
    """One-line label that makes the external/extended nature unmissable."""
    return f"{agent['name']} — {agent['workforce_type']} · {agent['posting']}"
