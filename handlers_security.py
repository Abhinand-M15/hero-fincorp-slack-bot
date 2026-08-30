"""
Security console handlers — the administrator's and security team's view.

The point of these buttons is that each one produces evidence: live channel
membership read from Slack, real authorisation checks run against real
assignment data, and a live call to Salesforce. Nothing here is a mock-up of a
control; it is the control, reporting on itself.
"""
import access
import access_review
import blocks_security as bs
import collections_journey as journey
import cpa_approvals as cpa
import personas
import sf_bridge
import slack_util as su
from audit_log import log_action


def _identity_for(agent):
    """
    How to act 'as' a sample agent for the test. A real Slack ID when one is
    configured; otherwise the agent's own private channel, which is how the
    relaxed access mode identifies them.
    """
    return agent["slack_id"] or f"simulated:{agent['agent_id']}", agent["channel"]


def run_cross_agent_test():
    """The real checks in access.py, run against the real assignment data."""
    agent_a = personas.PARTNER_AGENTS["AG-PUNE-01"]
    agent_b = personas.PARTNER_AGENTS["AG-LKO-02"]
    a_id, a_channel = _identity_for(agent_a)
    b_id, b_channel = _identity_for(agent_b)

    own_task = journey.assignments_for(agent_a["agent_id"])[0]
    other_task = journey.assignments_for(agent_b["agent_id"])[0]

    results = []

    allowed, reason, _ = access.check_task_access(a_id, own_task["task_id"], a_channel)
    results.append((f"{agent_a['name']} records an outcome on their own `{own_task['loan_id']}`",
                    allowed, reason or "assigned to this agent in Salesforce"))

    allowed, reason, _ = access.check_task_access(a_id, other_task["task_id"], a_channel)
    results.append((f"{agent_a['name']} tries `{other_task['loan_id']}` — assigned to {agent_b['name']}",
                    allowed, reason))

    allowed, reason, _ = access.check_task_access(b_id, own_task["task_id"], b_channel)
    results.append((f"{agent_b['name']} tries `{own_task['loan_id']}` — assigned to {agent_a['name']}",
                    allowed, reason))

    allowed, reason, _ = access.check_internal(a_id, a_channel)
    results.append((f"{agent_a['name']} tries to reach an internal escalation channel", allowed, reason))

    pending = cpa.pending_all()
    if pending:
        allowed, reason, _ = access.check_cpa_decision(a_id, pending[0], a_channel)
        results.append((f"{agent_a['name']} tries to approve `{pending[0].request_id}`", allowed, reason))

    manager = personas.INTERNAL_STAFF["MGR-COLL-01"]
    manager_id = manager["slack_id"] or "simulated:manager"
    allowed, reason, _ = access.check_task_access(manager_id, other_task["task_id"], "collections-control-room")
    results.append((f"{manager['name']} (Collections Manager) reviews {agent_b['name']}'s account",
                    allowed, reason or "internal staff oversee every partner agent"))

    return results


def register(app):

    @app.action("security_live_membership")
    def live_membership(ack, body, client):
        ack()
        channel = body["channel"]["id"]
        client.chat_postMessage(channel=channel, text="Reading live membership from Slack…")
        observations = access_review.review()
        text, blocks = bs.live_membership_card(observations)
        client.chat_postMessage(channel=channel, text=text, blocks=blocks)
        log_action("SECURITY_MEMBERSHIP_REVIEW", "-", su.actor_name(client, body["user"]["id"]),
                   f"{len(observations)} channels checked")

    @app.action("security_cross_agent_test")
    def cross_agent_test(ack, body, client):
        ack()
        results = run_cross_agent_test()
        text, blocks = bs.cross_agent_test_card(results)
        client.chat_postMessage(channel=body["channel"]["id"], text=text, blocks=blocks)
        blocked = sum(1 for _, allowed, _ in results if not allowed)
        log_action("SECURITY_ACCESS_TEST", "-", su.actor_name(client, body["user"]["id"]),
                   f"{blocked} of {len(results)} attempts blocked")

    @app.action("security_attachment_policy")
    def attachment_policy(ack, body, client):
        ack()
        text, blocks = bs.attachment_policy_card()
        client.chat_postMessage(channel=body["channel"]["id"], text=text, blocks=blocks)

    @app.action("sf_probe_now")
    def probe_salesforce(ack, body, client):
        ack()
        channel = body["channel"]["id"]
        ok, detail, instance = sf_bridge.probe()
        status = "✅ *Connected to Salesforce*" if ok else "❌ *Salesforce connection failed*"
        client.chat_postMessage(
            channel=channel, text="Salesforce connection check",
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text":
                    f"{status}\n`{instance or 'no instance URL'}`\n{detail}"}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text":
                    f"JWT Bearer Flow — no password involved. Write mode: `{sf_bridge.WRITE_MODE}`."}]},
            ],
        )
        log_action("SF_PROBE", "-", su.actor_name(client, body["user"]["id"]), detail)
