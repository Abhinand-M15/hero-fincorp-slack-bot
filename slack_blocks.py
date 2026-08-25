"""
Block Kit and modal builders for the 4 Hero FinCorp use cases.
"""


def kb_bot_intro():
    text = "Ask a Policy Question"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "📘 Ask a Policy Question"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "Branch and dealer staff: check the pinned *Canvas* tab above for product policies, eligibility, and document checklists before asking here.\n\nIf your question isn't answered there, post it in this channel — it becomes a tracked case instead of an unanswered message."}},
    ]
    return text, blocks


# ---------- Assignment queue cards (posted once, stay pinned as the "what to work on" view) ----------

def bucket_queue_card(bucket_label, queue):
    lines = [f"• *{q['borrower']}* — `{q['loan_id']}` — {q['dpd']} DPD — assigned to {q['assigned_officer']}" for q in queue]
    text = f"Assigned accounts — {bucket_label}"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"📋 Assigned Accounts — {bucket_label}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines) if lines else "No accounts currently assigned."}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Log Field Visit"}, "action_id": "open_visit_modal"}
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "Field officers: after visiting an account above, click Log Field Visit and select it from the list."}]},
    ]
    return text, blocks


def pending_approvals_notice_card(count):
    text = f"{count} credit deviation request(s) need review"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"🔔 *{count} credit deviation request(s) need review.* Please do check."}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "View Pending Approvals"}, "action_id": "view_pending_approvals"}
        ]},
    ]
    return text, blocks


def select_approval_modal(pending):
    options = [
        {"text": {"type": "plain_text", "text": f"{q['loan_id']} — {q['product']} — ₹{q['amount']}"}, "value": q["loan_id"]}
        for q in pending
    ]
    return {
        "type": "modal",
        "callback_id": "select_approval_modal_submit",
        "title": {"type": "plain_text", "text": "Pending Approvals"},
        "submit": {"type": "plain_text", "text": "View Detail"},
        "blocks": [
            {"type": "input", "block_id": "loan", "label": {"type": "plain_text", "text": "Which request do you want to review?"},
             "element": {"type": "static_select", "action_id": "loan_select", "options": options}},
        ],
    }


def approval_detail_modal(entry):
    loan_id = entry["loan_id"]
    return {
        "type": "modal",
        "callback_id": "approval_detail_view",
        "title": {"type": "plain_text", "text": "Deviation Detail"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Loan ID:* `{loan_id}`\n*Product:* {entry['product']}\n*Requested Amount:* ₹{entry['amount']}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Deviation:* {entry['deviation_type']} — {entry['deviation_detail']}\n*Justification:* \"{entry['justification']}\"\n*Requested by:* {entry['requesting_officer']}"}},
            {"type": "actions", "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "Approve"}, "style": "primary", "value": loan_id, "action_id": "approve_deviation_modal"},
                {"type": "button", "text": {"type": "plain_text", "text": "Reject"}, "style": "danger", "value": loan_id, "action_id": "reject_deviation_modal"},
            ]},
        ],
    }


def approval_confirmation_view(message):
    return {
        "type": "modal",
        "callback_id": "approval_confirmation_view",
        "title": {"type": "plain_text", "text": "Decision Recorded"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": message}}],
    }


def deviation_queue_card(queue):
    lines = [f"• `{q['loan_id']}` — {q['product']} — ₹{q['amount']} — {q['requesting_officer']}" for q in queue]
    text = "Pending deviation requests"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "📋 Applications Needing Deviation Review"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines) if lines else "No pending applications."}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Request Deviation Approval"}, "action_id": "open_deviation_modal"}
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "Credit officers: select the application, add the deviation reason and justification."}]},
    ]
    return text, blocks


def lead_queue_card(queue):
    lines = [f"• *{q['contact_name']}* — {q['source']} — interested in {q['product_interest']}" for q in queue]
    text = "New raw leads"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "📋 New Raw Leads"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines) if lines else "No new leads right now."}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Log Lead Contact"}, "action_id": "open_lead_modal"}
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "Inside sales: after calling a lead above, click Log Lead Contact to record the outcome."}]},
    ]
    return text, blocks


# ---------- Result cards (posted after a modal is submitted) ----------

def field_visit_card(loan_id, borrower, bucket_label, dpd, outcome, detail, officer, escalate_eligible=False):
    text = f"Visit logged — {loan_id}"
    emoji = {"Bucket 2 (31–60 DPD)": "🟡", "Bucket 3 (61–90 DPD)": "🟠"}.get(bucket_label, "🔴")
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Visit logged — `{loan_id}`*\n{emoji} {bucket_label}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Borrower:* {borrower}\n*Outcome:* {outcome}\n*Detail:* {detail}\n*Logged by:* {officer}"}},
    ]
    if escalate_eligible:
        blocks.append({
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "Escalate to Legal"}, "style": "danger", "value": loan_id, "action_id": "escalate_to_legal"}
            ],
        })
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": "Field Collections Coordination — audit trail entry"}]})
    return text, blocks


def deviation_approval_card(loan_id, product, amount, deviation_type, deviation_detail, justification, requesting_officer):
    text = f"Deviation Approval Needed — {loan_id}"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "📝 Deviation Approval Needed"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Loan ID:* `{loan_id}`\n*Product:* {product}\n*Requested Amount:* ₹{amount}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Deviation:* {deviation_type} — {deviation_detail}\n*Justification:* \"{justification}\"\n*Requested by:* {requesting_officer}"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "Routed to: *Credit Head* (placeholder approver for this demo)"}]},
        {
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "Approve"}, "style": "primary", "value": loan_id, "action_id": "approve_deviation"},
                {"type": "button", "text": {"type": "plain_text", "text": "Reject"}, "style": "danger", "value": loan_id, "action_id": "reject_deviation"},
            ],
        },
    ]
    return text, blocks


def legal_escalation_card(loan_id, borrower, dpd, reason, escalated_by, bucket_label="NPA (90+ DPD)", is_npa=True):
    text = f"Escalation — {loan_id}"
    eligibility_note = (
        "Legal-eligible under SARFAESI (secured loan, 90+ DPD). Review the reason above and decide."
        if is_npa else
        f"This account is in {bucket_label}, not yet legally eligible (SARFAESI applies at 90+ DPD). "
        "\"Proceed\" here means intensifying collections action, not filing legal action."
    )
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*🔴 New Escalation — `{loan_id}`* ({borrower}, {dpd} DPD, {bucket_label})"}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*Reason:* {reason}\n*Escalated by:* {escalated_by}"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": eligibility_note}]},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Proceed with Legal Action" if is_npa else "Proceed / Intensify"}, "style": "danger", "value": loan_id, "action_id": "proceed_legal_action"},
            {"type": "button", "text": {"type": "plain_text", "text": "Hold"}, "value": loan_id, "action_id": "hold_legal_action"},
        ]},
    ]
    return text, blocks


def lead_card(lead_id, contact_name, source, product_interest, outcome, note, docs_ready, qualifies=False):
    text = f"Lead {lead_id} — {contact_name}"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Lead `{lead_id}`* — {source}\n*{contact_name}* interested in: {product_interest}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Status:* {outcome}\n{note}\n*Documents:* {docs_ready}"}},
    ]
    if qualifies:
        blocks.append({
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "Handoff to Field/RM"}, "style": "primary", "value": lead_id, "action_id": "handoff_lead"}
            ],
        })
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": "Lead Swarming — inside sales lead tracking"}]})
    return text, blocks


# ---------- Modals ----------

_OUTCOME_OPTIONS = [
    {"text": {"type": "plain_text", "text": "Paid"}, "value": "Paid"},
    {"text": {"type": "plain_text", "text": "Promise to Pay"}, "value": "PTP"},
    {"text": {"type": "plain_text", "text": "Refused"}, "value": "Refused"},
    {"text": {"type": "plain_text", "text": "Not Available"}, "value": "NA"},
]
_OUTCOME_BY_VALUE = {o["value"]: o for o in _OUTCOME_OPTIONS}


def visit_modal(channel_id, queue, selected_loan=None, outcome=None):
    """
    outcome=None -> just the loan + outcome pickers, no detail fields yet.
    Once an outcome is picked, the modal is redrawn (via dispatch_action)
    with only the fields relevant to that outcome.
    """
    loan_options = [
        {"text": {"type": "plain_text", "text": f"{q['borrower']} — {q['loan_id']} ({q['dpd']} DPD)"}, "value": q["loan_id"]}
        for q in queue
    ]
    loan_select = {"type": "static_select", "action_id": "loan_select", "options": loan_options}
    if selected_loan:
        match = next((o for o in loan_options if o["value"] == selected_loan), None)
        if match:
            loan_select["initial_option"] = match

    outcome_select = {"type": "static_select", "action_id": "visit_outcome_select", "options": _OUTCOME_OPTIONS}
    if outcome and outcome in _OUTCOME_BY_VALUE:
        outcome_select["initial_option"] = _OUTCOME_BY_VALUE[outcome]

    blocks = [
        {"type": "input", "block_id": "loan", "label": {"type": "plain_text", "text": "Which account did you visit?"},
         "element": loan_select},
        {"type": "input", "block_id": "outcome", "label": {"type": "plain_text", "text": "Outcome"},
         "dispatch_action": True, "element": outcome_select},
    ]

    if outcome == "Paid":
        blocks.append({"type": "input", "block_id": "paid_amount", "optional": True,
                        "label": {"type": "plain_text", "text": "Amount Paid (₹)"},
                        "element": {"type": "plain_text_input", "action_id": "paid_amount_input"}})
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": "Marking this Paid closes the case — no further action needed."}]})

    elif outcome == "PTP":
        blocks.append({"type": "input", "block_id": "ptp_amount",
                        "label": {"type": "plain_text", "text": "Promised Amount (₹)"},
                        "element": {"type": "plain_text_input", "action_id": "ptp_amount_input"}})
        blocks.append({"type": "input", "block_id": "ptp_date",
                        "label": {"type": "plain_text", "text": "Promised Date"},
                        "element": {"type": "datepicker", "action_id": "ptp_date_input"}})
        blocks.append({"type": "input", "block_id": "ptp_mode",
                        "label": {"type": "plain_text", "text": "Payment Mode"},
                        "element": {"type": "static_select", "action_id": "ptp_mode_input", "options": [
                            {"text": {"type": "plain_text", "text": m}, "value": m} for m in ["UPI", "Cash", "Cheque", "NACH"]
                        ]}})

    elif outcome == "Refused":
        blocks.append({"type": "input", "block_id": "refusal_reason",
                        "label": {"type": "plain_text", "text": "Reason for Refusal"},
                        "element": {"type": "plain_text_input", "action_id": "refusal_reason_input", "multiline": True}})
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": "On an NPA account, a Refused outcome escalates to Legal automatically."}]})

    elif outcome == "NA":
        blocks.append({"type": "input", "block_id": "revisit_date",
                        "label": {"type": "plain_text", "text": "Schedule Revisit For"},
                        "element": {"type": "datepicker", "action_id": "revisit_date_input"}})
        blocks.append({"type": "input", "block_id": "na_note", "optional": True,
                        "label": {"type": "plain_text", "text": "Note"},
                        "element": {"type": "plain_text_input", "action_id": "na_note_input"}})

    return {
        "type": "modal",
        "callback_id": "visit_modal_submit",
        "private_metadata": channel_id,
        "title": {"type": "plain_text", "text": "Log Field Visit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": blocks,
    }


def deviation_modal(channel_id, queue):
    options = [
        {"text": {"type": "plain_text", "text": f"{q['loan_id']} — {q['product']} — ₹{q['amount']}"}, "value": q["loan_id"]}
        for q in queue
    ]
    return {
        "type": "modal",
        "callback_id": "deviation_modal_submit",
        "private_metadata": channel_id,
        "title": {"type": "plain_text", "text": "Request Deviation Approval"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": [
            {"type": "input", "block_id": "loan", "label": {"type": "plain_text", "text": "Which application?"},
             "element": {"type": "static_select", "action_id": "loan_select", "options": options}},
            {"type": "input", "block_id": "deviation_type", "label": {"type": "plain_text", "text": "Deviation Type"},
             "element": {"type": "static_select", "action_id": "type_select", "options": [
                 {"text": {"type": "plain_text", "text": "CIBIL Score"}, "value": "CIBIL Score"},
                 {"text": {"type": "plain_text", "text": "Income Shortfall"}, "value": "Income Shortfall"},
                 {"text": {"type": "plain_text", "text": "Age Outside Range"}, "value": "Age Outside Range"},
                 {"text": {"type": "plain_text", "text": "LTV Breach"}, "value": "LTV Breach"},
             ]}},
            {"type": "input", "block_id": "detail", "label": {"type": "plain_text", "text": "Deviation Detail"},
             "element": {"type": "plain_text_input", "action_id": "detail_input"}},
            {"type": "input", "block_id": "justification", "label": {"type": "plain_text", "text": "Officer Justification"},
             "element": {"type": "plain_text_input", "action_id": "justification_input", "multiline": True}},
        ],
    }


def lead_modal(channel_id, queue):
    options = [
        {"text": {"type": "plain_text", "text": f"{q['contact_name']} — {q['product_interest']}"}, "value": q["lead_id"]}
        for q in queue
    ]
    return {
        "type": "modal",
        "callback_id": "lead_modal_submit",
        "private_metadata": channel_id,
        "title": {"type": "plain_text", "text": "Log Lead Contact"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": [
            {"type": "input", "block_id": "lead", "label": {"type": "plain_text", "text": "Which lead?"},
             "element": {"type": "static_select", "action_id": "lead_select", "options": options}},
            {"type": "input", "block_id": "outcome", "label": {"type": "plain_text", "text": "Contact Outcome"},
             "element": {"type": "static_select", "action_id": "outcome_select", "options": [
                 {"text": {"type": "plain_text", "text": "Interested"}, "value": "Interested"},
                 {"text": {"type": "plain_text", "text": "Not Reachable"}, "value": "Not Reachable"},
                 {"text": {"type": "plain_text", "text": "Not Eligible"}, "value": "Not Eligible"},
                 {"text": {"type": "plain_text", "text": "Documents Not Ready"}, "value": "Documents Not Ready"},
             ]}},
            {"type": "input", "block_id": "note", "label": {"type": "plain_text", "text": "Rough Eligibility Note"},
             "element": {"type": "plain_text_input", "action_id": "note_input"}},
            {"type": "input", "block_id": "docs", "optional": True, "label": {"type": "plain_text", "text": "Documents Ready"},
             "element": {"type": "multi_static_select", "action_id": "docs_select", "placeholder": {"type": "plain_text", "text": "Select what's ready"},
                         "options": [
                             {"text": {"type": "plain_text", "text": "Aadhaar"}, "value": "Aadhaar"},
                             {"text": {"type": "plain_text", "text": "PAN"}, "value": "PAN"},
                             {"text": {"type": "plain_text", "text": "Income Proof"}, "value": "Income Proof"},
                             {"text": {"type": "plain_text", "text": "Address Proof"}, "value": "Address Proof"},
                         ]}},
        ],
    }
