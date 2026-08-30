"""
Hero FinCorp Bot — real Socket Mode app. Every action (button click, modal
submit) actually updates Slack and logs to the audit trail.

Two layers of workflows live here:

  * the original four use cases — knowledge base, bucket collections, credit
    deviation, lead swarming — handled in this file;
  * the connected journeys built for the customer walkthrough — the external
    partner agent's collections day with automated nudges, CPA approvals with
    one- and multi-level routing, and the security/data-ownership consoles —
    registered from handlers_collections.py, handlers_cpa.py and
    handlers_security.py.
"""
import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import handlers_collections
import handlers_cpa
import handlers_security
from app_config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN, require_tokens
from audit_log import log_action
from kb_answers import find_answer
from queues import BUCKET_QUEUES, BUCKET_LABELS, DEVIATION_QUEUE, LEAD_QUEUE, PENDING_APPROVALS
from queue_state import get_queue_message, remember_queue_message
from slack_blocks import (
    field_visit_card, lead_card, legal_escalation_card,
    visit_modal, deviation_modal, lead_modal, lead_queue_card,
    pending_approvals_notice_card, select_approval_modal, approval_detail_modal, approval_confirmation_view,
)

logging.basicConfig(level=logging.WARNING)

app = App(token=SLACK_BOT_TOKEN)

# The connected journeys register their own handlers so this file stays about
# the original four use cases.
handlers_collections.register(app)
handlers_cpa.register(app)
handlers_security.register(app)

_channel_name_cache = {}
_channel_id_cache = {}


def _channel_name(client, channel_id):
    if channel_id not in _channel_name_cache:
        info = client.conversations_info(channel=channel_id)
        _channel_name_cache[channel_id] = info["channel"]["name"] if info.get("ok") else ""
    return _channel_name_cache[channel_id]


def _channel_id_by_name(client, name):
    if name not in _channel_id_cache:
        cursor = None
        found = None
        while True:
            resp = client.conversations_list(types="public_channel", limit=200, cursor=cursor)
            for ch in resp.get("channels", []):
                if ch["name"] == name:
                    found = ch["id"]
                    break
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if found or not cursor:
                break
        _channel_id_cache[name] = found
    return _channel_id_cache[name]


def _actor_name(client, user_id):
    try:
        info = client.users_info(user=user_id)
        if info.get("ok"):
            return info["user"].get("real_name") or info["user"].get("name") or user_id
    except Exception:
        pass
    return user_id


# ---------- Knowledge base Q&A ----------

@app.event("message")
def handle_kb_question(event, client):
    if event.get("bot_id") or event.get("subtype"):
        return

    channel_id = event["channel"]
    name = _channel_name(client, channel_id)
    if name != "branch-support-escalations":
        return

    text = event.get("text") or ""
    ts = event["ts"]
    user = _actor_name(client, event.get("user", ""))
    answer = find_answer(text)

    if answer:
        client.chat_postMessage(channel=channel_id, thread_ts=ts, text=f"📘 {answer}")
        log_action("KB_QUESTION_ANSWERED", "-", user, text)
    else:
        client.chat_postMessage(
            channel=channel_id, thread_ts=ts,
            text="Couldn't find a confident answer in the knowledge base — flagging this for manual follow-up from the branch support team.",
        )
        log_action("KB_QUESTION_UNANSWERED", "-", user, text)


# ---------- Open modals ----------

@app.action("open_visit_modal")
def open_visit_modal(ack, body, client):
    ack()
    channel_id = body["channel"]["id"]
    name = _channel_name(client, channel_id)
    queue = BUCKET_QUEUES.get(name, [])
    client.views_open(trigger_id=body["trigger_id"], view=visit_modal(channel_id, queue))


@app.action("visit_outcome_select")
def handle_outcome_change(ack, body, client):
    ack()
    channel_id = body["view"]["private_metadata"]
    name = _channel_name(client, channel_id)
    queue = BUCKET_QUEUES.get(name, [])

    values = body["view"]["state"]["values"]
    selected_loan = values.get("loan", {}).get("loan_select", {}).get("selected_option", {}).get("value")
    new_outcome = body["actions"][0]["selected_option"]["value"]

    client.views_update(
        view_id=body["view"]["id"],
        view=visit_modal(channel_id, queue, selected_loan=selected_loan, outcome=new_outcome),
    )


@app.action("open_deviation_modal")
def open_deviation_modal(ack, body, client):
    ack()
    channel_id = body["channel"]["id"]
    client.views_open(trigger_id=body["trigger_id"], view=deviation_modal(channel_id, DEVIATION_QUEUE))


@app.action("view_pending_approvals")
def open_pending_approvals(ack, body, client):
    ack()
    client.views_open(trigger_id=body["trigger_id"], view=select_approval_modal(PENDING_APPROVALS))


@app.action("open_lead_modal")
def open_lead_modal(ack, body, client):
    ack()
    channel_id = body["channel"]["id"]
    client.views_open(trigger_id=body["trigger_id"], view=lead_modal(channel_id, LEAD_QUEUE))


# ---------- Handle modal submissions ----------

@app.view("visit_modal_submit")
def handle_visit_submit(ack, body, client, view):
    ack()
    channel_id = view["private_metadata"]
    name = _channel_name(client, channel_id)
    values = view["state"]["values"]

    loan_id = values["loan"]["loan_select"]["selected_option"]["value"]
    outcome_value = values["outcome"]["visit_outcome_select"]["selected_option"]["value"]
    outcome_label = {"Paid": "Paid", "PTP": "Promise to Pay", "Refused": "Refused", "NA": "Not Available"}[outcome_value]

    if outcome_value == "Paid":
        amount = values.get("paid_amount", {}).get("paid_amount_input", {}).get("value") or "full amount"
        detail = f"₹{amount} collected. Case closed."
    elif outcome_value == "PTP":
        amount = values["ptp_amount"]["ptp_amount_input"]["value"]
        date = values["ptp_date"]["ptp_date_input"]["selected_date"]
        mode = values["ptp_mode"]["ptp_mode_input"]["selected_option"]["value"]
        detail = f"₹{amount} promised by {date} via {mode}"
    elif outcome_value == "Refused":
        refusal_reason = values["refusal_reason"]["refusal_reason_input"]["value"]
        detail = f"Refused — {refusal_reason}"
    else:  # NA
        revisit = values["revisit_date"]["revisit_date_input"]["selected_date"]
        note = values.get("na_note", {}).get("na_note_input", {}).get("value") or ""
        detail = f"Not available. Revisit scheduled for {revisit}." + (f" {note}" if note else "")

    queue_entry = next((q for q in BUCKET_QUEUES.get(name, []) if q["loan_id"] == loan_id), {})
    borrower = queue_entry.get("borrower", "Unknown")
    dpd = queue_entry.get("dpd", "?")
    bucket_label = BUCKET_LABELS.get(name, name)
    user = _actor_name(client, body["user"]["id"])
    is_npa = (name == "collections-npa")
    will_escalate = outcome_value == "Refused"  # Refused in ANY bucket goes to the manager for a decision

    text, blocks = field_visit_card(loan_id, borrower, bucket_label, dpd, outcome_label, detail, user, escalate_eligible=(is_npa and not will_escalate))
    client.chat_postMessage(channel=channel_id, text=text, blocks=blocks)
    log_action("VISIT_LOGGED", loan_id, user, f"{outcome_label} — {detail}")

    # A Refused outcome, in any bucket, is not something the partner agent or
    # this workflow decides alone — it goes to the manager, who reads the
    # reason and decides whether to proceed with legal action or hold for
    # more information. Only NPA accounts (90+ DPD) are actually legally
    # eligible under SARFAESI, but the decision step itself is the same
    # everywhere; "Proceed" earlier in the pipeline means intensifying
    # collections, not literal legal filing.
    if will_escalate:
        legal_id = _channel_id_by_name(client, "legal-escalations")
        if legal_id:
            legal_text, legal_blocks = legal_escalation_card(loan_id, borrower, dpd, refusal_reason, user, bucket_label=bucket_label, is_npa=is_npa)
            client.chat_postMessage(channel=legal_id, text=legal_text, blocks=legal_blocks)
            log_action("ESCALATED_TO_LEGAL", loan_id, "system", refusal_reason)


def _refresh_pending_approvals_notice(client, channel_id):
    text, blocks = pending_approvals_notice_card(len(PENDING_APPROVALS))
    existing = get_queue_message("pending_approvals")
    if existing:
        client.chat_update(channel=existing["channel"], ts=existing["ts"], text=text, blocks=blocks)
    else:
        result = client.chat_postMessage(channel=channel_id, text=text, blocks=blocks)
        if result.get("ok"):
            remember_queue_message("pending_approvals", channel_id, result["ts"])


@app.view("deviation_modal_submit")
def handle_deviation_submit(ack, body, client, view):
    ack()
    channel_id = view["private_metadata"]
    values = view["state"]["values"]

    loan_id = values["loan"]["loan_select"]["selected_option"]["value"]
    deviation_type = values["deviation_type"]["type_select"]["selected_option"]["value"]
    detail = values["detail"]["detail_input"]["value"]
    justification = values["justification"]["justification_input"]["value"]

    entry = next((q for q in DEVIATION_QUEUE if q["loan_id"] == loan_id), {})
    user = _actor_name(client, body["user"]["id"])

    PENDING_APPROVALS.append({
        "loan_id": loan_id, "product": entry.get("product", ""), "amount": entry.get("amount", ""),
        "deviation_type": deviation_type, "deviation_detail": detail, "justification": justification,
        "requesting_officer": user,
    })
    log_action("DEVIATION_REQUESTED", loan_id, user, f"{deviation_type} — {detail}")
    client.chat_postMessage(channel=channel_id, text="🔔 New credit deviation request received. Please do check.")
    _refresh_pending_approvals_notice(client, channel_id)


@app.view("lead_modal_submit")
def handle_lead_submit(ack, body, client, view):
    ack()
    channel_id = view["private_metadata"]
    values = view["state"]["values"]

    lead_id = values["lead"]["lead_select"]["selected_option"]["value"]
    outcome = values["outcome"]["outcome_select"]["selected_option"]["value"]
    note = values["note"]["note_input"]["value"]
    selected_docs = values["docs"]["docs_select"].get("selected_options") or []
    docs = ", ".join(o["value"] for o in selected_docs) if selected_docs else "None confirmed yet"

    entry = next((q for q in LEAD_QUEUE if q["lead_id"] == lead_id), {})
    user = _actor_name(client, body["user"]["id"])
    qualifies = (outcome == "Interested")

    text, blocks = lead_card(
        lead_id=lead_id, contact_name=entry.get("contact_name", ""), source=entry.get("source", ""),
        product_interest=entry.get("product_interest", ""), outcome=outcome, note=note, docs_ready=docs,
        qualifies=qualifies,
    )
    client.chat_postMessage(channel=channel_id, text=text, blocks=blocks)
    log_action("LEAD_CONTACT_LOGGED", lead_id, user, f"{outcome} — {note}")

    # Once contacted (any outcome), remove from the raw-leads queue so it
    # doesn't show up again in the dropdown, and refresh the queue card.
    LEAD_QUEUE[:] = [q for q in LEAD_QUEUE if q["lead_id"] != lead_id]
    queue_msg = get_queue_message("lead_queue")
    if queue_msg:
        refreshed_text, refreshed_blocks = lead_queue_card(LEAD_QUEUE)
        client.chat_update(channel=queue_msg["channel"], ts=queue_msg["ts"], text=refreshed_text, blocks=refreshed_blocks)


@app.view("select_approval_modal_submit")
def handle_select_approval(ack, body):
    values = body["view"]["state"]["values"]
    loan_id = values["loan"]["loan_select"]["selected_option"]["value"]
    entry = next((q for q in PENDING_APPROVALS if q["loan_id"] == loan_id), None)
    if entry:
        ack(response_action="update", view=approval_detail_modal(entry))
    else:
        ack()


# ---------- Terminal actions from inside the detail modal ----------

@app.action("approve_deviation_modal")
def handle_approve_modal(ack, body, client):
    ack()
    loan_id = body["actions"][0]["value"]
    user = _actor_name(client, body["user"]["id"])
    log_action("APPROVED", loan_id, user)
    PENDING_APPROVALS[:] = [q for q in PENDING_APPROVALS if q["loan_id"] != loan_id]

    client.views_update(
        view_id=body["view"]["id"],
        view=approval_confirmation_view(f"✅ *Approved* — `{loan_id}`\nBy {user}. Proceeds to disbursement (outside Slack scope)."),
    )

    notice = get_queue_message("pending_approvals")
    if notice:
        client.chat_postMessage(channel=notice["channel"], text=f"✅ Deviation for `{loan_id}` approved by {user}.")
        _refresh_pending_approvals_notice(client, notice["channel"])


@app.action("reject_deviation_modal")
def handle_reject_modal(ack, body, client):
    ack()
    loan_id = body["actions"][0]["value"]
    user = _actor_name(client, body["user"]["id"])
    log_action("REJECTED", loan_id, user)
    PENDING_APPROVALS[:] = [q for q in PENDING_APPROVALS if q["loan_id"] != loan_id]

    client.views_update(
        view_id=body["view"]["id"],
        view=approval_confirmation_view(f"❌ *Rejected* — `{loan_id}`\nBy {user}. Officer notified, case closed."),
    )

    notice = get_queue_message("pending_approvals")
    if notice:
        client.chat_postMessage(channel=notice["channel"], text=f"❌ Deviation for `{loan_id}` rejected by {user}.")
        _refresh_pending_approvals_notice(client, notice["channel"])


@app.action("escalate_to_legal")
def handle_escalate(ack, body, client):
    ack()
    loan_id = body["actions"][0]["value"]
    user = _actor_name(client, body["user"]["id"])
    log_action("ESCALATED_TO_LEGAL", loan_id, user)

    channel, ts = body["channel"]["id"], body["message"]["ts"]
    blocks = [b for b in body["message"]["blocks"] if b.get("type") != "actions"]
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"🔴 *Escalated to Legal* by {user}."}})
    client.chat_update(channel=channel, ts=ts, blocks=blocks, text=f"Escalated — {loan_id}")

    entry = next((q for q in BUCKET_QUEUES.get("collections-npa", []) if q["loan_id"] == loan_id), {})
    borrower = entry.get("borrower", "Unknown")
    dpd = entry.get("dpd", "?")

    legal_id = _channel_id_by_name(client, "legal-escalations")
    if legal_id:
        legal_text, legal_blocks = legal_escalation_card(
            loan_id, borrower, dpd, f"Manager judgment call — see full visit outcome in the collections channel.", user
        )
        client.chat_postMessage(channel=legal_id, text=legal_text, blocks=legal_blocks)


@app.action("proceed_legal_action")
def handle_proceed_legal(ack, body, client):
    ack()
    loan_id = body["actions"][0]["value"]
    user = _actor_name(client, body["user"]["id"])
    log_action("LEGAL_ACTION_PROCEED", loan_id, user)

    channel, ts = body["channel"]["id"], body["message"]["ts"]
    blocks = [b for b in body["message"]["blocks"] if b.get("type") != "actions"]
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"⚖️ *Proceeding with legal action* — decided by {user}."}})
    client.chat_update(channel=channel, ts=ts, blocks=blocks, text=f"Proceeding with legal action — {loan_id}")


@app.action("hold_legal_action")
def handle_hold_legal(ack, body, client):
    ack()
    loan_id = body["actions"][0]["value"]
    user = _actor_name(client, body["user"]["id"])
    log_action("LEGAL_ACTION_HOLD", loan_id, user)

    channel, ts = body["channel"]["id"], body["message"]["ts"]
    blocks = [b for b in body["message"]["blocks"] if b.get("type") != "actions"]
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"⏸️ *On hold* — decided by {user}. No legal action taken yet."}})
    client.chat_update(channel=channel, ts=ts, blocks=blocks, text=f"On hold — {loan_id}")


@app.action("handoff_lead")
def handle_handoff(ack, body, client):
    ack()
    lead_id = body["actions"][0]["value"]
    user = _actor_name(client, body["user"]["id"])
    log_action("HANDED_OFF", lead_id, user)

    channel, ts = body["channel"]["id"], body["message"]["ts"]
    blocks = [b for b in body["message"]["blocks"] if b.get("type") != "actions"]
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"➡️ *Handed off* to Field/RM by {user}."}})
    client.chat_update(channel=channel, ts=ts, blocks=blocks, text=f"Handed off — {lead_id}")

    intake_id = _channel_id_by_name(client, "field-collections-intake")
    if intake_id:
        client.chat_postMessage(
            channel=intake_id, text=f"Lead handed off — {lead_id}",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": f"*Lead `{lead_id}` handed off* by {user} from lead swarming."}}],
        )


if __name__ == "__main__":
    require_tokens()
    print("Hero FinCorp Bot starting (Socket Mode)...")
    print("  workflows: knowledge base · bucket collections · credit deviation · lead swarming")
    print("  journeys:  partner-agent collections + nudges · CPA approvals · security console")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
