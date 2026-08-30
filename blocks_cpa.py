"""
Block Kit for the CPA approval journey.

The approver's question is "what is awaiting my decision, and do I have enough
to decide it?" — so the card carries the request detail, the officer's
justification, the routing that brought it here, and the supporting documents,
with the decision one click away.
"""
import cpa_approvals as cpa
import personas
from fmt import rupees


def cpa_request_card(request, attachment_links=None):
    approver = request.current_approver()
    text = f"{cpa.cpa_label()} awaiting decision — {request.request_id}"
    level_line = (f"Level {request.current_level()} of {request.total_levels()}"
                  if request.total_levels() > 1 else "Single-level approval")

    docs = attachment_links or []
    docs_text = "\n".join(f"• <{url}|{name}>" for name, url in docs) if docs else \
        "\n".join(f"• {name}" for name in request.attachments)

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🧾 {cpa.cpa_label()} — decision needed"}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*{personas.mention(approver)}, this is with you.*\n"
            f"`{request.request_id}` · {level_line}"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Applicant*\n{request.applicant}"},
            {"type": "mrkdwn", "text": f"*Product*\n{request.product}"},
            {"type": "mrkdwn", "text": f"*Amount*\n{rupees(request.amount)}"},
            {"type": "mrkdwn", "text": f"*Loan / LOS*\n`{request.loan_id}`\n`{request.los_reference}`"},
        ]},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*Policy exception raised*\n{request.deviation_lines()}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*Officer's justification*\n_\"{request.justification}\"_\n*Raised by:* {request.requester}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Supporting documents*\n{docs_text}"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            f"*Routing:* {request.routing_reason}\n{request.chain_summary()}"}]},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "✅  Approve"}, "style": "primary",
             "value": request.request_id, "action_id": "cpa_approve"},
            {"type": "button", "text": {"type": "plain_text", "text": "❌  Reject"}, "style": "danger",
             "value": request.request_id, "action_id": "cpa_reject"},
            {"type": "button", "text": {"type": "plain_text", "text": "💬  Ask the officer"},
             "value": request.request_id, "action_id": "cpa_query"},
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "Raised in Salesforce/LOS · decided here · written straight back to the LOS record. "
            "Only the approver this step belongs to can act on it."}]},
    ]
    return text, blocks


def cpa_decision_modal(request, decision):
    is_reject = decision == cpa.REJECTED
    return {
        "type": "modal",
        "callback_id": "cpa_decision_submit",
        "private_metadata": f"{request.request_id}|{decision}",
        "title": {"type": "plain_text", "text": "Reject request" if is_reject else "Approve request"},
        "submit": {"type": "plain_text", "text": "Confirm rejection" if is_reject else "Confirm approval"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text":
                f"`{request.request_id}` · {request.applicant} · {rupees(request.amount)} · {request.product}"}},
            {"type": "input", "block_id": "comment", "optional": not is_reject,
             "label": {"type": "plain_text", "text": "Reason for rejection" if is_reject else "Approval note (optional)"},
             "element": {"type": "plain_text_input", "action_id": "comment_input", "multiline": True}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text":
                ("This reason is written to the Salesforce record and sent to the requesting officer."
                 if is_reject else
                 ("Approving at this level sends the request to the next approver."
                  if not request.is_final_level() else
                  "This is the final level — approving completes the request in Salesforce."))}]},
        ],
    }


def cpa_decided_card(request, sync_record, decided_by):
    last = request.decisions[-1]
    approved = last["decision"] == cpa.APPROVED
    if request.status == cpa.PENDING:
        headline = (f"✅ *Approved at Level {last['level']}* by {decided_by} — "
                    f"now with {request.current_approver()['name']} for Level {request.current_level()}")
    elif approved:
        headline = f"✅ *Approved* — `{request.request_id}` fully approved by {decided_by}"
    else:
        headline = f"❌ *Rejected* at Level {last['level']} by {decided_by}"

    text = headline.replace("*", "")
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": headline}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*{request.applicant}* · {request.product} · {rupees(request.amount)} · `{request.loan_id}`"
            + (f"\n*Note:* \"{last['comment']}\"" if last.get("comment") else "")}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": request.chain_summary()}]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            f"*Salesforce:* {sync_record.status_line()} · requester notified"}]},
    ]
    return text, blocks


def requester_notification(request, sync_record):
    last = request.decisions[-1]
    if request.status == cpa.APPROVED:
        headline = f"✅ *Your {cpa.cpa_label()} request `{request.request_id}` is approved.*"
        next_step = "The LOS record has been updated — the application can move forward."
    elif request.status == cpa.REJECTED:
        headline = f"❌ *Your {cpa.cpa_label()} request `{request.request_id}` was rejected.*"
        next_step = "The reason is on the LOS record. Re-submit with fresh documentation if the position changes."
    else:
        headline = (f"➡️ *`{request.request_id}` cleared Level {last['level']}* and is now with "
                    f"{request.current_approver()['name']} ({request.current_approver()['role']}).")
        next_step = "No action needed from you — you will be told the final outcome."

    text = headline.replace("*", "")
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": headline}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*{request.applicant}* · {request.product} · {rupees(request.amount)}\n"
            f"*Decided by:* {last['by']}" + (f"\n*Comment:* \"{last['comment']}\"" if last.get("comment") else "")}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"{next_step}\n{sync_record.status_line()}"}]},
    ]
    return text, blocks


def cpa_audit_card(request, sync_record):
    last = request.decisions[-1]
    text = f"Audit — {request.request_id} {last['decision']}"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*`{request.request_id}`* · L{last['level']} *{last['decision']}* by {last['by']}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"```{sync_record.as_curl_ish()}```"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            f"{sync_record.status_line()} · {request.chain_summary()}"}]},
    ]
    return text, blocks


def cpa_inbox_card(person, requests):
    if requests:
        lines = "\n".join(
            f"• `{r.request_id}` — {r.applicant}, {r.product}, {rupees(r.amount)} "
            f"(L{r.current_level()} of {r.total_levels()})"
            for r in requests
        )
        body = f"*{len(requests)} awaiting your decision:*\n{lines}"
    else:
        body = "Nothing is waiting on you right now."

    text = f"{len(requests)} approvals awaiting {person['name']}"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"📥 {cpa.cpa_label()} — your queue"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": body}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "🔄  Refresh my queue"},
             "action_id": "cpa_refresh_inbox"},
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            f"{person['name']} — {person['role']}. Requests at other levels are not shown here and cannot be acted on from here."}]},
    ]
    return text, blocks


def cpa_query_modal(request):
    return {
        "type": "modal",
        "callback_id": "cpa_query_submit",
        "private_metadata": request.request_id,
        "title": {"type": "plain_text", "text": "Ask the officer"},
        "submit": {"type": "plain_text", "text": "Send"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text":
                f"Question about `{request.request_id}` — {request.applicant}"}},
            {"type": "input", "block_id": "question",
             "label": {"type": "plain_text", "text": "What do you need before deciding?"},
             "element": {"type": "plain_text_input", "action_id": "question_input", "multiline": True}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text":
                "The question is posted back to the requesting officer and logged on the Salesforce record. "
                "The request stays with you in the meantime."}]},
        ],
    }


def cpa_intake_card(request):
    """
    What the requesting officer sees when their LOS request reaches Slack:
    confirmation that it is moving, and exactly who it went to.
    """
    approver = request.current_approver()
    chain_names = " → ".join(
        f"L{i + 1} {personas.INTERNAL_STAFF[p]['name']}" for i, p in enumerate(request.chain)
    )
    text = f"Request routed — {request.request_id}"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"📨 *Raised in Salesforce/LOS and routed* — `{request.request_id}`"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Applicant*\n{request.applicant}"},
            {"type": "mrkdwn", "text": f"*Amount*\n{rupees(request.amount)}"},
            {"type": "mrkdwn", "text": f"*LOS reference*\n`{request.los_reference}`"},
            {"type": "mrkdwn", "text": f"*Stage*\n{request.los_stage}"},
        ]},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*Now with:* {personas.mention(approver)} — {approver['role']}\n"
            f"*Approval path:* {chain_names}\n*Why:* {request.routing_reason}"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "The full detail and the customer documents went only to the approver's private channel. "
            "You are told the outcome, not shown the internal deliberation."}]},
    ]
    return text, blocks


def cpa_question_card(request, question, asked_by):
    text = f"Question on {request.request_id}"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"💬 *{asked_by} has a question on `{request.request_id}`* ({request.applicant}, {rupees(request.amount)})"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"_\"{question}\"_"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "Logged on the Salesforce record. The request stays with the approver until it is answered."}]},
    ]
    return text, blocks
