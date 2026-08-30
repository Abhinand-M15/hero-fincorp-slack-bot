"""
Salesforce is the system of record. Slack is the interaction layer.

Every write in this demo goes through here, so there is exactly one place that
answers "where does the data actually live". Each call produces a SyncRecord —
the literal REST method, path and body — which the bot posts into
#salesforce-sync-log. The customer can therefore watch the write-back happen
rather than take it on trust.

Modes (SF_WRITE_MODE)
  simulate — (default) build and show the exact REST call, do not send it.
             Used because the custom objects below are not yet deployed in the
             demo org; nothing about the flow changes when they are.
  live     — actually send it, using the JWT Bearer connection in sf_auth.py.

Nothing here writes a Slack-side copy of a loan record. Slack holds the
conversation and the action; Salesforce holds the record.
"""
import os

import requests
from dotenv import load_dotenv

from audit_log import log_action

load_dotenv()

WRITE_MODE = os.environ.get("SF_WRITE_MODE", "simulate").strip().lower()
API_VERSION = os.environ.get("SF_API_VERSION", "v61.0")

# Object API names, overridable so the same code points at whatever the HFCL
# org actually calls these once they are built.
VISIT_OBJECT = os.environ.get("HFC_SF_VISIT_OBJECT", "Collections_Visit__c")
PTP_OBJECT = os.environ.get("HFC_SF_PTP_OBJECT", "Promise_To_Pay__c")
CASE_OBJECT = os.environ.get("HFC_SF_CASE_OBJECT", "Case")
APPROVAL_OBJECT = os.environ.get("HFC_SF_APPROVAL_OBJECT", "Credit_Approval_Request__c")
TASK_OBJECT = os.environ.get("HFC_SF_TASK_OBJECT", "Task")


class SyncRecord:
    """One Salesforce interaction, in a form that can be shown on screen."""

    def __init__(self, direction, method, path, body=None, note=""):
        self.direction = direction  # "read" or "write"
        self.method = method
        self.path = path
        self.body = body or {}
        self.note = note
        self.sent = False
        self.result = None
        self.error = None

    def as_curl_ish(self):
        lines = [f"{self.method} /services/data/{API_VERSION}{self.path}"]
        if self.body:
            for key, value in self.body.items():
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def status_line(self):
        if self.error:
            return f"❌ Salesforce error — {self.error}"
        if self.sent:
            record_id = (self.result or {}).get("id", "")
            return f"✅ Written to Salesforce{f' — record {record_id}' if record_id else ''}"
        return "🟡 Simulated — exact call shown above; not sent (SF_WRITE_MODE=simulate)"


def _send(record):
    """Execute a SyncRecord against the org. Only called in live mode."""
    from sf_auth import get_salesforce_token

    token = get_salesforce_token()
    if "access_token" not in token:
        record.error = token.get("error_description") or token.get("error") or "authentication failed"
        return record

    url = f"{token['instance_url']}/services/data/{API_VERSION}{record.path}"
    headers = {"Authorization": f"Bearer {token['access_token']}", "Content-Type": "application/json"}
    try:
        response = requests.request(record.method, url, headers=headers, json=record.body or None, timeout=20)
        payload = response.json() if response.content else {}
        if response.status_code >= 400:
            detail = payload[0] if isinstance(payload, list) and payload else payload
            record.error = f"HTTP {response.status_code} — {detail}"
        else:
            record.sent = True
            record.result = payload if isinstance(payload, dict) else {"records": payload}
    except requests.RequestException as exc:
        record.error = str(exc)
    return record


def _run(record, audit_action, loan_id, actor):
    if WRITE_MODE == "live" and record.direction == "write":
        _send(record)
    log_action(audit_action, loan_id, actor, record.as_curl_ish())
    return record


# ---------- Reads: assignments flow Salesforce -> Slack ----------

def read_assignments_query(agent_id):
    """The SOQL that produces one agent's day. Shown in the demo, not guessed at."""
    return SyncRecord(
        "read", "GET",
        f"/query?q=SELECT+Id,Loan__c,Borrower__c,DPD__c,Amount_Overdue__c+FROM+{TASK_OBJECT}"
        f"+WHERE+Assigned_Partner_Agent__c='{agent_id}'+AND+Status='Open'+AND+ActivityDate=TODAY",
        note=f"Only {agent_id}'s open visits for today are pulled into Slack — not the book.",
    )


# ---------- Writes: outcomes flow Slack -> Salesforce ----------

def write_visit_outcome(task_id, loan_id, outcome, fields, actor):
    body = {"Visit_Task__c": task_id, "Loan__c": loan_id, "Outcome__c": outcome,
            "Logged_By_Partner_Agent__c": actor, **fields}
    record = SyncRecord("write", "POST", f"/sobjects/{VISIT_OBJECT}/", body,
                        note="Visit outcome recorded against the loan in Salesforce.")
    return _run(record, "SF_WRITE_VISIT", loan_id, actor)


def write_promise_to_pay(task_id, loan_id, amount, promised_date, mode, actor):
    body = {"Visit_Task__c": task_id, "Loan__c": loan_id, "Promised_Amount__c": amount,
            "Promised_Date__c": promised_date, "Payment_Mode__c": mode,
            "Captured_By_Partner_Agent__c": actor, "Status__c": "Open"}
    record = SyncRecord("write", "POST", f"/sobjects/{PTP_OBJECT}/", body,
                        note="Promise to pay stored in Salesforce; the Slack reminder is derived from it.")
    return _run(record, "SF_WRITE_PTP", loan_id, actor)


def write_escalation_case(loan_id, reason, actor, bucket, dpd):
    body = {"Subject": f"Collections refusal — {loan_id}", "Origin": "Slack",
            "Type": "Collections Escalation", "Priority": "High",
            "Description": reason, "Loan__c": loan_id, "Bucket__c": bucket,
            "DPD__c": dpd, "Reported_By__c": actor}
    record = SyncRecord("write", "POST", f"/sobjects/{CASE_OBJECT}/", body,
                        note="Refusal opens a Case for internal legal/ops. The agent never sees the Case.")
    return _run(record, "SF_WRITE_ESCALATION", loan_id, actor)


def write_revisit(task_id, loan_id, revisit_date, actor):
    body = {"Status": "Revisit Scheduled", "ActivityDate": revisit_date,
            "Last_Attempt_By__c": actor}
    record = SyncRecord("write", "PATCH", f"/sobjects/{TASK_OBJECT}/{task_id}", body,
                        note="The same Salesforce Task is rescheduled — no duplicate record is created.")
    return _run(record, "SF_WRITE_REVISIT", loan_id, actor)


def write_approval_decision(request_id, loan_id, level, decision, approver, comment):
    body = {"Approval_Level__c": level, "Decision__c": decision,
            "Decided_By__c": approver, "Decision_Comment__c": comment,
            "Decided_In__c": "Slack"}
    record = SyncRecord("write", "PATCH", f"/sobjects/{APPROVAL_OBJECT}/{request_id}", body,
                        note="The decision lands on the originating LOS request; the requester is notified from there.")
    return _run(record, "SF_WRITE_APPROVAL", loan_id, approver)


def write_nudge_event(agent_id, nudge_key, actor="system"):
    body = {"Partner_Agent__c": agent_id, "Nudge_Type__c": nudge_key,
            "Channel__c": "Slack"}
    record = SyncRecord("write", "POST", "/sobjects/Agent_Nudge__c/", body,
                        note="Nudges are logged too, so 'was the agent chased?' is answerable from Salesforce.")
    return _run(record, "SF_WRITE_NUDGE", "-", actor)


# ---------- Live connectivity proof ----------

def probe():
    """
    Real call against the org, used in the demo to show the connection is not a
    mock. Uses /limits because it needs no custom schema.
    """
    from sf_auth import get_salesforce_token

    token = get_salesforce_token()
    if "access_token" not in token:
        return False, token.get("error_description") or token.get("error") or "auth failed", None

    url = f"{token['instance_url']}/services/data/{API_VERSION}/limits"
    try:
        response = requests.get(url, headers={"Authorization": f"Bearer {token['access_token']}"}, timeout=20)
        if response.status_code >= 400:
            return False, f"HTTP {response.status_code} — {response.text[:200]}", token.get("instance_url")
        limits = response.json()
        api_used = limits.get("DailyApiRequests", {})
        return True, f"API calls used today: {api_used.get('Max', 0) - api_used.get('Remaining', 0)} of {api_used.get('Max', 0)}", token.get("instance_url")
    except requests.RequestException as exc:
        return False, str(exc), token.get("instance_url")


if __name__ == "__main__":
    ok, detail, instance = probe()
    print("SALESFORCE CONNECTION:", "OK" if ok else "FAILED")
    print("instance_url:", instance)
    print(detail)
    print("write mode:", WRITE_MODE)
