"""
Offline checks for everything that can be verified without a Slack workspace:
Block Kit structure, approval routing, access control, nudge checkpoints and
the channel registry.

    ./venv/bin/python selftest.py

Nothing here calls Slack or Salesforce. It runs against a throwaway state file,
so it is safe to run at any time, including immediately before a demo.
"""
import json
import os
import sys
import tempfile

import journey_state

# Redirect state to a temp file BEFORE anything reads it.
_TEMP_STATE = os.path.join(tempfile.mkdtemp(prefix="hfc-selftest-"), "journey_state.json")
journey_state.STATE_PATH = _TEMP_STATE

import access                      # noqa: E402
import blocks_cpa as bc            # noqa: E402
import blocks_journey as bj        # noqa: E402
import blocks_security as bs       # noqa: E402
import channels                    # noqa: E402
import collections_journey as journey  # noqa: E402
import cpa_approvals as cpa        # noqa: E402
import nudge_engine                # noqa: E402
import personas                    # noqa: E402
import sf_bridge                   # noqa: E402

FAILURES = []
CHECKS = [0]


def check(condition, description):
    CHECKS[0] += 1
    if not condition:
        FAILURES.append(description)
        print(f"  ✗ {description}")
    return condition


def section(title):
    print(f"\n{title}")


# ---------- Block Kit structure ----------

MAX_TEXT = 3000
MAX_HEADER = 150


def validate_blocks(blocks, where):
    for index, block in enumerate(blocks):
        label = f"{where}[{index}]"
        check(isinstance(block, dict) and "type" in block, f"{label} has a type")
        kind = block.get("type")

        if kind == "header":
            text = block["text"]["text"]
            check(block["text"]["type"] == "plain_text", f"{label} header uses plain_text")
            check(len(text) <= MAX_HEADER, f"{label} header within {MAX_HEADER} chars (is {len(text)})")

        elif kind == "section":
            if "text" in block:
                check(len(block["text"]["text"]) <= MAX_TEXT,
                      f"{label} section text within {MAX_TEXT} chars (is {len(block['text']['text'])})")
                check(block["text"]["text"].strip() != "", f"{label} section text is not empty")
            elif "fields" in block:
                check(len(block["fields"]) <= 10, f"{label} has at most 10 fields")
            else:
                check(False, f"{label} section has text or fields")

        elif kind == "actions":
            check(len(block["elements"]) <= 25, f"{label} actions within 25 elements")
            for element in block["elements"]:
                check("action_id" in element, f"{label} element has an action_id")
                if element["type"] == "button":
                    check(len(element["text"]["text"]) <= 75, f"{label} button label within 75 chars")

        elif kind == "input":
            check("label" in block and "element" in block, f"{label} input has a label and an element")
            check("block_id" in block, f"{label} input has a block_id")

        elif kind == "context":
            check(len(block["elements"]) <= 10, f"{label} context within 10 elements")


def validate_modal(view, where):
    check(view["type"] == "modal", f"{where} is a modal")
    check(len(view["title"]["text"]) <= 24, f"{where} title within 24 chars (is {len(view['title']['text'])})")
    check(len(view["blocks"]) <= 100, f"{where} within 100 blocks")
    if "private_metadata" in view:
        check(len(view["private_metadata"]) <= 3000, f"{where} private_metadata within 3000 chars")
    validate_blocks(view["blocks"], where)


def test_blocks():
    section("Block Kit structure")
    agent = personas.PARTNER_AGENTS["AG-PUNE-01"]
    assignments = journey.assignments_for(agent["agent_id"])
    progress = journey.progress(agent["agent_id"])

    _, blocks = bj.agent_day_card(agent, assignments, progress)
    validate_blocks(blocks, "agent_day_card")

    validate_modal(bj.outcome_modal("C123", agent["agent_id"], assignments), "outcome_modal(base)")
    for outcome in journey.OUTCOME_LABELS:
        validate_modal(
            bj.outcome_modal("C123", agent["agent_id"], assignments,
                             selected_task=assignments[0]["task_id"], outcome=outcome),
            f"outcome_modal({outcome})",
        )

    sync = sf_bridge.write_visit_outcome("SFT-0001", "HFCL/TW/2026/00891", "Payment Collected",
                                         {"Amount_Collected__c": 4500}, "selftest")
    _, blocks = bj.outcome_receipt_card(agent, assignments[0], journey.PAID, "₹4,500 collected",
                                        sync, journey.follow_up_for(journey.PAID))
    validate_blocks(blocks, "outcome_receipt_card")

    _, blocks = bj.payment_proof_prompt(assignments[0])
    validate_blocks(blocks, "payment_proof_prompt")

    for kind in (bj.NUDGE_NOT_STARTED, bj.NUDGE_BEHIND, bj.NUDGE_END_OF_DAY):
        _, blocks = bj.nudge_card(agent, kind, progress, "11:00")
        validate_blocks(blocks, f"nudge_card({kind})")

    _, blocks = bj.manager_nudge_escalation(agent, progress, "18:00")
    validate_blocks(blocks, "manager_nudge_escalation")

    rows = [(a, journey.progress(a["agent_id"])) for a in personas.PARTNER_AGENTS.values()]
    _, blocks = bj.activity_board(rows)
    validate_blocks(blocks, "activity_board")

    _, blocks = bj.escalation_card(assignments[0], agent, "Dispute over amount", "Customer disputes the amount.", sync)
    validate_blocks(blocks, "escalation_card")

    validate_modal(bj.agent_progress_view(agent, assignments, progress), "agent_progress_view")

    for request in cpa.all_requests():
        _, blocks = bc.cpa_request_card(request)
        validate_blocks(blocks, f"cpa_request_card({request.request_id})")
        _, blocks = bc.cpa_intake_card(request)
        validate_blocks(blocks, f"cpa_intake_card({request.request_id})")
        validate_modal(bc.cpa_decision_modal(request, cpa.APPROVED), f"cpa_decision_modal(approve)")
        validate_modal(bc.cpa_decision_modal(request, cpa.REJECTED), f"cpa_decision_modal(reject)")
        validate_modal(bc.cpa_query_modal(request), "cpa_query_modal")
        _, blocks = bc.cpa_question_card(request, "Need the latest GST return.", "Neha Sinha")
        validate_blocks(blocks, "cpa_question_card")

    _, blocks = bc.cpa_inbox_card(personas.INTERNAL_STAFF["CPA-L1"], cpa.pending_all())
    validate_blocks(blocks, "cpa_inbox_card")

    _, blocks = bs.access_matrix_card()
    validate_blocks(blocks, "access_matrix_card")
    _, blocks = bs.attachment_policy_card()
    validate_blocks(blocks, "attachment_policy_card")
    _, blocks = bs.data_ownership_card()
    validate_blocks(blocks, "data_ownership_card")
    _, blocks = bs.sf_sync_card(sync, "selftest")
    validate_blocks(blocks, "sf_sync_card")
    validate_blocks(bs.denial_notice("blocked"), "denial_notice")

    observations = [{"channel": "collections-agent-pune-01", "exists": True, "private": True,
                     "members": ["Rakesh Sharma (EXTERNAL)"], "unexpected": [], "missing": []}]
    _, blocks = bs.live_membership_card(observations)
    validate_blocks(blocks, "live_membership_card")

    import handlers_security
    _, blocks = bs.cross_agent_test_card(handlers_security.run_cross_agent_test())
    validate_blocks(blocks, "cross_agent_test_card")

    print(f"  {CHECKS[0]} structural assertions run")


# ---------- Approval routing ----------

def test_routing():
    section("CPA approval routing")
    cases = [
        (300000, [{"type": "CIBIL Score", "detail": "x"}], 1),
        (500000, [{"type": "CIBIL Score", "detail": "x"}], 1),
        (500001, [{"type": "Income Shortfall", "detail": "x"}], 2),
        (2500000, [{"type": "Income Shortfall", "detail": "x"}], 2),
        (2500001, [{"type": "Income Shortfall", "detail": "x"}], 3),
        (400000, [{"type": "LTV Breach", "detail": "x"}], 2),
        (400000, [{"type": "CIBIL Score", "detail": "x"}, {"type": "Income Shortfall", "detail": "y"},
                  {"type": "Age Outside Range", "detail": "z"}], 2),
    ]
    for amount, deviations, expected_levels in cases:
        chain, reason = route_levels(amount, deviations)
        check(chain == expected_levels,
              f"₹{amount:,} with {len(deviations)} deviation(s) -> {expected_levels} level(s), got {chain}")
        check(bool(reason), "routing reason is populated")

    for request in cpa.all_requests():
        order = [cpa.L1, cpa.L2, cpa.L3]
        indices = [order.index(p) for p in request.chain]
        check(indices == sorted(indices), f"{request.request_id} chain is in seniority order")
        check(request.current_approver()["person_id"] == request.chain[0],
              f"{request.request_id} starts at its first approver")


def route_levels(amount, deviations):
    chain, reason = cpa.route(amount, deviations)
    return len(chain), reason


def test_multilevel_progression():
    section("Multi-level progression")
    request = next(r for r in cpa.all_requests() if r.total_levels() >= 2)
    request_id = request.request_id
    levels = request.total_levels()

    for level in range(1, levels + 1):
        current = cpa.get_request(request_id)
        check(current.current_level() == level, f"{request_id} is at level {level}")
        approver = current.current_approver()
        check(approver is not None, f"level {level} has an approver")
        current.approve(approver["name"], f"cleared L{level}")

    final = cpa.get_request(request_id)
    check(final.status == cpa.APPROVED, f"{request_id} is APPROVED after {levels} approvals")
    check(len(final.decisions) == levels, f"{request_id} recorded {levels} decisions")
    check(final.current_approver() is None, "a completed request has no pending approver")

    # Rejection at level 1 stops the chain immediately.
    other = next(r for r in cpa.all_requests() if r.status == cpa.PENDING and r.total_levels() >= 2)
    other.reject(other.current_approver()["name"], "insufficient documentation")
    reloaded = cpa.get_request(other.request_id)
    check(reloaded.status == cpa.REJECTED, f"{other.request_id} is REJECTED")
    check(len(reloaded.decisions) == 1, "a level-1 rejection does not travel up the chain")

    journey_state.save({"date": None, "agents": {}, "cards": {}, "nudges": {}, "cpa": {}})


# ---------- Access control ----------

def test_access():
    section("Access control")
    agent_a = personas.PARTNER_AGENTS["AG-PUNE-01"]
    agent_b = personas.PARTNER_AGENTS["AG-LKO-02"]
    task_a = journey.assignments_for("AG-PUNE-01")[0]["task_id"]
    task_b = journey.assignments_for("AG-LKO-02")[0]["task_id"]

    allowed, _, actor = access.check_task_access("u_a", task_a, agent_a["channel"])
    check(allowed, "agent A may record on their own account")
    check(actor.agent_id == "AG-PUNE-01", "agent A is resolved from their own channel")

    allowed, reason, _ = access.check_task_access("u_a", task_b, agent_a["channel"])
    check(not allowed, "agent A is blocked from agent B's account")
    check("Access denied" in reason, "the block explains itself to the person who hit it")

    allowed, _, _ = access.check_task_access("u_b", task_a, agent_b["channel"])
    check(not allowed, "agent B is blocked from agent A's account")

    allowed, _, _ = access.check_task_access("u_m", task_b, "collections-control-room")
    check(allowed, "internal staff may review any agent's account")

    allowed, _, _ = access.check_internal("u_a", agent_a["channel"])
    check(not allowed, "agent A cannot reach internal-only actions")

    allowed, _, _ = access.check_internal("u_m", "collections-legal-ops")
    check(allowed, "internal staff may reach internal-only actions")

    visible_a, _ = access.visible_assignments("u_a", agent_a["channel"])
    visible_b, _ = access.visible_assignments("u_b", agent_b["channel"])
    check(all(a["agent_id"] == "AG-PUNE-01" for a in visible_a), "agent A sees only their own assignments")
    check(all(a["agent_id"] == "AG-LKO-02" for a in visible_b), "agent B sees only their own assignments")
    check(not ({a["loan_id"] for a in visible_a} & {a["loan_id"] for a in visible_b}),
          "the two agents' visible accounts do not overlap")

    visible_m, _ = access.visible_assignments("u_m", "collections-control-room")
    check(len(visible_m) == len(journey.ASSIGNMENTS), "the manager sees every assignment")

    pending = cpa.pending_all()
    if pending:
        allowed, _, _ = access.check_cpa_decision("u_a", pending[0], agent_a["channel"])
        check(not allowed, "a partner agent cannot decide a credit approval")

    allowed, _, _ = access.check_task_access("nobody", "SFT-0001", None)
    check(not allowed, "an unmapped user with no channel context is refused")

    allowed, _, _ = access.check_task_access("u_a", "SFT-9999", agent_a["channel"])
    check(not allowed, "an unknown task id is refused")


# ---------- Channel registry ----------

def test_registry():
    section("Channel registry")
    names = [c["name"] for c in channels.ALL_CHANNELS]
    check(len(names) == len(set(names)), "no duplicate channel names")

    for channel in channels.JOURNEY_CHANNELS:
        check(channel["private"], f"#{channel['name']} is private")
        check(len(channel["name"]) <= 80, f"#{channel['name']} name within Slack's 80-char limit")
        check(channel["name"] == channel["name"].lower(), f"#{channel['name']} is lowercase")

    agent_ids = set(personas.PARTNER_AGENTS)
    for channel in channels.JOURNEY_CHANNELS:
        if channel["visibility"] == channels.INTERNAL:
            check(not (set(channel["members"]) & agent_ids),
                  f"#{channel['name']} has no partner agent in its member list")

    for agent in personas.PARTNER_AGENTS.values():
        owned = [c for c in channels.JOURNEY_CHANNELS
                 if c["visibility"] == channels.AGENT_PRIVATE and agent["agent_id"] in c["members"]]
        check(len(owned) == 1, f"{agent['name']} owns exactly one private channel")


# ---------- Nudges ----------

def test_nudges():
    section("Nudge checkpoints")
    journey_state.save({"date": None, "agents": {}, "cards": {}, "nudges": {}, "cpa": {}})

    progress = journey.progress("AG-LKO-02")
    check(not progress["started"], "an agent who has not started shows as not started")
    check(progress["pending"] == progress["assigned"], "nothing recorded means everything pending")

    not_started = next(c for c in nudge_engine.CHECKPOINTS if c["key"] == bj.NUDGE_NOT_STARTED)
    behind = next(c for c in nudge_engine.CHECKPOINTS if c["key"] == bj.NUDGE_BEHIND)
    end_of_day = next(c for c in nudge_engine.CHECKPOINTS if c["key"] == bj.NUDGE_END_OF_DAY)

    check(not_started["applies"](progress), "the 11:00 checkpoint applies to an agent who has not started")
    check(end_of_day["escalate"], "the 18:00 checkpoint escalates to the manager")

    journey_state.mark_started("AG-LKO-02")
    progress = journey.progress("AG-LKO-02")
    check(not not_started["applies"](progress), "the 11:00 checkpoint stops once the agent has started")
    check(behind["applies"](progress), "the 15:00 checkpoint still applies while visits are open")

    for item in journey.assignments_for("AG-LKO-02"):
        journey_state.record_outcome("AG-LKO-02", item["task_id"], journey.PAID, "paid", "selftest")
    progress = journey.progress("AG-LKO-02")
    check(progress["pending"] == 0, "recording every visit clears the pending count")
    check(not behind["applies"](progress), "no nudge once the day is complete")
    check(not end_of_day["applies"](progress), "no end-of-day escalation once the day is complete")

    check(not journey_state.nudge_already_sent("AG-PUNE-01", bj.NUDGE_BEHIND), "no nudge recorded yet")
    journey_state.mark_nudge_sent("AG-PUNE-01", bj.NUDGE_BEHIND)
    check(journey_state.nudge_already_sent("AG-PUNE-01", bj.NUDGE_BEHIND), "a sent nudge is remembered")

    forced = nudge_engine.due_checkpoints(forced="11:00")
    check(len(forced) == 1 and forced[0]["key"] == bj.NUDGE_NOT_STARTED, "a checkpoint can be forced for the demo")

    journey_state.save({"date": None, "agents": {}, "cards": {}, "nudges": {}, "cpa": {}})


# ---------- Salesforce calls ----------

def test_sf_calls():
    section("Salesforce write-back")
    check(sf_bridge.WRITE_MODE in {"simulate", "live"}, "write mode is simulate or live")

    record = sf_bridge.write_promise_to_pay("SFT-0001", "HFCL/TW/2026/00891", 4500, "2026-09-05", "UPI", "selftest")
    check(record.method == "POST" and record.path.endswith("/"), "a promise to pay is a POST to the PTP object")
    check("Promised_Date__c" in record.body, "the promised date is on the payload")
    check("Simulated" in record.status_line() or "Written" in record.status_line(), "the status line is readable")

    record = sf_bridge.write_revisit("SFT-0001", "HFCL/TW/2026/00891", "2026-09-02", "selftest")
    check(record.method == "PATCH", "a revisit patches the existing task rather than creating a record")
    check("SFT-0001" in record.path, "the patch targets the originating task")

    record = sf_bridge.write_approval_decision("CPA-2026-00417", "HFCL/PL/2026/01590", 1,
                                               cpa.APPROVED, "Neha Sinha", "ok")
    check("CPA-2026-00417" in record.path, "the decision patches the originating LOS request")

    query = sf_bridge.read_assignments_query("AG-PUNE-01")
    check("AG-PUNE-01" in query.path, "the assignment query is scoped to one agent")
    check("ActivityDate=TODAY" in query.path, "the assignment query is scoped to today")


# ---------- Handler wiring ----------

class StubApp:
    """Records what the handler modules register, without touching Slack."""

    def __init__(self):
        self.actions, self.views, self.events = set(), set(), set()

    def _register(self, bucket, name):
        def decorator(func):
            bucket.add(name)
            return func
        return decorator

    def action(self, name):
        return self._register(self.actions, name)

    def view(self, name):
        return self._register(self.views, name)

    def event(self, name):
        return self._register(self.events, name)


def collect_action_ids(blocks):
    found = set()
    for block in blocks:
        for element in block.get("elements", []):
            if isinstance(element, dict) and "action_id" in element:
                found.add(element["action_id"])
        element = block.get("element")
        if isinstance(element, dict) and "action_id" in element and block.get("dispatch_action"):
            found.add(element["action_id"])
    return found


def test_wiring():
    section("Handler wiring")
    import handlers_collections, handlers_cpa, handlers_security

    stub = StubApp()
    handlers_collections.register(stub)
    handlers_cpa.register(stub)
    handlers_security.register(stub)

    agent = personas.PARTNER_AGENTS["AG-PUNE-01"]
    assignments = journey.assignments_for(agent["agent_id"])
    progress = journey.progress(agent["agent_id"])
    request = cpa.all_requests()[0]
    sync = sf_bridge.write_visit_outcome("SFT-0001", "HFCL/TW/2026/00891", "Payment Collected", {}, "selftest")

    used = set()
    used |= collect_action_ids(bj.agent_day_card(agent, assignments, progress)[1])
    used |= collect_action_ids(bj.nudge_card(agent, bj.NUDGE_BEHIND, progress, "15:00")[1])
    used |= collect_action_ids(bj.manager_nudge_escalation(agent, progress, "18:00")[1])
    used |= collect_action_ids(bj.activity_board([(agent, progress)])[1])
    used |= collect_action_ids(bj.escalation_card(assignments[0], agent, "Refused", "no reason", sync)[1])
    used |= collect_action_ids(bj.outcome_modal("C1", agent["agent_id"], assignments)["blocks"])
    used |= collect_action_ids(bc.cpa_request_card(request)[1])
    used |= collect_action_ids(bc.cpa_inbox_card(personas.INTERNAL_STAFF["CPA-L1"], [request])[1])
    used |= collect_action_ids(bs.access_matrix_card()[1])
    used.add("sf_probe_now")  # added to the data-ownership card by setup_journey.py

    for action_id in sorted(used):
        check(action_id in stub.actions, f"action '{action_id}' has a handler")

    for callback in ("outcome_modal_submit", "cpa_decision_submit", "cpa_query_submit"):
        check(callback in stub.views, f"view '{callback}' has a handler")

    check("message" in stub.events, "the agent-channel message listener is registered")
    check(len(stub.actions) >= len(used), "no card references an unregistered action")


# ---------- Data sanity ----------

def test_data():
    section("Demo data")
    task_ids = [a["task_id"] for a in journey.ASSIGNMENTS]
    check(len(task_ids) == len(set(task_ids)), "task IDs are unique")

    for agent_id in personas.PARTNER_AGENTS:
        assigned = journey.assignments_for(agent_id)
        check(len(assigned) >= 3, f"{agent_id} has enough accounts to demo with ({len(assigned)})")

    for assignment in journey.ASSIGNMENTS:
        check(assignment["agent_id"] in personas.PARTNER_AGENTS,
              f"{assignment['task_id']} belongs to a known agent")

    request_ids = [r.request_id for r in cpa.all_requests()]
    check(len(request_ids) == len(set(request_ids)), "CPA request IDs are unique")

    import demo_assets
    for request in cpa.all_requests():
        for name in request.attachments:
            check(name in demo_assets.DOCUMENTS, f"{name} has a generator in demo_assets.py")

    levels = {r.total_levels() for r in cpa.all_requests()}
    check(1 in levels, "at least one single-level approval is seeded")
    check(any(level > 1 for level in levels), "at least one multi-level approval is seeded")


if __name__ == "__main__":
    print("Hero FinCorp demo — offline self-test")
    test_registry()
    test_data()
    test_wiring()
    test_access()
    test_routing()
    test_multilevel_progression()
    test_nudges()
    test_sf_calls()
    test_blocks()

    print(f"\n{'-' * 60}")
    if FAILURES:
        print(f"FAILED — {len(FAILURES)} of {CHECKS[0]} checks")
        for failure in FAILURES:
            print(f"  ✗ {failure}")
        sys.exit(1)
    print(f"PASSED — all {CHECKS[0]} checks")
    sys.exit(0)
