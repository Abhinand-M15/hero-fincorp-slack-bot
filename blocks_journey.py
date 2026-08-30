"""
Block Kit for the collections journey — everything the external partner agent
and their manager actually look at.

Written from each person's point of view, because that is how the demo is
presented: the agent's card answers "what do I need to do today", the manager's
board answers "who has not started or finished".
"""
import json

import collections_journey as journey
import journey_state
import personas
from fmt import human_date, human_time, rupees, today

OUTCOME_OPTIONS = [
    {"text": {"type": "plain_text", "text": f"{journey.OUTCOME_EMOJI[k]} {v}"}, "value": k}
    for k, v in journey.OUTCOME_LABELS.items()
]
OUTCOME_BY_VALUE = {o["value"]: o for o in OUTCOME_OPTIONS}


def _meta(channel_id, agent_id):
    return json.dumps({"channel": channel_id, "agent": agent_id})


def read_meta(private_metadata):
    try:
        return json.loads(private_metadata or "{}")
    except json.JSONDecodeError:
        return {}


# ---------- The agent's own day ----------

def agent_day_card(agent, assignments, progress):
    total_overdue = sum(a["overdue"] for a in assignments)
    lines = []
    logged = progress["logged"]
    for item in assignments:
        lines.append(
            f"• *{item['borrower']}* — `{item['loan_id']}`\n"
            f"   {item['product']} · {item['bucket']} · {item['dpd']} DPD · "
            f"{rupees(item['overdue'])} overdue · {item['locality']}"
        )

    text = f"Your collections for {human_date(today())}"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"📍 Your visits for {human_date(today())}"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            f"*{agent['name']}* · {agent['workforce_type']} · {agent['posting']} · Agent ID `{agent['agent_id']}`"}]},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*{len(assignments)} accounts assigned* · {rupees(total_overdue)} total overdue · "
            f"{logged} recorded so far"}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines) if lines else "Nothing assigned today."}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "▶️  Start my day"},
             "style": "primary", "value": agent["agent_id"], "action_id": "agent_start_day"},
            {"type": "button", "text": {"type": "plain_text", "text": "📝  Record visit outcome"},
             "value": agent["agent_id"], "action_id": "open_outcome_modal"},
            {"type": "button", "text": {"type": "plain_text", "text": "📊  My progress"},
             "value": agent["agent_id"], "action_id": "agent_progress"},
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "🔒 This is your private channel. These accounts came from Salesforce and are assigned to you — "
            "no other partner agent can see them, and you cannot see theirs."}]},
    ]
    return text, blocks


def outcome_modal(channel_id, agent_id, assignments, selected_task=None, outcome=None):
    """
    Only the caller's own assignments are ever put in this dropdown — and the
    submission is re-checked server-side against the record owner as well.
    """
    task_options = [
        {"text": {"type": "plain_text", "text": f"{a['borrower']} — {a['loan_id']} ({a['dpd']} DPD)"},
         "value": a["task_id"]}
        for a in assignments
    ]
    task_select = {"type": "static_select", "action_id": "task_select", "options": task_options}
    if selected_task:
        match = next((o for o in task_options if o["value"] == selected_task), None)
        if match:
            task_select["initial_option"] = match

    outcome_select = {"type": "static_select", "action_id": "outcome_select", "options": OUTCOME_OPTIONS}
    if outcome in OUTCOME_BY_VALUE:
        outcome_select["initial_option"] = OUTCOME_BY_VALUE[outcome]

    blocks = [
        {"type": "input", "block_id": "task", "label": {"type": "plain_text", "text": "Which account did you visit?"},
         "element": task_select},
        {"type": "input", "block_id": "outcome", "label": {"type": "plain_text", "text": "What happened?"},
         "dispatch_action": True, "element": outcome_select},
    ]

    if outcome == journey.PAID:
        blocks += [
            {"type": "input", "block_id": "amount", "label": {"type": "plain_text", "text": "Amount collected (₹)"},
             "element": {"type": "plain_text_input", "action_id": "amount_input"}},
            {"type": "input", "block_id": "mode", "label": {"type": "plain_text", "text": "Mode"},
             "element": {"type": "static_select", "action_id": "mode_input", "options": [
                 {"text": {"type": "plain_text", "text": m}, "value": m} for m in ["UPI", "Cash", "Cheque", "NACH"]]}},
            {"type": "input", "block_id": "receipt", "optional": True,
             "label": {"type": "plain_text", "text": "Receipt number"},
             "element": {"type": "plain_text_input", "action_id": "receipt_input"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text":
                "Salesforce records the payment and closes the visit. You will be asked to attach the payment proof — "
                "it stays in this private channel."}]},
        ]

    elif outcome == journey.PTP:
        blocks += [
            {"type": "input", "block_id": "amount", "label": {"type": "plain_text", "text": "Promised amount (₹)"},
             "element": {"type": "plain_text_input", "action_id": "amount_input"}},
            {"type": "input", "block_id": "promise_date", "label": {"type": "plain_text", "text": "Promised date"},
             "element": {"type": "datepicker", "action_id": "promise_date_input"}},
            {"type": "input", "block_id": "mode", "label": {"type": "plain_text", "text": "Promised mode"},
             "element": {"type": "static_select", "action_id": "mode_input", "options": [
                 {"text": {"type": "plain_text", "text": m}, "value": m} for m in ["UPI", "Cash", "Cheque", "NACH"]]}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text":
                "A reminder is scheduled back to you the day before the promised date."}]},
        ]

    elif outcome == journey.REFUSED:
        blocks += [
            {"type": "input", "block_id": "refusal_type", "label": {"type": "plain_text", "text": "Reason category"},
             "element": {"type": "static_select", "action_id": "refusal_type_input", "options": [
                 {"text": {"type": "plain_text", "text": r}, "value": r} for r in
                 ["Dispute over amount", "Financial hardship claimed", "Refused without reason",
                  "Asset already sold", "Threatened / hostile"]]}},
            {"type": "input", "block_id": "reason", "label": {"type": "plain_text", "text": "What did the customer say?"},
             "element": {"type": "plain_text_input", "action_id": "reason_input", "multiline": True}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text":
                "This goes to the Hero FinCorp internal team for a decision. You will see that it was escalated — "
                "the internal discussion itself stays internal."}]},
        ]

    elif outcome == journey.UNAVAILABLE:
        blocks += [
            {"type": "input", "block_id": "revisit", "label": {"type": "plain_text", "text": "Revisit on"},
             "element": {"type": "datepicker", "action_id": "revisit_input"}},
            {"type": "input", "block_id": "attempt", "label": {"type": "plain_text", "text": "Which attempt was this?"},
             "element": {"type": "static_select", "action_id": "attempt_input", "options": [
                 {"text": {"type": "plain_text", "text": "First attempt"}, "value": "1"},
                 {"text": {"type": "plain_text", "text": "Second attempt — nobody home again"}, "value": "2"}]}},
            {"type": "input", "block_id": "note", "optional": True,
             "label": {"type": "plain_text", "text": "Note"},
             "element": {"type": "plain_text_input", "action_id": "note_input"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text":
                "A second consecutive miss on the same account is raised to your Hero FinCorp manager."}]},
        ]

    return {
        "type": "modal",
        "callback_id": "outcome_modal_submit",
        "private_metadata": _meta(channel_id, agent_id),
        "title": {"type": "plain_text", "text": "Record visit outcome"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": blocks,
    }


def outcome_receipt_card(agent, task, outcome, detail, sync_record, follow_up):
    emoji = journey.OUTCOME_EMOJI[outcome]
    label = journey.OUTCOME_LABELS[outcome]
    text = f"{label} recorded — {task['loan_id']}"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"{emoji} *{label} recorded* — `{task['loan_id']}` · {task['borrower']}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": detail}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*Salesforce:* {sync_record.status_line()}\n*Next:* {follow_up['follow_up']}"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            f"Recorded by {agent['name']} · Salesforce holds the record; this channel holds the conversation."}]},
    ]
    return text, blocks


def payment_proof_prompt(task):
    text = f"Attach payment proof — {task['loan_id']}"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"📎 *Attach the payment proof for `{task['loan_id']}`* — upload the screenshot or receipt "
            f"straight into this channel."}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "The file is stored against the loan in Salesforce and stays in your private channel. "
            "No other partner agent can open it."}]},
    ]
    return text, blocks


# ---------- Nudges ----------

NUDGE_NOT_STARTED = "not_started"
NUDGE_BEHIND = "behind"
NUDGE_END_OF_DAY = "end_of_day"

def nudge_card(agent, kind, progress, deadline_label):
    pending = progress["pending"]
    if kind == NUDGE_NOT_STARTED:
        headline = f"👋 {agent['name']}, your {progress['assigned']} visits for {human_date(today())} are still not started."
        body = (f"Nothing has been recorded yet as of {deadline_label}. Tap *Start my day* on your assignment card, "
                f"or record an outcome if you have already been out.")
    elif kind == NUDGE_BEHIND:
        headline = f"⏳ {agent['name']}, {pending} of {progress['assigned']} visits are still open."
        body = (f"As of {deadline_label} you have recorded {progress['logged']}. "
                f"Record whatever you have so far — partial updates are fine and they reach Salesforce immediately.")
    else:
        headline = f"🔔 {agent['name']}, {pending} visits are closing unrecorded today."
        body = (f"It is {deadline_label}. Anything not recorded by end of day is reported to your Hero FinCorp "
                f"manager as incomplete.")

    text = headline
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{headline}*\n{body}"}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "📝  Record visit outcome"},
             "style": "primary", "value": agent["agent_id"], "action_id": "open_outcome_modal"},
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "Automated reminder from the Hero FinCorp collections workflow · logged against your agent record in Salesforce"}]},
    ]
    return text, blocks


def manager_nudge_escalation(agent, progress, deadline_label):
    manager = personas.manager_for(agent["agent_id"])
    text = f"{agent['name']} — {progress['pending']} visits unrecorded"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"⚠️ *{agent['name']}* ({agent['workforce_type']}, {agent['cluster']}) has "
            f"*{progress['pending']} of {progress['assigned']}* visits unrecorded at {deadline_label}."}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*Started:* {'yes, ' + human_time(progress['started_at']) if progress['started'] else 'no'}\n"
            f"*Last activity:* {human_time(progress['last_activity'])}\n"
            f"*Nudges already sent:* automated reminders at the not-started and mid-day checkpoints"}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Send a direct reminder"},
             "style": "primary", "value": agent["agent_id"], "action_id": "manager_nudge_agent"},
            {"type": "button", "text": {"type": "plain_text", "text": "Reassign tomorrow"},
             "value": agent["agent_id"], "action_id": "manager_flag_reassign"},
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            f"Internal channel — {manager['name']} and collections ops only. {agent['name']} cannot see this message."}]},
    ]
    return text, blocks


# ---------- Manager view ----------

def activity_board(agents_progress):
    rows = []
    for agent, progress in agents_progress:
        if not progress["started"]:
            status = "🔴 not started"
        elif progress["pending"] == 0:
            status = "🟢 complete"
        else:
            status = f"🟡 {progress['logged']}/{progress['assigned']} done"
        outcomes = " · ".join(
            f"{journey.OUTCOME_EMOJI[k]} {v}" for k, v in progress["outcomes"].items()
        ) or "no outcomes yet"
        rows.append(
            f"*{agent['name']}* — {agent['workforce_type']}, {agent['cluster']}\n"
            f"   {status} · collected {rupees(progress['collected'])} · {outcomes}\n"
            f"   last activity {human_time(progress['last_activity'])}"
        )

    text = "Partner agent activity"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🗂️ Partner agent activity — {human_date(today())}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n\n".join(rows)}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "🔄  Refresh"}, "action_id": "refresh_activity_board"},
            {"type": "button", "text": {"type": "plain_text", "text": "🔔  Nudge whoever is behind"},
             "style": "primary", "action_id": "nudge_all_behind"},
            {"type": "button", "text": {"type": "plain_text", "text": "🔍  Open an agent's day"},
             "action_id": "manager_open_agent"},
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "Manager view · every partner agent in one place. Each agent sees only their own channel — "
            "this roll-up is not visible to any of them."}]},
    ]
    return text, blocks


def escalation_card(task, agent, refusal_type, reason, sync_record):
    text = f"Refusal escalated — {task['loan_id']}"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"⛔ *Refusal — `{task['loan_id']}`* · {task['borrower']} · {task['bucket']} · {task['dpd']} DPD · "
            f"{rupees(task['overdue'])} overdue"}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*Category:* {refusal_type}\n*Reported:* \"{reason}\"\n"
            f"*Reported by:* {agent['name']} ({agent['workforce_type']}, {agent['posting']})"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Salesforce:* {sync_record.status_line()}"}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Proceed — issue notice"},
             "style": "danger", "value": task["task_id"], "action_id": "escalation_proceed"},
            {"type": "button", "text": {"type": "plain_text", "text": "Hold — need more information"},
             "value": task["task_id"], "action_id": "escalation_hold"},
            {"type": "button", "text": {"type": "plain_text", "text": "Send back to the agent"},
             "value": task["task_id"], "action_id": "escalation_return"},
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "Internal legal & ops only. The partner agent sees that the case was escalated, not what is decided here."}]},
    ]
    return text, blocks


def agent_progress_view(agent, assignments, progress):
    logged = journey_state.logged_items(agent["agent_id"])
    lines = []
    for item in assignments:
        entry = logged.get(item["task_id"])
        if entry:
            lines.append(f"{journey.OUTCOME_EMOJI[entry['outcome']]} *{item['borrower']}* — "
                         f"{journey.OUTCOME_LABELS[entry['outcome']]}\n   {entry['detail']}")
        else:
            lines.append(f"⬜ *{item['borrower']}* — `{item['loan_id']}` — not recorded yet")

    return {
        "type": "modal",
        "callback_id": "agent_progress_view",
        "title": {"type": "plain_text", "text": "My day so far"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text":
                f"*{progress['logged']} of {progress['assigned']} recorded* · "
                f"{rupees(progress['collected'])} collected today"}},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n\n".join(lines)}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text":
                "Only your own assignments appear here."}]},
        ],
    }
