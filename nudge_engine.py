"""
The automated nudge: if a partner agent has not started, or has not finished,
the day's assigned work, Slack chases them — and if the day closes with work
still unrecorded, their Hero FinCorp manager is told.

Checkpoints (local time, overridable)
    11:00  nothing recorded yet          -> nudge the agent
    15:00  still has open visits         -> nudge the agent
    18:00  still has open visits         -> final nudge + manager escalation

Each nudge fires once per agent per day; journey_state.py remembers what has
already been sent. Every nudge is also written back to Salesforce, so
"was the agent chased, and when?" is answerable from the system of record.

Usage
    ./venv/bin/python nudge_engine.py                 # run the checkpoints due right now
    ./venv/bin/python nudge_engine.py --at 11:00      # force a checkpoint, for a live demo
    ./venv/bin/python nudge_engine.py --watch 300     # keep checking every 5 minutes
    ./venv/bin/python nudge_engine.py --dry-run       # show what would be sent
"""
import argparse
import os
import time
from datetime import datetime

from dotenv import load_dotenv

import blocks_journey as bj
import collections_journey as journey
import journey_state
import personas
import sf_bridge
from audit_log import log_action
from slack_client import find_channel_id, post_message

load_dotenv()

CONTROL_ROOM = "collections-control-room"

CHECKPOINTS = [
    {"key": bj.NUDGE_NOT_STARTED, "at": os.environ.get("HFC_NUDGE_START", "11:00"),
     "label": "11:00", "applies": lambda p: not p["started"] and p["pending"] > 0,
     "escalate": False},
    {"key": bj.NUDGE_BEHIND, "at": os.environ.get("HFC_NUDGE_MIDDAY", "15:00"),
     "label": "15:00", "applies": lambda p: p["pending"] > 0, "escalate": False},
    {"key": bj.NUDGE_END_OF_DAY, "at": os.environ.get("HFC_NUDGE_END", "18:00"),
     "label": "18:00", "applies": lambda p: p["pending"] > 0, "escalate": True},
]


def _as_minutes(hhmm):
    hours, _, minutes = hhmm.partition(":")
    return int(hours) * 60 + int(minutes)


def due_checkpoints(now=None, forced=None):
    if forced:
        return [c for c in CHECKPOINTS if c["at"] == forced or c["label"] == forced or c["key"] == forced]
    now = now or datetime.now()
    minutes_now = now.hour * 60 + now.minute
    return [c for c in CHECKPOINTS if minutes_now >= _as_minutes(c["at"])]


def run_once(forced=None, dry_run=False, now=None):
    """Returns a list of human-readable lines describing what fired."""
    fired = []
    checkpoints = due_checkpoints(now=now, forced=forced)
    if not checkpoints:
        return ["No checkpoint is due yet."]

    for agent in personas.PARTNER_AGENTS.values():
        progress = journey.progress(agent["agent_id"])

        for checkpoint in checkpoints:
            if not checkpoint["applies"](progress):
                continue
            if journey_state.nudge_already_sent(agent["agent_id"], checkpoint["key"]):
                continue

            text, blocks = bj.nudge_card(agent, checkpoint["key"], progress, checkpoint["label"])
            line = (f"{checkpoint['label']} · {agent['name']} · {checkpoint['key']} "
                    f"({progress['logged']}/{progress['assigned']} recorded)")

            if dry_run:
                fired.append(f"[dry run] {line}")
                continue

            channel_id = find_channel_id(agent["channel"])
            if not channel_id:
                fired.append(f"[skipped — #{agent['channel']} not found] {line}")
                continue

            post_message(channel_id, text=text, blocks=blocks)
            journey_state.mark_nudge_sent(agent["agent_id"], checkpoint["key"])
            sync = sf_bridge.write_nudge_event(agent["agent_id"], checkpoint["key"])
            log_action("NUDGE_SENT", "-", "system", f"{agent['agent_id']} {checkpoint['key']}")

            if checkpoint["escalate"]:
                control_room = find_channel_id(CONTROL_ROOM)
                if control_room:
                    mgr_text, mgr_blocks = bj.manager_nudge_escalation(agent, progress, checkpoint["label"])
                    post_message(control_room, text=mgr_text, blocks=mgr_blocks)
                    log_action("NUDGE_ESCALATED_TO_MANAGER", "-", "system", agent["agent_id"])
                    line += " + manager escalation"

            sync_channel = find_channel_id("salesforce-sync-log")
            if sync_channel:
                import blocks_security as bs
                sync_text, sync_blocks = bs.sf_sync_card(sync, f"Nudge logged for {agent['name']}")
                post_message(sync_channel, text=sync_text, blocks=sync_blocks)

            fired.append(line)

    return fired or ["Every partner agent is up to date — nothing to nudge."]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nudge partner agents who have not started or finished their day.")
    parser.add_argument("--at", help="force a checkpoint: 11:00, 15:00, 18:00, or its key")
    parser.add_argument("--watch", type=int, metavar="SECONDS", help="keep checking on this interval")
    parser.add_argument("--dry-run", action="store_true", help="show what would be sent, send nothing")
    args = parser.parse_args()

    while True:
        for entry in run_once(forced=args.at, dry_run=args.dry_run):
            print(f"{datetime.now().strftime('%d %b %Y, %H:%M')}  {entry}")
        if not args.watch:
            break
        time.sleep(args.watch)
