"""
CPA approval handlers.

    Salesforce/LOS raises it
      -> #cpa-requests shows the requesting officer that it moved, and to whom
      -> the full detail plus the customer documents go to the approver's
         private channel, and nowhere else
      -> one click decides it
      -> a non-final approval moves it to the next approver automatically
      -> the decision is written back to Salesforce and the requester is told
"""
import access
import blocks_cpa as bc
import blocks_security as bs
import cpa_approvals as cpa
import demo_assets
import personas
import sf_bridge
import slack_files
import slack_util as su
from audit_log import log_action

REQUESTS = "cpa-requests"
AUDIT = "cpa-audit-trail"
SYNC_LOG = "salesforce-sync-log"


def post_request_to_approver(client, request, with_attachments=True):
    """
    Put the request in front of exactly one approver — the one whose step it is.
    Documents are uploaded into that same private channel, in the card's thread.
    """
    channel_name = request.channel_for_current_level()
    text, blocks = bc.cpa_request_card(request)
    result = su.post_to(client, channel_name, text, blocks)
    if not result or not result.get("ok"):
        return None

    if with_attachments and request.attachments:
        demo_assets.ensure_documents()
        paths = [demo_assets.path_for(name) for name in request.attachments]
        slack_files.upload_many(
            paths, result["channel"],
            initial_comment=(f"Supporting documents for `{request.request_id}` — "
                             f"shared into this private channel only."),
            thread_ts=result["ts"],
        )
    log_action("CPA_ROUTED", request.loan_id, "system",
               f"{request.request_id} -> L{request.current_level()} {request.current_approver()['name']}")
    return result


def announce_intake(client, request):
    text, blocks = bc.cpa_intake_card(request)
    return su.post_to(client, REQUESTS, text, blocks)


def register(app):

    @app.action("cpa_approve")
    def approve(ack, body, client):
        ack()
        _open_decision(body, client, cpa.APPROVED)

    @app.action("cpa_reject")
    def reject(ack, body, client):
        ack()
        _open_decision(body, client, cpa.REJECTED)

    def _open_decision(body, client, decision):
        channel = body["channel"]["id"]
        user = body["user"]["id"]
        request = cpa.get_request(body["actions"][0]["value"])
        if not request:
            su.ephemeral(client, channel, user, "That request no longer exists.")
            return

        allowed, reason, _ = access.check_cpa_decision(user, request, su.channel_name(client, channel))
        if not allowed:
            log_action("ACCESS_DENIED", request.loan_id, su.actor_name(client, user), reason.split("\n")[0])
            su.ephemeral(client, channel, user, "Access denied", bs.denial_notice(reason))
            return

        if request.status != cpa.PENDING:
            su.ephemeral(client, channel, user, f"`{request.request_id}` is already {request.status.lower()}.")
            return

        client.views_open(trigger_id=body["trigger_id"], view=bc.cpa_decision_modal(request, decision))

    @app.view("cpa_decision_submit")
    def decide(ack, body, client, view):
        ack()
        request_id, decision = view["private_metadata"].split("|")
        request = cpa.get_request(request_id)
        if not request or request.status != cpa.PENDING:
            return

        user = body["user"]["id"]
        approver = request.current_approver()
        decided_by = approver["name"] if approver else su.actor_name(client, user)
        comment = view["state"]["values"]["comment"]["comment_input"]["value"] or ""
        level_just_decided = request.current_level()
        source_channel = request.channel_for_current_level()

        if decision == cpa.APPROVED:
            request.approve(decided_by, comment)
        else:
            request.reject(decided_by, comment)

        sync = sf_bridge.write_approval_decision(
            request.request_id, request.loan_id, level_just_decided, decision, decided_by, comment
        )
        log_action(f"CPA_{decision}", request.loan_id, decided_by,
                   f"{request.request_id} L{level_just_decided} — {comment}")

        # Close out the card in the channel where the decision was taken.
        text, blocks = bc.cpa_decided_card(request, sync, decided_by)
        su.post_to(client, source_channel, text, blocks)

        # Still pending means it cleared a level and moves up the chain.
        if request.status == cpa.PENDING:
            post_request_to_approver(client, request)

        notify_text, notify_blocks = bc.requester_notification(request, sync)
        su.post_to(client, REQUESTS, notify_text, notify_blocks)

        audit_text, audit_blocks = bc.cpa_audit_card(request, sync)
        su.post_to(client, AUDIT, audit_text, audit_blocks)

        sync_text, sync_blocks = bs.sf_sync_card(
            sync, f"{decided_by} {decision.lower()} `{request.request_id}` at Level {level_just_decided}"
        )
        su.post_to(client, SYNC_LOG, sync_text, sync_blocks)

    @app.action("cpa_query")
    def query(ack, body, client):
        ack()
        request = cpa.get_request(body["actions"][0]["value"])
        if not request:
            return
        channel = body["channel"]["id"]
        allowed, reason, _ = access.check_cpa_decision(body["user"]["id"], request, su.channel_name(client, channel))
        if not allowed:
            su.ephemeral(client, channel, body["user"]["id"], "Access denied", bs.denial_notice(reason))
            return
        client.views_open(trigger_id=body["trigger_id"], view=bc.cpa_query_modal(request))

    @app.view("cpa_query_submit")
    def submit_query(ack, body, client, view):
        ack()
        request = cpa.get_request(view["private_metadata"])
        if not request:
            return
        question = view["state"]["values"]["question"]["question_input"]["value"]
        asked_by = su.actor_name(client, body["user"]["id"])
        text, blocks = bc.cpa_question_card(request, question, asked_by)
        su.post_to(client, REQUESTS, text, blocks)
        log_action("CPA_QUERY", request.loan_id, asked_by, question)

    @app.action("cpa_refresh_inbox")
    def refresh_inbox(ack, body, client):
        ack()
        channel = body["channel"]["id"]
        user = body["user"]["id"]
        channel_name = su.channel_name(client, channel)
        actor = access.resolve_actor(user, channel_name)

        if actor.kind == access.AGENT:
            su.ephemeral(client, channel, user, "Access denied", bs.denial_notice(
                ":lock: *Access denied.* Credit approvals are an internal Hero FinCorp decision."))
            return

        person = actor.staff or personas.INTERNAL_STAFF["CPA-L1"]
        levels = ["CPA-L1"] if channel_name == "cpa-approvals-l1" else ["CPA-L2", "CPA-L3"]
        waiting = [r for r in cpa.pending_all()
                   if r.current_approver() and r.current_approver()["person_id"] in levels]
        text, blocks = bc.cpa_inbox_card(person, waiting)
        client.chat_postMessage(channel=channel, text=text, blocks=blocks)
