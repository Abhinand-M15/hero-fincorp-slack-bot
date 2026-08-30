"""
Block Kit for the security, access-control and data-ownership stories.

These cards exist so the administrator's question — "who can see each message,
record and attachment?" — is answered by showing live workspace state, not by
asserting a policy on a slide.
"""
import access
import channels
import personas
from fmt import human_date, today


def denial_notice(reason):
    """What the person who hit the wall sees. Shown ephemerally."""
    return [
        {"type": "section", "text": {"type": "mrkdwn", "text": reason}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "Checked on the server against the record owner in Salesforce — not just by which channel you are in."}]},
    ]


def access_matrix_card():
    rows = access.access_matrix()
    agent_rows = [r for r in rows if r["visibility"] == channels.AGENT_PRIVATE]
    internal_rows = [r for r in rows if r["visibility"] == channels.INTERNAL]

    def fmt(row):
        return (f"*#{row['channel']}* — _{row['type']}_\n"
                f"   👥 {row['members']}\n"
                f"   🚫 External access: {row['external_access']}")

    text = "Access matrix"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "🔐 Who can see what"}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            "*Partner-agent channels* — one private channel per external agent"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n\n".join(fmt(r) for r in agent_rows)}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            "*Internal-only channels* — no external partner agent is a member of any of these"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n\n".join(fmt(r) for r in internal_rows)}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "🔎  Read live membership from Slack"},
             "style": "primary", "action_id": "security_live_membership"},
            {"type": "button", "text": {"type": "plain_text", "text": "🧪  Run the cross-agent access test"},
             "action_id": "security_cross_agent_test"},
            {"type": "button", "text": {"type": "plain_text", "text": "📎  Where do attachments live?"},
             "action_id": "security_attachment_policy"},
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            f"Access mode: `{access.ACCESS_MODE}` · generated {human_date(today())}"}]},
    ]
    return text, blocks


def live_membership_card(observations):
    """
    `observations` is a list of dicts from access_review.py:
      {channel, exists, private, members (names), unexpected, missing}
    """
    lines = []
    for row in observations:
        if not row["exists"]:
            lines.append(f"• *#{row['channel']}* — not created in this workspace yet")
            continue
        mark = "✅" if not row["unexpected"] else "⚠️"
        privacy = "🔒 private" if row["private"] else "🌐 public"
        lines.append(
            f"{mark} *#{row['channel']}* — {privacy} · {len(row['members'])} members: "
            f"{', '.join(row['members']) or 'bot only'}"
            + (f"\n   ⚠️ unexpected members: {', '.join(row['unexpected'])}" if row["unexpected"] else "")
        )

    clean = all(row["exists"] and not row["unexpected"] for row in observations)
    verdict = ("✅ Live membership matches the access matrix — no external partner agent is in an internal channel."
               if clean else
               "⚠️ Live membership differs from the access matrix. Review the flagged channels above.")

    text = "Live channel membership"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "🔎 Live membership, read from Slack"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}},
        {"type": "section", "text": {"type": "mrkdwn", "text": verdict}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "Pulled with conversations.members at the moment this button was pressed."}]},
    ]
    return text, blocks


def cross_agent_test_card(results):
    """`results` is a list of (description, allowed, reason)."""
    lines = []
    for description, allowed, reason in results:
        mark = "✅ allowed" if allowed else "🚫 blocked"
        first_line = reason.split("\n")[0] if reason else "as expected"
        lines.append(f"*{description}*\n   {mark} — {first_line}")

    text = "Cross-agent access test"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "🧪 Cross-agent access test"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n\n".join(lines)}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "Each line ran the real authorisation check in access.py against the real assignment data."}]},
    ]
    return text, blocks


def attachment_policy_card():
    text = "Attachment containment"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "📎 Where uploaded files end up"}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            "*A payment-proof screenshot from a partner agent*\n"
            "   → completed into that agent's own private channel only\n"
            "   → reachable by that agent, the Collections Manager, and the bot — nobody else\n"
            "   → linked to the loan record in Salesforce, which is where it is retained"}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            "*A customer document on a credit approval*\n"
            "   → completed into `#cpa-approvals-l1` or `#cpa-approvals-l2`, both private and internal\n"
            "   → no external partner agent is a member of either channel, so the file is not reachable by them\n"
            "   → never posted into a shared or partner-facing channel at any point in the flow"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "Slack file access follows the channel the file was shared into. Because the flow only ever shares "
            "into private channels, there is no step at which a document becomes broadly visible."}]},
    ]
    return text, blocks


def sf_sync_card(sync_record, context_line):
    text = f"Salesforce {sync_record.direction} — {sync_record.path.split('?')[0]}"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"{'📤 *Slack → Salesforce*' if sync_record.direction == 'write' else '📥 *Salesforce → Slack*'} · {context_line}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"```{sync_record.as_curl_ish()}```"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            f"{sync_record.status_line()}" + (f" · {sync_record.note}" if sync_record.note else "")}]},
    ]
    return text, blocks


def data_ownership_card():
    text = "Salesforce is the system of record"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "🗄️ Where the data lives"}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            "`Salesforce / LOS`  →  *assignment or request appears in Slack*  →  "
            "*person acts on a form*  →  `written back to Salesforce`  →  *manager sees it*"}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            "• Salesforce stays the system of record for every lead, loan, visit and approval\n"
            "• Slack carries the interaction — the assignment, the form, the decision, the conversation\n"
            "• Every action here writes back; nothing is held only in Slack\n"
            "• No parallel Slack-side database is created or maintained"}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            "*On the 1.5–2 lakh records a day:* those stay in Salesforce. What reaches Slack is the "
            "actionable slice — one agent's visits for one day, one approver's pending decisions. "
            "Slack is not being asked to store or index the book."}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "Every call in this demo is visible in #salesforce-sync-log as it happens."}]},
    ]
    return text, blocks
