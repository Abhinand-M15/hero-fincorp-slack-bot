"""
Collections journey handlers — the external partner agent's day, end to end.

    assignment in Slack -> form -> Salesforce write-back -> follow-up -> manager view

Every entry point re-checks authorisation in access.py before it does anything,
so the isolation between two partner agents holds at the record level and not
only at the channel level.
"""
import os
from datetime import datetime, time, timedelta, timezone

from dotenv import load_dotenv

import access
import blocks_journey as bj
import blocks_security as bs
import collections_journey as journey
import journey_state
import personas
import sf_bridge
import slack_util as su
from audit_log import log_action
from fmt import human_date, rupees

load_dotenv()

DEMO_FAST = os.environ.get("HFC_DEMO_FAST", "false").strip().lower() == "true"
REMINDER_HOUR = int(os.environ.get("HFC_REMINDER_HOUR", "9"))

CONTROL_ROOM = "collections-control-room"
LEGAL_OPS = "collections-legal-ops"
SYNC_LOG = "salesforce-sync-log"


# ---------- shared plumbing ----------

def show_sync(client, sync_record, context_line):
    """Every Salesforce interaction is echoed where the customer can watch it."""
    text, blocks = bs.sf_sync_card(sync_record, context_line)
    su.post_to(client, SYNC_LOG, text, blocks)


def deny(client, channel, user, reason, what):
    log_action("ACCESS_DENIED", what, user, reason.split("\n")[0])
    su.ephemeral(client, channel, user, "Access denied", bs.denial_notice(reason))


def refresh_day_card(client, agent):
    card = journey_state.get_card(f"day:{agent['agent_id']}")
    if not card:
        return
    pending = journey.pending_for(agent["agent_id"])
    progress = journey.progress(agent["agent_id"])
    text, blocks = bj.agent_day_card(agent, pending or journey.assignments_for(agent["agent_id"]), progress)
    if not pending:
        blocks.insert(3, {"type": "section", "text": {"type": "mrkdwn", "text":
            "🎉 *Every assigned visit for today has been recorded.* Nothing further is pending on you."}})
    try:
        client.chat_update(channel=card["channel"], ts=card["ts"], text=text, blocks=blocks)
    except Exception as exc:
        print(f"DAY CARD REFRESH FAILED: {exc}")


def refresh_activity_board(client):
    rows = [(agent, journey.progress(agent["agent_id"])) for agent in personas.PARTNER_AGENTS.values()]
    text, blocks = bj.activity_board(rows)
    card = journey_state.get_card("activity_board")
    if card:
        try:
            client.chat_update(channel=card["channel"], ts=card["ts"], text=text, blocks=blocks)
            return
        except Exception:
            pass
    result = su.post_to(client, CONTROL_ROOM, text, blocks)
    if result and result.get("ok"):
        journey_state.remember_card("activity_board", result["channel"], result["ts"])


def _schedule_at(target_date, hour=None):
    """Unix timestamp for a reminder — compressed to ~90 seconds in demo mode."""
    if DEMO_FAST:
        return int((datetime.now(timezone.utc) + timedelta(seconds=90)).timestamp())
    when = datetime.combine(target_date, time(hour if hour is not None else REMINDER_HOUR, 30))
    stamp = when.astimezone().timestamp()
    floor = datetime.now(timezone.utc).timestamp() + 60
    return int(max(stamp, floor))


def _schedule_reminder(client, channel_id, post_at, text, blocks=None):
    try:
        payload = {"channel": channel_id, "post_at": post_at, "text": text}
        if blocks:
            payload["blocks"] = blocks
        result = client.chat_scheduleMessage(**payload)
        return result.get("ok", False)
    except Exception as exc:
        print(f"SCHEDULE FAILED: {exc}")
        return False


# ---------- registration ----------

def register(app):

    # --- the agent's day ---

    @app.action("agent_start_day")
    def start_day(ack, body, client):
        ack()
        channel = body["channel"]["id"]
        user = body["user"]["id"]
        name = su.channel_name(client, channel)
        actor = access.resolve_actor(user, name)

        if actor.kind == access.UNKNOWN:
            deny(client, channel, user, ":lock: *Access denied.* Your account is not mapped to a partner agent.", "-")
            return

        agent = actor.agent or personas.PARTNER_AGENTS[body["actions"][0]["value"]]
        started_at = journey_state.mark_started(agent["agent_id"])
        log_action("AGENT_DAY_STARTED", "-", agent["name"], f"{len(journey.assignments_for(agent['agent_id']))} visits")

        query = sf_bridge.read_assignments_query(agent["agent_id"])
        show_sync(client, query, f"{agent['name']} started the day — assignments pulled from Salesforce")

        client.chat_postMessage(
            channel=channel,
            text="Day started",
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text":
                    f"▶️ *Day started* — {len(journey.assignments_for(agent['agent_id']))} visits assigned to you "
                    f"for {human_date(datetime.now().date())}."}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text":
                    "Your manager can see that you have started. Record each outcome as you go — you do not have to wait until the end of the day."}]},
            ],
        )
        refresh_activity_board(client)

    @app.action("open_outcome_modal")
    def open_outcome(ack, body, client):
        ack()
        channel = body["channel"]["id"] if body.get("channel") else None
        user = body["user"]["id"]
        name = su.channel_name(client, channel) if channel else None
        assignments, actor = access.visible_assignments(user, name)

        if not assignments:
            deny(client, channel, user,
                 ":lock: *Nothing is assigned to you.* This form only offers the accounts assigned to your agent ID.", "-")
            return

        agent_id = actor.agent_id or body["actions"][0].get("value")
        scope = [a for a in assignments if not agent_id or a["agent_id"] == agent_id]
        pending = [a for a in scope if a["task_id"] not in journey_state.logged_items(a["agent_id"])]
        client.views_open(
            trigger_id=body["trigger_id"],
            view=bj.outcome_modal(channel, agent_id, pending or scope),
        )

    @app.action("outcome_select")
    def outcome_changed(ack, body, client):
        ack()
        meta = bj.read_meta(body["view"]["private_metadata"])
        values = body["view"]["state"]["values"]
        selected_task = values.get("task", {}).get("task_select", {}).get("selected_option", {}).get("value")
        new_outcome = body["actions"][0]["selected_option"]["value"]

        channel_name = su.channel_name(client, meta["channel"]) if meta.get("channel") else None
        assignments, actor = access.visible_assignments(body["user"]["id"], channel_name)
        agent_id = meta.get("agent") or actor.agent_id
        scope = [a for a in assignments if not agent_id or a["agent_id"] == agent_id]
        pending = [a for a in scope if a["task_id"] not in journey_state.logged_items(a["agent_id"])]

        client.views_update(
            view_id=body["view"]["id"],
            view=bj.outcome_modal(meta.get("channel"), agent_id, pending or scope,
                                  selected_task=selected_task, outcome=new_outcome),
        )

    @app.view("outcome_modal_submit")
    def submit_outcome(ack, body, client, view):
        meta = bj.read_meta(view["private_metadata"])
        channel = meta.get("channel")
        user = body["user"]["id"]
        values = view["state"]["values"]

        task_id = values["task"]["task_select"]["selected_option"]["value"]
        outcome = values["outcome"]["outcome_select"]["selected_option"]["value"]

        channel_name = su.channel_name(client, channel) if channel else None
        allowed, reason, actor = access.check_task_access(user, task_id, channel_name)
        if not allowed:
            log_action("ACCESS_DENIED", task_id, su.actor_name(client, user), reason.split("\n")[0])
            ack(response_action="errors", errors={
                "task": "This account is assigned to a different partner agent. You can only record outcomes for your own accounts."
            })
            return

        ack()
        task = journey.assignment(task_id)
        agent = personas.PARTNER_AGENTS[task["agent_id"]]
        actor_label = actor.name if actor.kind == access.AGENT else su.actor_name(client, user)

        detail, sync_record, extras = _apply_outcome(client, task, agent, outcome, values, actor_label)

        journey_state.record_outcome(task["agent_id"], task_id, outcome, detail, actor_label)
        if outcome == journey.PAID:
            state = journey_state.load()
            state["agents"][task["agent_id"]]["items"][task_id]["amount"] = extras.get("amount", 0)
            journey_state.save(state)

        follow_up = journey.follow_up_for(outcome)
        text, blocks = bj.outcome_receipt_card(agent, task, outcome, detail, sync_record, follow_up)
        if channel:
            client.chat_postMessage(channel=channel, text=text, blocks=blocks)

        show_sync(client, sync_record, f"{agent['name']} recorded {journey.OUTCOME_LABELS[outcome]} on `{task['loan_id']}`")
        log_action("VISIT_OUTCOME", task["loan_id"], actor_label, f"{outcome} — {detail}")

        for follow_text, follow_blocks in extras.get("agent_messages", []):
            if channel:
                client.chat_postMessage(channel=channel, text=follow_text, blocks=follow_blocks)

        refresh_day_card(client, agent)
        refresh_activity_board(client)

    @app.action("agent_progress")
    def show_progress(ack, body, client):
        ack()
        channel = body["channel"]["id"]
        user = body["user"]["id"]
        name = su.channel_name(client, channel)
        assignments, actor = access.visible_assignments(user, name)
        agent = actor.agent or personas.PARTNER_AGENTS.get(body["actions"][0]["value"])
        if not agent:
            deny(client, channel, user, ":lock: *Access denied.* No agent record is mapped to your account.", "-")
            return
        mine = [a for a in assignments if a["agent_id"] == agent["agent_id"]]
        client.views_open(
            trigger_id=body["trigger_id"],
            view=bj.agent_progress_view(agent, mine, journey.progress(agent["agent_id"])),
        )

    # --- manager view ---

    @app.action("refresh_activity_board")
    def manager_refresh(ack, body, client):
        ack()
        allowed, reason, _ = access.check_internal(body["user"]["id"], su.channel_name(client, body["channel"]["id"]))
        if not allowed:
            deny(client, body["channel"]["id"], body["user"]["id"], reason, "-")
            return
        refresh_activity_board(client)

    @app.action("nudge_all_behind")
    def manager_nudge_all(ack, body, client):
        ack()
        channel = body["channel"]["id"]
        allowed, reason, _ = access.check_internal(body["user"]["id"], su.channel_name(client, channel))
        if not allowed:
            deny(client, channel, body["user"]["id"], reason, "-")
            return

        sent = []
        for agent in personas.PARTNER_AGENTS.values():
            progress = journey.progress(agent["agent_id"])
            if progress["pending"] == 0:
                continue
            kind = bj.NUDGE_NOT_STARTED if not progress["started"] else bj.NUDGE_BEHIND
            text, blocks = bj.nudge_card(agent, kind, progress, "your manager's check just now")
            su.post_to(client, agent["channel"], text, blocks)
            sf_record = sf_bridge.write_nudge_event(agent["agent_id"], f"manual:{kind}")
            show_sync(client, sf_record, f"Manual nudge sent to {agent['name']}")
            sent.append(f"{agent['name']} ({progress['pending']} open)")

        client.chat_postMessage(
            channel=channel,
            text="Nudges sent",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text":
                ("🔔 *Nudge sent to:* " + ", ".join(sent)) if sent else
                "✅ *Nobody is behind* — every partner agent has recorded all of their assigned visits."}}],
        )

    @app.action("manager_open_agent")
    def manager_open_agent(ack, body, client):
        ack()
        channel = body["channel"]["id"]
        user = body["user"]["id"]
        allowed, reason, _ = access.check_internal(user, su.channel_name(client, channel))
        if not allowed:
            deny(client, channel, user, reason, "-")
            return

        lines = []
        for agent in personas.PARTNER_AGENTS.values():
            progress = journey.progress(agent["agent_id"])
            logged = journey_state.logged_items(agent["agent_id"])
            detail = "\n".join(
                f"   {journey.OUTCOME_EMOJI[item['outcome']]} {journey.assignment(task)['borrower']} — {item['detail']}"
                for task, item in logged.items() if journey.assignment(task)
            ) or "   nothing recorded yet"
            lines.append(f"*{agent['name']}* — {progress['logged']}/{progress['assigned']} recorded\n{detail}")

        client.views_open(trigger_id=body["trigger_id"], view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Agent activity"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": "\n\n".join(lines)}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text":
                    "Manager view. An agent opening the same button sees only their own row."}]},
            ],
        })

    @app.action("manager_nudge_agent")
    def manager_nudge_one(ack, body, client):
        ack()
        channel = body["channel"]["id"]
        user = body["user"]["id"]
        allowed, reason, _ = access.check_internal(user, su.channel_name(client, channel))
        if not allowed:
            deny(client, channel, user, reason, "-")
            return

        agent = personas.PARTNER_AGENTS[body["actions"][0]["value"]]
        progress = journey.progress(agent["agent_id"])
        text, blocks = bj.nudge_card(agent, bj.NUDGE_END_OF_DAY, progress, "a direct reminder from your manager")
        su.post_to(client, agent["channel"], text, blocks)
        client.chat_postMessage(channel=channel, text=f"Reminder sent to {agent['name']}.")

    @app.action("manager_flag_reassign")
    def manager_flag_reassign(ack, body, client):
        ack()
        agent = personas.PARTNER_AGENTS[body["actions"][0]["value"]]
        user = su.actor_name(client, body["user"]["id"])
        log_action("FLAGGED_FOR_REASSIGNMENT", "-", user, agent["agent_id"])
        client.chat_postMessage(
            channel=body["channel"]["id"],
            text="Flagged for reassignment",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text":
                f"🔁 *{agent['name']}'s open visits flagged for reassignment* by {user}. "
                f"Reallocation happens in Salesforce — tomorrow's assignment run picks it up."}}],
        )

    # --- internal legal/ops decisions on escalations ---

    def _close_escalation(body, client, decision_text, action_name):
        channel = body["channel"]["id"]
        user = body["user"]["id"]
        allowed, reason, _ = access.check_internal(user, su.channel_name(client, channel))
        if not allowed:
            deny(client, channel, user, reason, "-")
            return None

        task = journey.assignment(body["actions"][0]["value"])
        actor = su.actor_name(client, user)
        blocks = [b for b in body["message"]["blocks"] if b.get("type") != "actions"]
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": decision_text.format(actor=actor)}})
        client.chat_update(channel=channel, ts=body["message"]["ts"], blocks=blocks,
                           text=f"Escalation decided — {task['loan_id'] if task else ''}")
        log_action(action_name, task["loan_id"] if task else "-", actor)
        return task, actor

    @app.action("escalation_proceed")
    def escalation_proceed(ack, body, client):
        ack()
        result = _close_escalation(body, client, "⚖️ *Proceeding — notice to be issued.* Decided by {actor}.",
                                   "ESCALATION_PROCEED")
        if not result or not result[0]:
            return
        task, actor = result
        agent = personas.PARTNER_AGENTS[task["agent_id"]]
        su.post_to(client, agent["channel"], f"Update on {task['loan_id']}", [
            {"type": "section", "text": {"type": "mrkdwn", "text":
                f"📌 *Update on `{task['loan_id']}` ({task['borrower']})* — Hero FinCorp has taken this case "
                f"in-house. No further visits are needed from you."}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text":
                "You are told the outcome that affects your work. The internal decision and its reasoning stay internal."}]},
        ])

    @app.action("escalation_hold")
    def escalation_hold(ack, body, client):
        ack()
        _close_escalation(body, client, "⏸️ *On hold pending more information.* Decided by {actor}.", "ESCALATION_HOLD")

    @app.action("escalation_return")
    def escalation_return(ack, body, client):
        ack()
        result = _close_escalation(body, client, "↩️ *Sent back to the partner agent for one more attempt.* Decided by {actor}.",
                                   "ESCALATION_RETURNED")
        if not result or not result[0]:
            return
        task, actor = result
        agent = personas.PARTNER_AGENTS[task["agent_id"]]
        su.post_to(client, agent["channel"], f"Revisit requested — {task['loan_id']}", [
            {"type": "section", "text": {"type": "mrkdwn", "text":
                f"🔁 *One more attempt requested on `{task['loan_id']}` ({task['borrower']})* — please revisit and "
                f"record the outcome again."}},
        ])

    # --- forms are the interaction mechanism; free text is not a record ---

    @app.event("message")
    def agent_channel_message(event, client):
        if event.get("bot_id") or event.get("subtype") in {"channel_join", "channel_leave", "message_deleted"}:
            return

        name = su.channel_name(client, event["channel"])
        agent = personas.agent_by_channel(name)
        if not agent:
            return

        user = event.get("user", "")
        if event.get("files"):
            _acknowledge_attachment(client, event, agent)
            return

        su.ephemeral(
            client, event["channel"], user,
            "Use the form so it reaches Salesforce",
            [
                {"type": "section", "text": {"type": "mrkdwn", "text":
                    "📝 *Updates are recorded on the form, not in chat.* A typed message is not written to "
                    "Salesforce and your manager will still see the visit as pending."}},
                {"type": "actions", "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "📝  Record visit outcome"},
                     "style": "primary", "value": agent["agent_id"], "action_id": "open_outcome_modal"}]},
                {"type": "context", "elements": [{"type": "mrkdwn", "text":
                    "Chat is still there for anything you need to ask your manager — it just is not the record."}]},
            ],
        )

    def _acknowledge_attachment(client, event, agent):
        files = event.get("files", [])
        names = ", ".join(f.get("name", "file") for f in files)
        client.chat_postMessage(
            channel=event["channel"], thread_ts=event["ts"],
            text="Attachment received",
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text":
                    f"📎 *Received: {names}* — attached to the loan record in Salesforce."}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text":
                    f"Stored in this private channel. Visible to you ({agent['name']}) and Hero FinCorp internal staff — "
                    f"no other partner agent can open it."}]},
            ],
        )
        log_action("ATTACHMENT_RECEIVED", "-", agent["name"], names)


# ---------- outcome -> Salesforce + follow-up ----------

def _apply_outcome(client, task, agent, outcome, values, actor_label):
    """Writes to Salesforce and fires the follow-up. Returns (detail, sync_record, extras)."""
    extras = {"agent_messages": []}

    if outcome == journey.PAID:
        raw_amount = values["amount"]["amount_input"]["value"]
        mode = values["mode"]["mode_input"]["selected_option"]["value"]
        receipt = values.get("receipt", {}).get("receipt_input", {}).get("value") or "—"
        amount = _to_int(raw_amount)
        extras["amount"] = amount
        shortfall = task["overdue"] - amount
        detail = f"{rupees(amount)} collected via {mode} · receipt {receipt}"
        if shortfall > 0:
            detail += f"\n⚠️ Part payment — {rupees(shortfall)} still outstanding, the account stays open."
        sync = sf_bridge.write_visit_outcome(
            task["task_id"], task["loan_id"], "Payment Collected",
            {"Amount_Collected__c": amount, "Payment_Mode__c": mode, "Receipt_Number__c": receipt},
            actor_label,
        )
        extras["agent_messages"].append(bj.payment_proof_prompt(task))

    elif outcome == journey.PTP:
        amount = _to_int(values["amount"]["amount_input"]["value"])
        promised = values["promise_date"]["promise_date_input"]["selected_date"]
        mode = values["mode"]["mode_input"]["selected_option"]["value"]
        detail = f"{rupees(amount)} promised by {human_date(promised)} via {mode}"
        sync = sf_bridge.write_promise_to_pay(task["task_id"], task["loan_id"], amount, promised, mode, actor_label)

        reminder_on = journey.ptp_reminder_date(promised)
        post_at = _schedule_at(reminder_on)
        channel_id = su.channel_id(client, agent["channel"])
        scheduled = channel_id and _schedule_reminder(
            client, channel_id, post_at,
            f"Reminder — {task['borrower']} promised {rupees(amount)} tomorrow",
            [
                {"type": "section", "text": {"type": "mrkdwn", "text":
                    f"⏰ *Reminder* — *{task['borrower']}* (`{task['loan_id']}`) promised {rupees(amount)} "
                    f"by {human_date(promised)} via {mode}."}},
                {"type": "actions", "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "📝  Record the follow-up"},
                     "style": "primary", "value": agent["agent_id"], "action_id": "open_outcome_modal"}]},
            ],
        )
        detail += ("\n⏰ Reminder scheduled to you for " + human_date(reminder_on)) if scheduled else ""

    elif outcome == journey.REFUSED:
        refusal_type = values["refusal_type"]["refusal_type_input"]["selected_option"]["value"]
        reason = values["reason"]["reason_input"]["value"]
        detail = f"{refusal_type} — \"{reason}\"\n🔺 Escalated to the Hero FinCorp internal team."
        sync = sf_bridge.write_escalation_case(
            task["loan_id"], f"{refusal_type}: {reason}", actor_label, task["bucket"], task["dpd"]
        )
        esc_text, esc_blocks = bj.escalation_card(task, agent, refusal_type, reason, sync)
        su.post_to(client, LEGAL_OPS, esc_text, esc_blocks)

    else:  # UNAVAILABLE
        revisit = values["revisit"]["revisit_input"]["selected_date"]
        attempt = values["attempt"]["attempt_input"]["selected_option"]["value"]
        note = values.get("note", {}).get("note_input", {}).get("value") or ""
        detail = f"Nobody available — revisit set for {human_date(revisit)}" + (f" · {note}" if note else "")
        sync = sf_bridge.write_revisit(task["task_id"], task["loan_id"], revisit, actor_label)

        channel_id = su.channel_id(client, agent["channel"])
        if channel_id:
            _schedule_reminder(
                client, channel_id, _schedule_at(_as_date(revisit)),
                f"Revisit due today — {task['borrower']}",
                [{"type": "section", "text": {"type": "mrkdwn", "text":
                    f"📍 *Revisit due today* — *{task['borrower']}* (`{task['loan_id']}`), {task['locality']}."}}],
            )

        if attempt == "2":
            detail += "\n🔺 Second consecutive miss — raised to your Hero FinCorp manager."
            progress = journey.progress(agent["agent_id"])
            mgr_text, mgr_blocks = bj.manager_nudge_escalation(agent, progress, "a second failed attempt")
            mgr_blocks.insert(1, {"type": "section", "text": {"type": "mrkdwn", "text":
                f"Trigger: second consecutive *customer unavailable* on `{task['loan_id']}` ({task['borrower']})."}})
            su.post_to(client, CONTROL_ROOM, f"Repeat miss — {task['loan_id']}", mgr_blocks)

    return detail, sync, extras


def _to_int(raw):
    try:
        return int(float(str(raw).replace(",", "").replace("₹", "").strip()))
    except (TypeError, ValueError):
        return 0


def _as_date(value):
    from datetime import date
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return date.today()
