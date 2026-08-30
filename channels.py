"""
Channel registry — the single place that says which channel exists, whether it
is private, and who is supposed to be in it.

This registry IS the security demo. `setup_journey.py` creates channels from
it, `invite_users.py` fills membership from it, and `access_review.py` reads
the live workspace back and compares it against this file, so the access
matrix shown to the customer is verified against Slack rather than asserted.

Visibility legend
  agent-private  : one external partner agent + their manager + the bot
  internal       : HFCL staff only — no external partner ever joins
  shared-public  : legacy demo channels from the original 4 use cases
"""
from personas import PARTNER_AGENTS

AGENT_PRIVATE = "agent-private"
INTERNAL = "internal"
SHARED_PUBLIC = "shared-public"


def _agent_channels():
    rows = []
    for agent in PARTNER_AGENTS.values():
        rows.append({
            "name": agent["channel"],
            "private": True,
            "visibility": AGENT_PRIVATE,
            "purpose": f"Assigned collections for {agent['name']} ({agent['workforce_type']}) — visible to this agent and HFCL internal staff only",
            "members": [agent["agent_id"], "MGR-COLL-01"],
        })
    return rows


JOURNEY_CHANNELS = _agent_channels() + [
    {
        "name": "collections-control-room",
        "private": True,
        "visibility": INTERNAL,
        "purpose": "Manager view of every partner agent's progress — agents are not members",
        "members": ["MGR-COLL-01", "OPS-LEGAL-01"],
    },
    {
        "name": "collections-legal-ops",
        "private": True,
        "visibility": INTERNAL,
        "purpose": "Refusals and escalations routed for internal legal/ops decision",
        "members": ["MGR-COLL-01", "OPS-LEGAL-01"],
    },
    {
        "name": "cpa-requests",
        "private": True,
        "visibility": INTERNAL,
        "purpose": "Where a Salesforce/LOS approval request lands and where the requesting officer is told the outcome",
        "members": ["MGR-COLL-01", "CPA-L1"],
    },
    {
        "name": "cpa-approvals-l1",
        "private": True,
        "visibility": INTERNAL,
        "purpose": "CPA Level 1 queue — request detail, justification and supporting attachments",
        "members": ["CPA-L1", "MGR-COLL-01"],
    },
    {
        "name": "cpa-approvals-l2",
        "private": True,
        "visibility": INTERNAL,
        "purpose": "CPA Level 2 / Level 3 queue for higher-value cases",
        "members": ["CPA-L2", "CPA-L3"],
    },
    {
        "name": "cpa-audit-trail",
        "private": True,
        "visibility": INTERNAL,
        "purpose": "Every CPA decision and its Salesforce write-back, in order",
        "members": ["CPA-L1", "CPA-L2", "CPA-L3", "ADMIN-01"],
    },
    {
        "name": "salesforce-sync-log",
        "private": True,
        "visibility": INTERNAL,
        "purpose": "Each read from and write back to Salesforce, shown as the actual REST call",
        "members": ["MGR-COLL-01", "ADMIN-01"],
    },
    {
        "name": "admin-security-console",
        "private": True,
        "visibility": INTERNAL,
        "purpose": "Access matrix canvas and live membership proof for the security team",
        "members": ["ADMIN-01", "MGR-COLL-01"],
    },
]

# Channels created by the original 4 use cases. Left public so the existing
# demo keeps working, but they hold no external-partner-facing data — see
# DEMO_SCRIPT.md for the note on converting these before a customer session.
LEGACY_CHANNELS = [
    {"name": n, "private": False, "visibility": SHARED_PUBLIC, "purpose": p, "members": []}
    for n, p in [
        ("branch-support-escalations", "Knowledge base Q&A"),
        ("collections-bucket2", "Bucket 2 internal queue view"),
        ("collections-bucket3", "Bucket 3 internal queue view"),
        ("collections-npa", "NPA internal queue view"),
        ("legal-escalations", "Legacy legal escalation channel"),
        ("credit-deviation-approvals", "Legacy deviation approval channel"),
        ("lead-swarming", "Inside sales lead swarming"),
        ("field-collections-intake", "Qualified lead handoff"),
    ]
]

ALL_CHANNELS = JOURNEY_CHANNELS + LEGACY_CHANNELS


def by_name(name):
    return next((c for c in ALL_CHANNELS if c["name"] == name), None)


def journey_channel_names():
    return [c["name"] for c in JOURNEY_CHANNELS]


def internal_only_names():
    return [c["name"] for c in JOURNEY_CHANNELS if c["visibility"] == INTERNAL]
