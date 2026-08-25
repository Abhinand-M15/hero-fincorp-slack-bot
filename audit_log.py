"""
Local audit trail for every button action taken. This is a stand-in for the
Salesforce write-back — writing to a real loan record requires the object
schema to exist in the org first, which hasn't been built for this demo.
"""
import json
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(__file__), "audit_log.jsonl")


def log_action(action, loan_id, actor, detail=""):
    entry = {
        "action": action,
        "loan_id": loan_id,
        "actor": actor,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry
