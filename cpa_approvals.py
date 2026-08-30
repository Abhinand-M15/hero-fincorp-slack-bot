"""
CPA approvals — a request raised in Salesforce/LOS, decided in Slack, written
back to Salesforce.

  NOTE ON THE ACRONYM
  The HFCL discovery call referred to this as the "CPA use case" without
  expanding it. This demo shows it as "CPA Approval" and keeps the expansion in
  one constant so it is a one-line change once HFCL confirms whether CPA means
  Credit Policy Approval, Credit Proposal Approval, or something else in their
  vocabulary. Nothing else in the code depends on the wording.

Flow
  LOS/Salesforce raises the request
    -> routed to the correct approver for its value band (1, 2 or 3 levels)
    -> that approver, and only that approver, sees it in a private channel
       with the full detail, the officer's justification and the supporting
       documents attached
    -> one click to approve or reject
    -> on approve at a non-final level it moves to the next approver
    -> the final decision is written back to Salesforce and the requester is
       notified
"""
import os

from dotenv import load_dotenv

import journey_state
import personas

load_dotenv()

# Unconfirmed — see the note above. Confirm with HFCL before the demo.
CPA_EXPANSION = os.environ.get("HFC_CPA_EXPANSION", "Credit Policy Approval")
CPA_EXPANSION_CONFIRMED = os.environ.get("HFC_CPA_EXPANSION_CONFIRMED", "false").lower() == "true"


def cpa_label(long_form=False):
    if not long_form:
        return "CPA Approval"
    suffix = "" if CPA_EXPANSION_CONFIRMED else " — expansion to be confirmed with HFCL"
    return f"CPA Approval ({CPA_EXPANSION}{suffix})"


# ---------- Routing: value band decides how many levels are needed ----------

L1, L2, L3 = "CPA-L1", "CPA-L2", "CPA-L3"

ROUTING_RULES = [
    {"max_amount": 500000, "chain": [L1],
     "why": "Up to ₹5L — single-level approval by the Credit Manager"},
    {"max_amount": 2500000, "chain": [L1, L2],
     "why": "₹5L–₹25L — Credit Manager, then Credit Head"},
    {"max_amount": None, "chain": [L1, L2, L3],
     "why": "Above ₹25L — Credit Manager, Credit Head, then Chief Risk Officer"},
]

# Conditions that add a level regardless of ticket size.
ESCALATING_DEVIATIONS = {"LTV Breach", "Negative Profile Match"}


def route(amount, deviations):
    """Returns (chain, reason). Deterministic, so it can be explained on screen."""
    rule = next(r for r in ROUTING_RULES if r["max_amount"] is None or amount <= r["max_amount"])
    chain = list(rule["chain"])
    reason = rule["why"]

    severe = [d for d in deviations if d["type"] in ESCALATING_DEVIATIONS]
    if severe and len(chain) < 3:
        chain.append(L2 if L2 not in chain else L3)
        reason += f"; one level added for {severe[0]['type']}"
    if len(deviations) >= 3 and len(chain) < 3:
        chain.append(L2 if L2 not in chain else L3)
        reason += "; one level added for three or more deviations"

    # Keep the chain in seniority order no matter which rules fired.
    order = {L1: 0, L2: 1, L3: 2}
    chain = sorted(set(chain), key=lambda p: order[p])
    return chain, reason


APPROVED = "APPROVED"
REJECTED = "REJECTED"
PENDING = "PENDING"


class CPARequest:
    def __init__(self, data):
        self.__dict__.update(data)
        self.chain = data.get("chain") or []
        self.decisions = data.get("decisions") or []
        self.status = data.get("status", PENDING)
        self.level_index = data.get("level_index", 0)

    # -- routing state --

    def current_level(self):
        return self.level_index + 1

    def total_levels(self):
        return len(self.chain)

    def current_approver(self):
        if self.status != PENDING or self.level_index >= len(self.chain):
            return None
        return personas.INTERNAL_STAFF[self.chain[self.level_index]]

    def approver_at(self, index):
        return personas.INTERNAL_STAFF[self.chain[index]]

    def is_final_level(self):
        return self.level_index == len(self.chain) - 1

    def channel_for_current_level(self):
        """L1 has its own queue; L2 and L3 share the senior queue."""
        return "cpa-approvals-l1" if self.level_index == 0 else "cpa-approvals-l2"

    # -- transitions --

    def approve(self, approver_name, comment=""):
        self.decisions.append({"level": self.current_level(), "decision": APPROVED,
                               "by": approver_name, "comment": comment})
        if self.is_final_level():
            self.status = APPROVED
        else:
            self.level_index += 1
        self.save()
        return self.status

    def reject(self, approver_name, comment=""):
        self.decisions.append({"level": self.current_level(), "decision": REJECTED,
                               "by": approver_name, "comment": comment})
        self.status = REJECTED
        self.save()
        return self.status

    # -- persistence (Slack-side routing state only; the record lives in Salesforce) --

    def to_dict(self):
        data = dict(self.__dict__)
        return data

    def save(self):
        journey_state.save_cpa_state(self.request_id, self.to_dict())

    def chain_summary(self):
        parts = []
        for index, person_id in enumerate(self.chain):
            person = personas.INTERNAL_STAFF[person_id]
            decision = next((d for d in self.decisions if d["level"] == index + 1), None)
            if decision:
                mark = "✅" if decision["decision"] == APPROVED else "❌"
                parts.append(f"{mark} L{index + 1} {person['name']}")
            elif self.status == PENDING and index == self.level_index:
                parts.append(f"🟡 L{index + 1} {person['name']} — with them now")
            else:
                parts.append(f"⚪ L{index + 1} {person['name']}")
        return "  →  ".join(parts)

    def deviation_lines(self):
        return "\n".join(f"• *{d['type']}* — {d['detail']}" for d in self.deviations)


# ---------- Requests raised in Salesforce/LOS, waiting in Slack ----------

def _seed():
    return [
        {
            "request_id": "CPA-2026-00417",
            "los_reference": "LOS/APP/2026/118904",
            "loan_id": "HFCL/PL/2026/01590",
            "applicant": "Deepak Yadav",
            "product": "Personal Loan",
            "amount": 450000,
            "los_stage": "Credit Underwriting — held for policy exception",
            "deviations": [{"type": "CIBIL Score", "detail": "640 against 700 preferred"}],
            "justification": ("Existing loyalty customer. 14 on-time two-wheeler EMIs, zero bounces. "
                              "Requesting a top-up against the same income profile."),
            "requester": "Branch Credit Officer, Pune Cluster",
            "requester_persona": "MGR-COLL-01",
            "attachments": ["cibil_summary.pdf", "repayment_history.pdf"],
        },
        {
            "request_id": "CPA-2026-00418",
            "los_reference": "LOS/APP/2026/118921",
            "loan_id": "HFCL/LAP/2026/00203",
            "applicant": "Kavya Enterprises",
            "product": "Loan Against Property",
            "amount": 6200000,
            "los_stage": "Credit Underwriting — LTV exception",
            "deviations": [
                {"type": "LTV Breach", "detail": "78% requested against a 75% cap for residential"},
                {"type": "Income Shortfall", "detail": "Latest ITR 12% below the policy minimum"},
            ],
            "justification": ("Prime-location property with a strong resale comparable. Applicant has a "
                              "clean five-year repayment record on an existing LAP. The ITR dip traces to "
                              "a one-time GST filing correction."),
            "requester": "Branch Credit Officer, Ahmedabad Cluster",
            "requester_persona": "MGR-COLL-01",
            "attachments": ["property_valuation.pdf", "itr_extract.pdf", "bank_statement.pdf"],
        },
        {
            "request_id": "CPA-2026-00420",
            "los_reference": "LOS/APP/2026/118933",
            "loan_id": "HFCL/BL/2026/00389",
            "applicant": "Verma Traders",
            "product": "Business Loan",
            "amount": 1800000,
            "los_stage": "Credit Underwriting — turnover exception",
            "deviations": [{"type": "Income Shortfall", "detail": "Turnover 15% below the policy minimum on the latest ITR"}],
            "justification": ("Turnover dip traces to a one-time GST filing correction. Current-year provisional "
                              "figures are back above the policy minimum, and the GST returns support it."),
            "requester": "Branch Credit Officer, Lucknow Cluster",
            "requester_persona": "MGR-COLL-01",
            "attachments": ["itr_extract.pdf", "bank_statement.pdf"],
        },
        {
            "request_id": "CPA-2026-00419",
            "los_reference": "LOS/APP/2026/118940",
            "loan_id": "HFCL/TW/2026/00915",
            "applicant": "Arjun Deshmukh",
            "product": "Two-Wheeler Loan",
            "amount": 120000,
            "los_stage": "Credit Underwriting — income exception",
            "deviations": [{"type": "Income Shortfall", "detail": "₹8,500/month against a ₹10,000 minimum"}],
            "justification": ("Seasonal income. Six-month averaged bank statement shows consistent inflow "
                              "above the threshold."),
            "requester": "Branch Credit Officer, Nashik Cluster",
            "requester_persona": "MGR-COLL-01",
            "attachments": ["bank_statement.pdf"],
        },
    ]


def _hydrate(data):
    chain, reason = route(data["amount"], data["deviations"])
    data.setdefault("chain", chain)
    data.setdefault("routing_reason", reason)
    return CPARequest(data)


def all_requests():
    """Seed data, overlaid with any decisions already taken in this session."""
    requests = []
    for data in _seed():
        saved = journey_state.cpa_state(data["request_id"])
        requests.append(CPARequest(saved) if saved else _hydrate(data))
    return requests


def get_request(request_id):
    return next((r for r in all_requests() if r.request_id == request_id), None)


def pending_for_approver(person_id):
    return [r for r in all_requests()
            if r.status == PENDING and r.current_approver()
            and r.current_approver()["person_id"] == person_id]


def pending_all():
    return [r for r in all_requests() if r.status == PENDING]
