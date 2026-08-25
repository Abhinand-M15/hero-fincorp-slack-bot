"""
Remembers which channel/message the 'assignment queue' card lives at, so
that after someone acts on an item we can refresh that same card in place
instead of leaving a stale list behind.
"""
import json
import os

STATE_PATH = os.path.join(os.path.dirname(__file__), "queue_state.json")


def _load():
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f)


def remember_queue_message(key, channel_id, ts):
    state = _load()
    state[key] = {"channel": channel_id, "ts": ts}
    _save(state)


def get_queue_message(key):
    state = _load()
    return state.get(key)
