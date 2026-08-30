"""
The collections journey, from the external partner agent's point of view.

    Salesforce assigns the work  ->  the agent sees only their own list in Slack
    ->  the agent records the visit outcome on a form
    ->  the outcome is written back to Salesforce
    ->  the right follow-up, reminder or escalation fires automatically
    ->  the manager sees progress; the agent never sees another agent's work

ASSIGNMENTS below is the slice of Salesforce that reaches Slack for one day.
It is deliberately small: Salesforce may hold 150,000-200,000 records a day,
but what lands in Slack is one agent's actionable visits for one day. Slack is
never asked to be the store of record — see sf_bridge.py and
canvas_content_architecture.py.
"""
from datetime import date, timedelta

import journey_state

# ---------- Outcomes the agent can record ----------

PAID = "PAID"
PTP = "PTP"
REFUSED = "REFUSED"
UNAVAILABLE = "UNAVAILABLE"

OUTCOME_LABELS = {
    PAID: "Payment collected",
    PTP: "Promise to pay",
    REFUSED: "Refused to pay",
    UNAVAILABLE: "Customer unavailable",
}

OUTCOME_EMOJI = {PAID: "✅", PTP: "🤝", REFUSED: "⛔", UNAVAILABLE: "🚪"}

# ---------- Today's assignments, pushed from Salesforce ----------
# task_id mirrors the Salesforce Task/Visit record ID that owns this row.

ASSIGNMENTS = [
    # --- Rakesh Sharma, external partner, Kothrud showroom, Pune ---
    {"task_id": "SFT-0001", "agent_id": "AG-PUNE-01", "loan_id": "HFCL/TW/2026/00891",
     "borrower": "Ramesh Kumar", "product": "Two-Wheeler Loan", "bucket": "Bucket 2",
     "dpd": 42, "overdue": 4500, "locality": "Kothrud, Pune", "phone": "+91 ·····4471"},
    {"task_id": "SFT-0002", "agent_id": "AG-PUNE-01", "loan_id": "HFCL/PL/2026/01301",
     "borrower": "Ashwini More", "product": "Personal Loan", "bucket": "Bucket 2",
     "dpd": 45, "overdue": 13500, "locality": "Karve Nagar, Pune", "phone": "+91 ·····2093"},
    {"task_id": "SFT-0003", "agent_id": "AG-PUNE-01", "loan_id": "HFCL/UC/2026/00611",
     "borrower": "Ganesh Pawar", "product": "Used Car Loan", "bucket": "Bucket 2",
     "dpd": 33, "overdue": 15800, "locality": "Warje, Pune", "phone": "+91 ·····8810"},
    {"task_id": "SFT-0004", "agent_id": "AG-PUNE-01", "loan_id": "HFCL/CD/2026/00220",
     "borrower": "Snehal Joshi", "product": "Consumer Durable Loan", "bucket": "Bucket 2",
     "dpd": 50, "overdue": 8400, "locality": "Bavdhan, Pune", "phone": "+91 ·····6127"},

    # --- Imran Qureshi, extended workforce, Aliganj branch, Lucknow ---
    {"task_id": "SFT-0005", "agent_id": "AG-LKO-02", "loan_id": "HFCL/PL/2026/01204",
     "borrower": "Sunita Devi", "product": "Personal Loan", "bucket": "Bucket 3",
     "dpd": 68, "overdue": 27000, "locality": "Aliganj, Lucknow", "phone": "+91 ·····5502"},
    {"task_id": "SFT-0006", "agent_id": "AG-LKO-02", "loan_id": "HFCL/BL/2026/00344",
     "borrower": "Verma Traders", "product": "Business Loan", "bucket": "Bucket 3",
     "dpd": 81, "overdue": 124000, "locality": "Hazratganj, Lucknow", "phone": "+91 ·····7734"},
    {"task_id": "SFT-0007", "agent_id": "AG-LKO-02", "loan_id": "HFCL/PL/2026/01277",
     "borrower": "Mohd. Irfan", "product": "Personal Loan", "bucket": "Bucket 3",
     "dpd": 89, "overdue": 36000, "locality": "Chowk, Lucknow", "phone": "+91 ·····1188"},
    {"task_id": "SFT-0008", "agent_id": "AG-LKO-02", "loan_id": "HFCL/UC/2026/00588",
     "borrower": "Anita Singh", "product": "Used Car Loan", "bucket": "Bucket 3",
     "dpd": 65, "overdue": 35000, "locality": "Gomti Nagar, Lucknow", "phone": "+91 ·····9046"},
]


def assignments_for(agent_id):
    """Every account assigned to this agent today — and nobody else's."""
    return [a for a in ASSIGNMENTS if a["agent_id"] == agent_id]


def assignment(task_id):
    return next((a for a in ASSIGNMENTS if a["task_id"] == task_id), None)


def assignment_by_loan(loan_id):
    return next((a for a in ASSIGNMENTS if a["loan_id"] == loan_id), None)


def owner_of(task_id):
    entry = assignment(task_id)
    return entry["agent_id"] if entry else None


def pending_for(agent_id):
    """Assigned but not yet logged."""
    done = journey_state.logged_items(agent_id)
    return [a for a in assignments_for(agent_id) if a["task_id"] not in done]


def progress(agent_id):
    assigned = assignments_for(agent_id)
    logged = journey_state.logged_items(agent_id)
    state = journey_state.agent_state(agent_id)
    counts = {"assigned": len(assigned), "logged": len(logged)}
    counts["pending"] = counts["assigned"] - counts["logged"]
    counts["started"] = bool(state.get("started_at"))
    counts["started_at"] = state.get("started_at")
    counts["outcomes"] = {}
    for item in logged.values():
        counts["outcomes"][item["outcome"]] = counts["outcomes"].get(item["outcome"], 0) + 1
    counts["collected"] = sum(
        item.get("amount", 0) for item in logged.values() if item["outcome"] == PAID
    )
    counts["last_activity"] = max(
        (item["logged_at"] for item in logged.values()), default=state.get("started_at")
    )
    return counts


# ---------- What happens after each outcome ----------

FOLLOW_UP_RULES = {
    PAID: {
        "salesforce": "Payment_Collected__c + Task closed",
        "follow_up": "Receipt confirmation to the customer; agent asked to attach payment proof",
        "escalates": False,
    },
    PTP: {
        "salesforce": "Promise_To_Pay__c created with promised amount, date and mode",
        "follow_up": "Reminder scheduled to the same agent the day before the promised date",
        "escalates": False,
    },
    REFUSED: {
        "salesforce": "Escalation Case created, Task closed as Refused",
        "follow_up": "Routed to HFCL internal legal/ops for a Proceed or Hold decision",
        "escalates": True,
    },
    UNAVAILABLE: {
        "salesforce": "Visit_Attempt__c logged, revisit date set on the Task",
        "follow_up": "Revisit scheduled; a second consecutive miss on the same account goes to the manager",
        "escalates": False,
    },
}


def follow_up_for(outcome):
    return FOLLOW_UP_RULES[outcome]


def ptp_reminder_date(promised_date_str):
    """Remind the agent the day before the promise falls due."""
    promised = date.fromisoformat(promised_date_str)
    return max(promised - timedelta(days=1), date.today())


def missed_twice(agent_id, task_id):
    """Second consecutive 'customer unavailable' on the same account."""
    item = journey_state.logged_items(agent_id).get(task_id)
    return bool(item and item.get("outcome") == UNAVAILABLE and item.get("repeat_miss"))
