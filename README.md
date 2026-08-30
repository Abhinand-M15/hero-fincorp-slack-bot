# Hero FinCorp Slack Bot

A working Slack bot (Socket Mode, `slack-bolt`) on top of Hero FinCorp's Salesforce foundation.

**Two layers.** The original four workflows, and the connected end-to-end journeys built for the customer walkthrough.

### The four workflows

1. **Knowledge Base Bot** — policy Q&A backed by a Slack Canvas
2. **Field Collections** — DPD-bucket visit logging with automatic legal escalation
3. **Credit Deviation Approval** — a pending-approvals queue with a two-step review modal
4. **Lead Swarming** — inside-sales lead tracking with a self-shrinking queue and handoff

### The connected journeys

5. **Partner-agent collections + nudges** — an external partner or extended-workforce agent gets their own private channel, records visit outcomes on a form, and every outcome writes back to Salesforce and fires its own follow-up. If the day's work is not started or not finished, Slack nudges the agent and then escalates to their manager.
6. **CPA approvals** — a request raised in Salesforce/LOS is routed to the right approver by value band, shown with its justification and supporting documents, decided in one click, moved up the chain where more than one level is needed, and written back.
7. **Security, access and data ownership consoles** — live channel membership read back out of Slack, real authorisation checks run on demand, and every Salesforce call visible as it happens.

Plus a proven Salesforce JWT Bearer Flow connection (`sf_auth.py`) — no password ever used.

**Running the demo: see [DEMO_SCRIPT.md](DEMO_SCRIPT.md).** It is written per user point of view, which is how the customer asked to see it.

## What you need before running this

This repo has **no secrets in it** — you need two things from whoever gave you this link, sent to you outside of GitHub:

1. **Two Slack tokens and your own member ID** — a bot token (`xoxb-…`), an app-level token (`xapp-…`) with `connections:write`, and `HFC_PRESENTER_SLACK_IDS` set to your Slack member ID. The member ID matters: the bot creates the journey channels privately, so without it the bot is the only member and you will not see them. `./run.sh` writes a `.env` for you on first run; see `.env.example` for what every variable does.
2. **The `server.key` file** — *optional.* The private key matching the certificate registered on the `Hero FinCorp Bot API` Connected App in Salesforce. Without it the demo runs Slack-only: every Salesforce call is built in full and shown, but not sent. This must be the **exact file** you were given — a newly generated one will not match.

## Quick start

```bash
./run.sh
```

That is the whole thing. On first run it creates the virtualenv, installs
dependencies, and writes a `.env` for you to fill in. Run it again once the two
Slack tokens are in place and it will check the setup, create the channels,
post the opening cards, and start the bot.

On Windows, or if you would rather not use the shell wrapper:

```bash
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python demo.py
```

### The other commands

```bash
./run.sh check        # pre-flight only — changes nothing
./run.sh test         # 800+ offline checks, no Slack or Salesforce needed
./run.sh setup        # create channels, invite people, post the opening cards
./run.sh start        # start the bot on its own
./run.sh review       # read live channel membership back out of Slack
./run.sh nudge 18:00  # fire a nudge checkpoint on demand
./run.sh reset        # wipe the journey channels and re-post the cards
./run.sh --fresh      # reset, then set up and start
```

`./run.sh check` is worth knowing about: it verifies the tokens, checks the bot
has every OAuth scope the demo needs (and names the ones it is missing), reports
whether Salesforce is configured, and warns if `HFC_DEMO_FAST` is off — which is
the difference between the scheduled reminders being visible during a session or
not. Nothing it does touches the workspace.

## Slack app scopes

The bot token needs:

```
chat:write          channels:read       groups:read         groups:write
channels:manage     users:read          files:read          files:write
canvases:write      im:write
```

Event subscriptions: `message.channels`, `message.groups`. Socket Mode on, with an app-level token carrying `connections:write`.

## What the bot prints when it starts

```
Hero FinCorp Bot starting (Socket Mode)...
  workflows: knowledge base · bucket collections · credit deviation · lead swarming
  journeys:  partner-agent collections + nudges · CPA approvals · security console
Bolt app is running!
```

If something is wrong, `./run.sh check` will have said so before it got this far.

## Verifying the connections separately

```bash
python sf_auth.py       # AUTH SUCCESS + instance_url
python sf_bridge.py     # live call against the org, plus the current write mode
python slack_client.py  # AUTH SUCCESS + team and bot identity
```

Salesforce auth does not depend on the Slack bot running, or the other way round.

## Scripts

| Script | Purpose |
|---|---|
| `run.sh` | Launcher — virtualenv, dependencies, `.env`, then hands over to `demo.py` |
| `demo.py` | The orchestrator behind every `run.sh` subcommand |
| `preflight.py` | Verifies tokens, OAuth scopes, personas, Salesforce and demo settings |
| `selftest.py` | Offline checks: routing, access control, nudges, Block Kit structure, handler wiring |
| `setup_journey.py` | Creates the journey channels, invites the personas, creates the canvases, posts the opening cards |
| `access_review.py` | Reads live channel membership and checks it against the access matrix (`--post` to publish it to the security console) |
| `nudge_engine.py` | Runs the nudge checkpoints (`--at 18:00` to force one, `--watch` to loop, `--dry-run` to preview) |
| `reset_demo.py` | Clears the journey channels, cancels scheduled reminders, resets the day, re-posts the cards |
| `demo_assets.py` | Generates the sample customer documents used by the approval demo |
| `create_channels.py` | Creates the eight legacy public channels |
| `create_canvas.py` | Creates the knowledge base Canvas |
| `populate_demo.py` | Posts the original assignment-queue cards |
| `invite_users.py` | Invites everyone to the legacy channels, and only the permitted personas to the journey channels |
| `clear_channel.py` | Deletes bot-posted messages from one, several, or all channels (`--all`) |

## Files

| File | Purpose |
|---|---|
| `app.py` | The running bot — the original four use cases, and registration of the journey handlers |
| `personas.py` | Who is who: two sample partner agents, internal staff, and their Slack IDs |
| `channels.py` | Channel registry — name, private or not, and who belongs in it |
| `access.py` | Server-side authorisation, re-checked on every click |
| `collections_journey.py` | Today's assignments and the follow-up rules for each outcome |
| `cpa_approvals.py` | CPA requests, the routing bands, and the approval state machine |
| `sf_bridge.py` | Every Salesforce read and write, in one place, with a simulate mode |
| `nudge_engine.py` | The nudge checkpoints and the manager escalation |
| `journey_state.py` | Which card to refresh and which nudge already fired — nothing else is kept locally |
| `handlers_collections.py` / `handlers_cpa.py` / `handlers_security.py` | The journey handlers |
| `blocks_journey.py` / `blocks_cpa.py` / `blocks_security.py` | Block Kit for the journeys |
| `slack_util.py` | Channel and user lookups with a cache |
| `slack_files.py` | File uploads, completed into one named private channel |
| `fmt.py` | Date and rupee formatting |
| `slack_client.py` | Thin wrapper around Slack's Web API |
| `slack_blocks.py` | Block Kit for the original four use cases |
| `queues.py` | Sample data for the original four use cases |
| `queue_state.py` | Message positions for the original queue cards |
| `audit_log.py` | Local audit trail (`audit_log.jsonl`) of every action, including every refusal |
| `sf_auth.py` | Salesforce JWT Bearer Flow authentication |
| `kb_answers.py` | Keyword-matched knowledge base answers |
| `canvas_content*.py` | Canvas markdown — knowledge base, lending, buckets, EMI, security, architecture |

## A note on Salesforce writes

`SF_WRITE_MODE` defaults to `simulate`: every call is built in full and shown in `#salesforce-sync-log`, but not sent, because the custom objects it targets are not yet deployed in the demo org. The connection itself is live and provable (`sf_bridge.py`). Set `SF_WRITE_MODE=live` once the objects exist — nothing else changes.
