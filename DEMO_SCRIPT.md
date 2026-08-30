# Hero FinCorp — Slack Demo Runbook

The customer asked to be shown this **from each user's point of view**, not feature by feature. This runbook is ordered that way. Each section states the question that person is asking, exactly what to click, and what to say while it happens.

Total running time: **30–35 minutes** for all five points of view, or **12 minutes** for the collections journey alone.

---

## Before the session

```bash
./run.sh
```

One command. It runs the 801 offline checks, verifies the tokens and OAuth scopes, creates the ten private channels, invites the personas listed in `.env`, creates the two canvases, posts the opening cards, reads channel membership back out of Slack to confirm no external account is in an internal channel, and then starts the bot. Leave it running.

If anything is missing it stops and says exactly what to fix — a missing scope is named, not guessed at.

**Set `HFC_DEMO_FAST=true` in `.env`** so scheduled reminders land ~90 seconds later instead of on the real date. Otherwise the promise-to-pay reminder is invisible during the session. `./run.sh check` warns you if you forget.

To start over from a clean workspace: `./run.sh --fresh`.

Individual steps, when you want them: `./run.sh check` · `test` · `setup` · `start` · `review` · `reset`.

### The two sample agents

| | Agent A | Agent B |
|---|---|---|
| Name | Rakesh Sharma | Imran Qureshi |
| Type | **External Partner** — Sai Recovery Services, an empanelled partner | **Extended HFCL Workforce** |
| Sits at | Kothrud two-wheeler showroom, Pune | Aliganj branch counter, Lucknow |
| Channel | `#collections-agent-pune-01` | `#collections-agent-lucknow-02` |
| Assigned today | 4 accounts | 4 accounts |

Both flavours the customer described are represented: a genuinely external partner firm, and an extended-workforce member sitting in a branch. Neither is an HFCL employee on the internal payroll, and neither is the end customer.

### Driving it with one account, or two

The journey channels are private and created by the bot, so **`HFC_PRESENTER_SLACK_IDS` in `.env` is not optional** — put your own Slack member ID there (Slack → your profile → ⋮ → Copy member ID) and you are invited to all ten. Without it the bot is the only member and you will see nothing.

**One account (the normal case).** Set only `HFC_PRESENTER_SLACK_IDS` and leave every persona ID blank. In relaxed access mode your identity follows the channel you are acting in: in `#collections-agent-pune-01` the bot treats you as Rakesh and shows you his four accounts; in `#collections-control-room` it treats you as the manager. You walk all five points of view from one sidebar, and record-level ownership is still enforced — the cross-agent access test in §5 produces the isolation evidence from the server side.

**Two accounts (stronger).** Also set `HFC_AGENT_B_SLACK_ID` to a second account — a Slack guest works well. That account is invited to Imran's channel and nothing else, so putting the two sidebars side by side shows one channel each and no overlap in the customer lists. This is the single most convincing moment in the security section if you can arrange it.

---

## 1. The external partner agent — "What do I need to do today?"

**Sign in as Agent A. Open `#collections-agent-pune-01`.**

### Show

1. **The day's card.** Four accounts, each with borrower, product, DPD, amount overdue, and locality. Point at the footer: *this is a private channel, and these four accounts are the ones assigned to this agent in Salesforce.*
2. **Start my day.** One tap. The manager can now see the agent has started; a card is posted confirming it; `#salesforce-sync-log` shows the SOQL that pulled the assignments.
3. **Record visit outcome →** the form. Note the account dropdown contains **only this agent's four accounts**.

### Walk all four outcomes

Do these in order — each one demonstrates a different follow-up.

| Outcome | Enter | What happens |
|---|---|---|
| **Payment collected** — Ramesh Kumar | ₹4,500, UPI, any receipt number | Written to Salesforce, visit closed, agent is asked to attach the payment proof. Enter a *lower* amount, say ₹2,000, to show part-payment handling: the shortfall is called out and the account stays open. |
| **Promise to pay** — Ashwini More | ₹13,500, a date 3–4 days out, UPI | A `Promise_To_Pay__c` record is created and **a reminder is scheduled back to this agent** for the day before. With `HFC_DEMO_FAST=true` it arrives during the session. |
| **Customer unavailable** — Ganesh Pawar | revisit date, **Second attempt** | Revisit scheduled, and because it is the second consecutive miss it is **raised to the manager** in the internal control room. |
| **Refused to pay** — Snehal Joshi | any category, a sentence of reason | A Case is opened in Salesforce and the refusal is **escalated to `#collections-legal-ops`**, which this agent is not in. The agent's own channel says only that it was escalated. |

### Then say

> Four outcomes, four different follow-ups, none of them chosen by the agent. The agent records what happened; the workflow decides what happens next.

### Also worth showing

Type a plain message in the agent's channel — "collected from Ramesh". The bot replies, only to that agent, that chat is not the record and offers the form. **Forms are the interaction mechanism**; free text is never written to Salesforce.

---

## 2. The manager — "Who has not started or completed their work?"

**Switch to `#collections-control-room`.** Agents are not members of this channel.

### Show

1. **The activity board.** One row per partner agent: started or not, how many of the assigned visits are recorded, what was collected, what the outcomes were, and when they were last active. Agent A now shows progress; Agent B has done nothing.
2. **The repeat-miss escalation** that arrived from the second failed attempt in section 1.
3. **Nudge whoever is behind.** One click sends each agent a reminder in their own channel — and each nudge is logged to Salesforce, so *"was this agent chased, and when?"* is answerable from the system of record.

### Then run the automated nudge

In a second terminal:

```bash
./run.sh nudge 18:00
```

This forces the end-of-day checkpoint. Agent B, who has recorded nothing, gets a final nudge in their own channel **and** the manager gets an escalation in the control room naming them, with the count of what is unrecorded and the reminders already sent.

The three checkpoints are 11:00 (not started), 15:00 (still behind), and 18:00 (final + manager escalation). Each fires once per agent per day. In production this runs on a scheduler; `--at` is only so it can be shown on demand.

### Then say

> The manager never had to ask anyone for a status. And notice what the manager can see: every agent's progress, but each agent sees only their own channel. There is no shared channel where the two agents can see each other's customers.

---

## 3. The approver — "What is waiting on my decision?"

**Open `#cpa-requests`** — where a request raised in Salesforce/LOS lands and the requesting officer is told where it went.

Four requests are seeded, deliberately spanning all three routing bands:

| Request | Amount | Levels | Path |
|---|---|---|---|
| CPA-2026-00417 | ₹4,50,000 | **1** | Credit Manager |
| CPA-2026-00420 | ₹18,00,000 | **2** | Credit Manager → Credit Head |
| CPA-2026-00418 | ₹62,00,000 | **3** | Credit Manager → Credit Head → Chief Risk Officer |
| CPA-2026-00419 | ₹1,20,000 | **1** | Credit Manager |

Routing is deterministic and shown on the card: value band decides the chain, and an LTV breach or three-plus deviations adds a level.

### Show

1. **The intake card in `#cpa-requests`.** The requesting officer sees that their LOS request moved, who it is with, and the approval path — and nothing else. The documents did not come here.
2. **`#cpa-approvals-l1`.** The full card: applicant, product, amount, the policy exception, the officer's justification in their own words, the routing that brought it here, and **the supporting documents attached in the thread** — a CIBIL summary, a bank statement, a valuation report.
3. **Single-level:** approve `CPA-2026-00417`. Add a note. It completes, writes back to Salesforce, notifies the requester in `#cpa-requests`, and lands in `#cpa-audit-trail` with the REST call visible.
4. **Multi-level:** approve `CPA-2026-00420` at Level 1. The card updates to *approved at L1, now with the Credit Head* — and a fresh card appears in `#cpa-approvals-l2`, which the Level 1 approver's channel does not contain. Approve there to complete the chain.
5. **Rejection:** reject `CPA-2026-00419` with a reason. The reason is written to Salesforce and sent to the requester. Rejection stops the chain immediately — it does not travel up.
6. **Ask the officer** — where an approver needs something before deciding. The question goes back to the requester and is logged; the request stays with the approver.

### Then say

> One click each way. One level or three, driven by a rule the approver can see. The decision lands on the LOS record — Slack did not become a second approval system, it became the place the decision was made.

### ⚠️ Confirm before the session

**"CPA" was never expanded on the discovery call.** The demo shows it as *CPA Approval* and carries the expansion in a single setting. Ask HFCL what it stands for in their vocabulary, then set `HFC_CPA_EXPANSION` and `HFC_CPA_EXPANSION_CONFIRMED=true` in `.env`. Until it is confirmed, the caveat is visible in the UI so nobody in the room assumes we guessed right.

---

## 4. Internal operations and legal — "Which cases need follow-up?"

**Open `#collections-legal-ops`.** The refusal recorded by Agent A in section 1 is here, with the borrower, the bucket, the DPD, the amount, the category, and the agent's verbatim account of what the customer said.

### Show

- **Proceed — issue notice.** The card closes out, and a short update goes back to the agent's channel: *Hero FinCorp has taken this case in-house, no further visits needed.* The agent is told the outcome that affects their work — not the reasoning.
- **Send back to the agent** — one more attempt requested, which reappears in the agent's channel as a revisit.
- **Hold** — parked, nothing sent outward.

### Then say

> The escalation exists in a channel the agent who raised it cannot open. They see the outcome that changes their work and nothing else.

---

## 5. The administrator and security team — "Who can see each message, record and attachment?"

**Open `#admin-security-console`.** This is the section the customer flagged as the adoption blocker, so show evidence rather than explanation.

### Show, in this order

1. **The access matrix card** — every channel, its type, who is in it, and what external access exists.
2. **Read live membership from Slack.** The button calls `conversations.members` and prints what Slack actually reports right now, flagging any external account found in an internal channel and any channel that is public when it should be private. This is observed state, not a diagram.
3. **Run the cross-agent access test.** Six real authorisation checks against the real assignment data:

   | Attempt | Result |
   |---|---|
   | Rakesh records on his own account | ✅ allowed |
   | Rakesh reaches for Imran's account | 🚫 blocked |
   | Imran reaches for Rakesh's account | 🚫 blocked |
   | Rakesh reaches an internal escalation channel | 🚫 blocked |
   | Rakesh tries to approve a credit request | 🚫 blocked |
   | The Collections Manager reviews any agent's account | ✅ allowed |

4. **Where do attachments live?** The button spells out that a payment-proof screenshot is completed into the uploading agent's own private channel, and a customer document into the approver's private channel — and that no step in either flow posts a file into a shared or partner-facing channel.
5. **The Access & Security canvas** in the channel's Canvas tab — the same matrix in a form the security team can read after the meeting.
6. **If both agent accounts are signed in:** put the two sidebars side by side. Each shows one channel. The customer lists do not overlap.

### The four controls, in the order they apply

1. **Channel membership** — one private channel per external agent, and membership in nothing else.
2. **Record-level authorisation on the server** — every click re-checked against the record's owner, so a copied button payload still fails. This is the one worth dwelling on: channel membership alone would not survive a determined user.
3. **Forms as the interaction mechanism** — the form only ever offers the caller's own accounts, and free text is not a record.
4. **Attachment containment** — files are completed into a named private channel and never travel.

### Also raise: how external agents get into Slack

Worth putting on the table, because it is a platform-level control that sits above everything above:

- **Single-channel guests** are the natural fit — an external partner agent gets access to exactly one channel, enforced by Slack itself, not by our code. Recommended for the empanelled-partner population.
- **Slack Connect** suits partner *firms* that run their own workspace.
- **Multi-channel guests** for extended workforce members who genuinely need two or three channels.

Guest accounts have licensing implications worth confirming with HFCL's Slack account team before rollout.

---

## 6. The architecture — "Where does the data actually live?"

Keep this short; it answers the objection rather than selling anything. **Open `#salesforce-sync-log`.**

Every action taken in the last thirty minutes is in this channel as the literal REST call it produced. Scroll back through it while saying:

```
Salesforce / LOS  →  Slack task or agent interaction  →  workflow action  →  Salesforce update  →  manager visibility
```

- **Check the Salesforce connection now** — the button runs a live call against the org over the JWT Bearer Flow. No password anywhere in the integration.
- **The Canvas tab** holds the full data-ownership write-up.

### On the volume question

The discovery call put lead volume at 1,50,000–2,00,000 records a day. Say this plainly:

> That volume stays in Salesforce. What reaches Slack is the actionable slice — one agent's visits for one day, one approver's pending decisions. If a record needs no human action today, it never appears in Slack at all. Slack is not being asked to store or index the book, and there is no Slack-side database to keep in sync.

The only local state is which card to refresh and which reminder has already been sent — a few kilobytes, rebuildable from Salesforce at any time.

**`SF_WRITE_MODE` is `simulate` by default**, because the custom objects (`Collections_Visit__c`, `Promise_To_Pay__c`, `Credit_Approval_Request__c`) are not yet deployed in the demo org. Every call is built in full and shown; only the send is held back. Say so if asked — the honest version is more convincing than a mocked success, and the connection itself is live and demonstrable. Setting `SF_WRITE_MODE=live` once the objects exist changes nothing else.

---

## Coverage against what was asked

| Asked for | Where it is shown |
|---|---|
| Connected collections journey, agent's point of view | §1 — one channel, one form, four outcomes |
| Four outcomes: paid / PTP / refused / unavailable | §1 — each with its own follow-up |
| Outcome updates Salesforce | §1 and §6 — every call visible in `#salesforce-sync-log` |
| Follow-up, reminder or escalation triggered | §1 — proof request, scheduled reminder, repeat-miss escalation, legal escalation |
| Automated nudge when work is not started or finished | §2 — three checkpoints, plus manager escalation |
| Managers monitor without exposing other agents' data | §2 — the control room, which agents are not in |
| "Agent" means external partner / extended workforce | Throughout — both types are named on every card |
| CPA approval originating in Salesforce/LOS | §3 — intake in `#cpa-requests` |
| Routed to the correct approver | §3 — deterministic bands, shown on the card |
| Detail, justification, supporting attachments | §3 — full card plus documents in the thread |
| One-click approve or reject | §3 |
| One-level and multi-level | §3 — 1, 2 and 3-level requests all seeded |
| Decision written back, requester notified | §3 — `#cpa-audit-trail` and `#cpa-requests` |
| Private / restricted channels | §5 — all ten are private |
| User-specific assignments and notifications | §1, §3 — the form and the queue are scoped to the caller |
| External agents see only their own work | §5 — the cross-agent test and two sidebars |
| Internal teams get internal-only channels | §4, §5 |
| Workflow forms as the interaction mechanism | §1 — free text gets redirected to the form |
| Screenshots and documents kept from external users | §5 — attachment containment |
| Salesforce is the system of record | §6 |
| Slack is the interaction layer, not a database | §6 |
| Assignments flow in, updates flow back | §1, §6 |
| No separate Slack database | §6 |
| Not positioned as storage for 1.5–2 lakh records/day | §6 — the actionable-slice framing |
| Presented per user point of view | The structure of this document |

---

## Open questions for HFCL

1. **What does CPA stand for?** Asked on the call, never expanded. One setting to change once confirmed.
2. **How will external partner agents access Slack?** Single-channel guests, Slack Connect, or multi-channel guests — this changes the licensing conversation and adds a platform-level control worth having.
3. **Which Salesforce objects should the write-back target?** The demo assumes `Collections_Visit__c`, `Promise_To_Pay__c` and `Credit_Approval_Request__c`; all are configurable in `.env`. Confirm the real API names and the approval-matrix thresholds.
4. **Are the approval bands right?** ₹5L and ₹25L are placeholders chosen to make the demo legible. HFCL's real delegation-of-authority matrix should replace them.
5. **How many accounts does a partner agent carry per day?** The volume framing in §6 assumes 15–25. Worth confirming, since it is the number that answers the storage objection.

---

## Housekeeping

**The eight legacy public channels** from the original four use cases (`#collections-bucket2`, `#credit-deviation-approvals` and so on) are still public. They contain no partner-facing data, but a customer looking at the sidebar during a security conversation will notice. Before the session, either archive them or convert them to private in the Slack UI — there is no standard API for converting a public channel, so it has to be done by hand.

**Between runs:** `./run.sh reset` deletes the bot's messages from the journey channels, cancels any reminders it scheduled, clears the day's progress, and re-posts the opening cards.
