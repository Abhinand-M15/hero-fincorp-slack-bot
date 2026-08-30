SECURITY_CANVAS_MARKDOWN = """# 🔐 Access & Security — Who Can See What

*The administrator's and information-security team's view. Every row here is checked against live Slack membership by `access_review.py`, and re-checked on the server for every button click.*

## The two questions this answers

1. Can an external partner agent see another partner agent's customers, documents or conversations? **No.**
2. Can an external partner agent see anything internal to Hero FinCorp — escalations, other agents' activity, credit approvals? **No.**

## Channel map

| Channel | Type | Who is in it | External partner access |
|---|---|---|---|
| collections-agent-pune-01 | Private | Rakesh Sharma (external partner) + Collections Manager | Rakesh only |
| collections-agent-lucknow-02 | Private | Imran Qureshi (extended workforce) + Collections Manager | Imran only |
| collections-control-room | Private | Collections Manager, Collections Ops | None |
| collections-legal-ops | Private | Collections Manager, Legal & Ops | None |
| cpa-requests | Private | Requesting officer, Credit Manager | None |
| cpa-approvals-l1 | Private | Credit Manager (L1) | None |
| cpa-approvals-l2 | Private | Credit Head (L2), Chief Risk Officer (L3) | None |
| cpa-audit-trail | Private | Approvers + Admin | None |
| salesforce-sync-log | Private | Collections Manager, Admin | None |
| admin-security-console | Private | Admin / Information Security | None |

## The four controls, in the order they apply

**1. Channel membership.** Each external partner agent has exactly one private channel. They are not a member of any other channel in this workspace. There is no shared channel where two partner agents meet.

**2. Record-level authorisation on the server.** Channel membership alone is not relied on. Every button click and every form submission is re-checked in `access.py` against the record's owner in Salesforce before anything is read, written or displayed. A button payload copied from elsewhere still fails.

**3. Forms as the interaction mechanism.** Partner agents record work on a workflow form, not in free chat. The form only ever offers the accounts assigned to the person opening it. A typed message in an agent channel gets a reminder that chat is not the record — it is never written to Salesforce.

**4. Attachment containment.** Files are completed into a specific channel, and every channel in this flow is private. A payment-proof screenshot goes into the uploading agent's own channel. A customer document on a credit request goes into the approver's channel. Neither is ever posted into a shared or partner-facing channel, so there is no step at which either becomes broadly visible.

## What each person can see

| Person | Sees | Does not see |
|---|---|---|
| External partner agent | Their own assigned accounts, their own outcomes, their own uploads, the outcome of anything escalated that affects their work | Any other agent's accounts, the internal escalation discussion, credit approvals, the manager roll-up |
| Collections Manager | Every partner agent's progress and outcomes, escalations, the sync log | Credit approval detail at levels they are not on |
| CPA approver | The requests at their own level, with full detail and documents | Requests sitting at other levels; collections agent channels |
| Requesting officer | That their request moved, who it is with, the final decision and reason | The internal deliberation, the other requests in the approver's queue |
| Admin / InfoSec | The access matrix, live membership, the audit trail | — |

## Proving it in the room

- **Live membership** — the button in ![](#{admin_channel}) calls `conversations.members` and prints who is actually in each channel, flagging any external account found in an internal channel.
- **Cross-agent access test** — runs the real authorisation checks: Agent A on their own account (allowed), Agent A on Agent B's account (blocked), Agent A on an internal channel (blocked), Agent A on a credit approval (blocked), the manager on any account (allowed).
- **Two accounts side by side** — with both sample agents signed in, each sidebar shows one channel, and the two lists of customers do not overlap.

## Audit

Every action — including every refusal — is written to the local audit trail with actor, record and timestamp, and mirrored to Salesforce. `ACCESS_DENIED` entries record who reached for what and were shown the block.
"""
