ARCHITECTURE_CANVAS_MARKDOWN = """# 🗄️ Salesforce & Slack — Where the Data Lives

*Salesforce stays the system of record. Slack is the interaction and collaboration layer. Nothing in this demo creates a second database.*

## The loop

```
  Salesforce / LOS                    Slack                          Salesforce
  ────────────────                    ─────                          ──────────
  assignment or                 task or request appears
  approval request      ──►     in the right private      ──►    write-back on
  is created                    channel, for one person        the same record
                                          │                           │
                                          ▼                           ▼
                                  person acts on a            manager and
                                  workflow form               requester see it
```

1. **Salesforce assigns.** A collections visit or a credit approval request is created in Salesforce/LOS, with an owner.
2. **Slack surfaces it.** The bot pulls that person's slice and posts it into their private channel. Only the assignee's records travel.
3. **The person acts on a form.** Outcome, decision, amount, date — captured in structured fields, not free text.
4. **Slack writes back.** The outcome becomes a record on the same Salesforce object. Every call is visible in ![](#{sync_channel}) as it happens.
5. **Everyone downstream reads Salesforce.** Manager dashboards, reporting and the next workflow step all read the system of record, not Slack.

## What is stored where

| | Salesforce | Slack |
|---|---|---|
| Lead, loan, customer master | ✅ Record of truth | ❌ Never stored |
| Visit assignment | ✅ Task record | Shown as a card for the day |
| Visit outcome, PTP, refusal | ✅ Written back | The form that captured it |
| Credit approval request + decision | ✅ Written back to the LOS record | The card the approver clicked |
| Customer documents | ✅ Attached to the record | Shared into one private channel |
| Conversation and coordination | ❌ | ✅ This is what Slack is for |
| Audit of who did what | ✅ Mirrored | Local audit trail as a backup |

## On the volume question

The discovery call put lead volume at roughly **1,50,000–2,00,000 records a day**. That volume lives in Salesforce and stays there.

What reaches Slack is the *actionable slice*:

| | Per day |
|---|---|
| Records in Salesforce | 1,50,000 – 2,00,000 |
| Records pushed into Slack | one agent's assigned visits — typically 15–25 per agent |
| Approvals pushed into Slack | only the applications that hit a policy exception |
| Messages a person reads | their own channel, their own queue |

Slack is being asked to carry decisions and conversations, not to index the book. If a record needs no human action today, it never appears in Slack at all.

## Why no Slack-side database is needed

- Slack messages carry only what the person needs to act, and the identifiers to write back.
- The only local state kept is which card to refresh and which reminder has already been sent — a few kilobytes, rebuildable from Salesforce at any time.
- Delete the local state and the next Salesforce pull restores the working view. No reconciliation, no second source of truth.

## The connection

Salesforce authentication uses the **JWT Bearer Flow** against a connected app — certificate-based, no password stored anywhere in the integration. The live check in ![](#{sync_channel}) proves the connection during the demo.
"""
