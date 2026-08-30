"""
Per-day state for the collections journey: which partner agent started work,
what they have logged, where the live cards live so they can be updated in
place, and which nudges have already fired (so an agent is never nudged twice
for the same thing).

Slack is the interaction layer, not the database — this file exists only so a
card can be refreshed and a nudge de-duplicated between process restarts.
Salesforce remains the system of record for every outcome; see sf_bridge.py.
"""
import json
import os
import threading
from datetime import datetime, timezone

STATE_PATH = os.path.join(os.path.dirname(__file__), "journey_state.json")
_LOCK = threading.Lock()


def _blank():
    return {"date": None, "agents": {}, "cards": {}, "nudges": {}, "cpa": {}}


def load():
    if not os.path.exists(STATE_PATH):
        return _blank()
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _blank()
    for key, default in _blank().items():
        state.setdefault(key, default)
    return state


def save(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _now():
    return datetime.now(timezone.utc).isoformat()


def agent_state(agent_id):
    return load()["agents"].get(agent_id, {"started_at": None, "items": {}})


def mark_started(agent_id):
    with _LOCK:
        state = load()
        entry = state["agents"].setdefault(agent_id, {"started_at": None, "items": {}})
        if not entry["started_at"]:
            entry["started_at"] = _now()
        save(state)
        return entry["started_at"]


def record_outcome(agent_id, task_id, outcome, detail, actor):
    with _LOCK:
        state = load()
        entry = state["agents"].setdefault(agent_id, {"started_at": None, "items": {}})
        if not entry["started_at"]:
            entry["started_at"] = _now()
        entry["items"][task_id] = {
            "status": "logged",
            "outcome": outcome,
            "detail": detail,
            "actor": actor,
            "logged_at": _now(),
        }
        save(state)
        return entry["items"][task_id]


def logged_items(agent_id):
    return agent_state(agent_id).get("items", {})


def remember_card(key, channel_id, ts):
    with _LOCK:
        state = load()
        state["cards"][key] = {"channel": channel_id, "ts": ts}
        save(state)


def get_card(key):
    return load()["cards"].get(key)


def nudge_already_sent(agent_id, nudge_key):
    return nudge_key in load()["nudges"].get(agent_id, [])


def mark_nudge_sent(agent_id, nudge_key):
    with _LOCK:
        state = load()
        state["nudges"].setdefault(agent_id, [])
        if nudge_key not in state["nudges"][agent_id]:
            state["nudges"][agent_id].append(nudge_key)
        save(state)


def cpa_state(request_id):
    return load()["cpa"].get(request_id, {})


def save_cpa_state(request_id, data):
    with _LOCK:
        state = load()
        state["cpa"][request_id] = data
        save(state)


def reset():
    """Wipe the day's state — used by the demo reset script."""
    save(_blank())
