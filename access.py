"""
Server-side access control.

Channel membership is the first line of defence, but it is not the only one:
every button click and every form submission is re-checked here against the
record's owner before anything is written or shown. That matters because a
button payload is just data — an external partner agent who obtained one for
another agent's account still cannot act on it.

This module is what lets the demo SHOW the control instead of describing it:
`check_task_access` is what produces the "Access denied" reply when Agent A
reaches for Agent B's account.

Access modes (HFC_ACCESS_MODE)
  strict  — the Slack user must map to a known persona. Use this when the
            demo workspace has a separate account per sample agent.
  relaxed — (default) if the Slack user is unknown, their identity is taken
            from the agent-private channel they are acting in, so a
            single-account workspace can still run the whole journey.
            Record-level ownership is still enforced either way.
"""
import os

from dotenv import load_dotenv

import channels
import collections_journey as journey
import personas

load_dotenv()

ACCESS_MODE = os.environ.get("HFC_ACCESS_MODE", "relaxed").strip().lower()

AGENT = "agent"
INTERNAL = "internal"
UNKNOWN = "unknown"


class Actor:
    def __init__(self, kind, slack_id, agent=None, staff=None, inferred=False):
        self.kind = kind
        self.slack_id = slack_id
        self.agent = agent
        self.staff = staff
        self.inferred = inferred  # identity came from the channel, not the user ID

    @property
    def agent_id(self):
        return self.agent["agent_id"] if self.agent else None

    @property
    def name(self):
        if self.agent:
            return self.agent["name"]
        if self.staff:
            return self.staff["name"]
        return self.slack_id or "unknown user"

    @property
    def label(self):
        if self.agent:
            return f"{self.agent['name']} ({self.agent['workforce_type']})"
        if self.staff:
            return f"{self.staff['name']} — {self.staff['role']}"
        return "unrecognised user"

    def __repr__(self):
        return f"<Actor {self.kind} {self.name}>"


def resolve_actor(slack_user_id, channel_name=None):
    """Who is clicking, and are they an external partner agent or internal staff?"""
    agent = personas.agent_by_slack_id(slack_user_id)
    if agent:
        return Actor(AGENT, slack_user_id, agent=agent)

    staff = personas.staff_by_slack_id(slack_user_id)
    if staff:
        return Actor(INTERNAL, slack_user_id, staff=staff)

    if ACCESS_MODE == "relaxed" and channel_name:
        channel_agent = personas.agent_by_channel(channel_name)
        if channel_agent:
            return Actor(AGENT, slack_user_id, agent=channel_agent, inferred=True)
        if channel_name in channels.internal_only_names():
            return Actor(INTERNAL, slack_user_id, staff=personas.INTERNAL_STAFF["MGR-COLL-01"], inferred=True)

    return Actor(UNKNOWN, slack_user_id)


# ---------- Collections: record-level ownership ----------

def check_task_access(slack_user_id, task_id, channel_name=None):
    """
    Can this user record an outcome against this visit?
    Returns (allowed, reason, actor). `reason` is written for the person who
    hit the wall, so it can be shown to them verbatim.
    """
    actor = resolve_actor(slack_user_id, channel_name)
    task = journey.assignment(task_id)

    if not task:
        return False, f"`{task_id}` is not an assignment in this workspace.", actor

    owner_id = task["agent_id"]
    owner = personas.PARTNER_AGENTS[owner_id]

    if actor.kind == AGENT:
        if actor.agent_id == owner_id:
            return True, "", actor
        return (
            False,
            (f":lock: *Access denied.* `{task['loan_id']}` is assigned to a different "
             f"partner agent ({owner['cluster']} cluster). You can only record outcomes "
             f"for the accounts assigned to you.\n"
             f"_This check runs on the server, so it holds even for a button copied "
             f"from another channel._"),
            actor,
        )

    if actor.kind == INTERNAL:
        return True, "", actor  # HFCL staff oversee every agent

    return (
        False,
        (":lock: *Access denied.* Your Slack account is not mapped to a Hero FinCorp "
         "partner agent or internal role, so no loan records are visible to you."),
        actor,
    )


def visible_assignments(slack_user_id, channel_name=None):
    """The accounts this user is allowed to see — never the full book."""
    actor = resolve_actor(slack_user_id, channel_name)
    if actor.kind == AGENT:
        return journey.assignments_for(actor.agent_id), actor
    if actor.kind == INTERNAL:
        return list(journey.ASSIGNMENTS), actor
    return [], actor


def check_internal(slack_user_id, channel_name=None):
    """Gate for anything an external partner agent must never reach."""
    actor = resolve_actor(slack_user_id, channel_name)
    if actor.kind == INTERNAL:
        return True, "", actor
    return (
        False,
        (":lock: *Internal only.* Escalation notes, other agents' activity and "
         "customer documents stay inside Hero FinCorp. Partner agents see their own "
         "assignments and outcomes only."),
        actor,
    )


# ---------- CPA approvals: approver-level authorisation ----------

def check_cpa_decision(slack_user_id, request, channel_name=None):
    """
    Only the approver the request is currently sitting with may decide it —
    not the previous level, not the requester, and never an external agent.
    """
    actor = resolve_actor(slack_user_id, channel_name)
    expected = request.current_approver()

    if actor.kind == AGENT:
        return False, ":lock: *Access denied.* Credit approvals are an internal Hero FinCorp decision.", actor

    if actor.kind == UNKNOWN and ACCESS_MODE == "strict":
        return False, ":lock: *Access denied.* Your account is not mapped to an approver role.", actor

    if actor.staff and expected and actor.staff["person_id"] != expected["person_id"]:
        return (
            False,
            (f":lock: *Not your approval step.* `{request.request_id}` is currently with "
             f"*{expected['name']}* ({expected['role']}). It will reach you if and when "
             f"it is escalated to your level."),
            actor,
        )

    return True, "", actor


# ---------- Access matrix, used by the canvas and by access_review.py ----------

def access_matrix():
    """
    The intended answer to 'who can see each message, record and attachment'.
    access_review.py checks this against live Slack membership.
    """
    rows = []
    for channel in channels.JOURNEY_CHANNELS:
        if channel["visibility"] == channels.AGENT_PRIVATE:
            agent = personas.agent_by_channel(channel["name"])
            who = f"{agent['name']} (external) + Collections Manager"
            external = f"{agent['name']} only"
        else:
            who = ", ".join(
                personas.INTERNAL_STAFF[m]["name"] for m in channel["members"]
                if m in personas.INTERNAL_STAFF
            )
            external = "None — no external partner agent is a member"
        rows.append({
            "channel": channel["name"],
            "type": "Private" if channel["private"] else "Public",
            "visibility": channel["visibility"],
            "members": who,
            "external_access": external,
            "purpose": channel["purpose"],
        })
    return rows
