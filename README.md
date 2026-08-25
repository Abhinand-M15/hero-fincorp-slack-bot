# Hero FinCorp Slack Bot

A working Slack bot (Socket Mode, `slack-bolt`) demonstrating 4 operational workflows on top of Hero FinCorp's Salesforce foundation:

1. **Knowledge Base Bot** — policy Q&A backed by a Slack Canvas
2. **Field Collections** — DPD-bucket-based visit logging, with automatic legal escalation logic
3. **Credit Deviation Approval** — a pending-approvals queue with a two-step review modal
4. **Lead Swarming** — inside-sales lead tracking with a self-shrinking queue and handoff to Field/RM

Plus a proven Salesforce JWT Bearer Flow connection (`sf_auth.py`) — no password ever used.

## What you need before running this

This repo has **no secrets in it** — you need two things from whoever gave you this link, sent to you outside of GitHub:

1. **Values for a `.env` file** — see `.env.example` for the exact variable names. Copy `.env.example` to `.env` and fill in the real values you were given.
2. **The `server.key` file** — the private key that matches the certificate already registered on the `Hero FinCorp Bot API` Connected App in Salesforce. This must be the **exact file** you were given — do not generate a new one, it won't match what's registered. Place it directly in this folder (same directory as `app.py`).

## Setup

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in the real values (given to you separately, not in this repo). Place the `server.key` file you were given into this same folder.

## Running it

```bash
python app.py
```

You should see:
```
Hero FinCorp Bot starting (Socket Mode)...
Bolt app is running!
```

If you see an error instead, it's almost always one of:
- `.env` is missing a value, or wasn't created at all
- `server.key` isn't in this folder, or isn't the exact file you were given

## Verifying the Salesforce connection separately

```bash
python sf_auth.py
```

Should print `AUTH SUCCESS` and an `instance_url`. If it prints `AUTH FAILED`, check the `.env` values and that `server.key` is correct — Salesforce auth doesn't depend on the Slack bot running.

## One-time setup scripts (already run once — only needed if starting fresh)

- `create_channels.py` — creates the 8 channels this bot uses
- `create_canvas.py` — creates the knowledge base Canvas
- `populate_demo.py` — posts the initial assignment-queue cards
- `invite_users.py` — adds specific users to all the channels (edit the user IDs first)
- `clear_channel.py` — deletes all bot-posted messages from one, several, or all channels (`--all`) — useful to reset before a demo

## Files

| File | Purpose |
|---|---|
| `app.py` | The running bot — all Slack event/action/view handlers |
| `slack_client.py` | Thin wrapper around Slack's Web API |
| `slack_blocks.py` | All Block Kit card and modal builders |
| `queues.py` | Sample data — leads, loan accounts, pending approvals |
| `queue_state.py` | Tracks which channel/message a live queue card lives at, so it can be updated in place |
| `audit_log.py` | Local audit trail (`audit_log.jsonl`) of every action taken |
| `sf_auth.py` | Salesforce JWT Bearer Flow authentication |
| `canvas_content.py` | The knowledge base Canvas markdown content |
