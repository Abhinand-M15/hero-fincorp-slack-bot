"""
Pre-flight checks — everything that has to be true before the demo will work,
checked in the order it will break if it is not.

    ./venv/bin/python preflight.py

Blocking problems stop the run and say exactly what to fix. Advisory ones
(Salesforce not configured, persona IDs unset) are reported and allowed
through, because the Slack half of the demo runs fine without them.
"""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

# Scopes the bot genuinely uses, and what breaks without each one.
REQUIRED_SCOPES = {
    "chat:write": "post any message",
    "channels:read": "find public channels",
    "groups:read": "find the private journey channels",
    "groups:write": "create the private journey channels",
    "channels:manage": "create the legacy public channels",
    "users:read": "resolve who clicked a button",
    "files:write": "attach the supporting documents to an approval",
    "canvases:write": "create the security and architecture canvases",
    "channels:history": "receive the message.channels event the knowledge base bot answers",
    "groups:history": "receive message.groups in the private agent channels, and read history so "
                      "reset can clear old messages",
}
OPTIONAL_SCOPES = {
    "files:read": "read details of a file an agent uploads",
    "im:write": "send a direct message instead of a channel post",
}

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    GREEN = RED = YELLOW = DIM = RESET = ""

PASS = f"{GREEN}✓{RESET}"
FAIL = f"{RED}✗{RESET}"
WARN = f"{YELLOW}!{RESET}"


class Report:
    def __init__(self):
        self.blocking = []
        self.advisory = []

    def ok(self, label, detail=""):
        print(f"  {PASS} {label}" + (f"  {DIM}{detail}{RESET}" if detail else ""))

    def fail(self, label, fix):
        print(f"  {FAIL} {label}")
        print(f"      {DIM}fix: {fix}{RESET}")
        self.blocking.append(label)

    def warn(self, label, detail=""):
        print(f"  {WARN} {label}" + (f"  {DIM}{detail}{RESET}" if detail else ""))
        self.advisory.append(label)


def check_env_file(report):
    print("\nEnvironment")
    here = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(here, ".env")):
        report.fail(".env not found",
                    "cp .env.example .env  — then fill in the values you were given")
        return False
    report.ok(".env found")

    bot = os.environ.get("SLACK_BOT_TOKEN", "")
    app = os.environ.get("SLACK_APP_TOKEN", "")

    if not bot:
        report.fail("SLACK_BOT_TOKEN is empty", "add it to .env — it starts with xoxb-")
    elif not bot.startswith("xoxb-"):
        report.warn("SLACK_BOT_TOKEN does not start with xoxb-", "check you have the bot token, not the app token")
    else:
        report.ok("SLACK_BOT_TOKEN set", f"{bot[:9]}…")

    if not app:
        report.fail("SLACK_APP_TOKEN is empty",
                    "add it to .env — it starts with xapp- and needs the connections:write scope")
    elif not app.startswith("xapp-"):
        report.warn("SLACK_APP_TOKEN does not start with xapp-", "Socket Mode needs an app-level token")
    else:
        report.ok("SLACK_APP_TOKEN set", f"{app[:9]}…")

    return bool(bot)


def check_slack(report):
    print("\nSlack connection")
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        report.warn("skipped — no bot token to test")
        return

    try:
        response = requests.post(
            "https://slack.com/api/auth.test",
            headers={"Authorization": f"Bearer {token}"}, timeout=15,
        )
    except requests.RequestException as exc:
        report.fail(f"cannot reach Slack — {exc}", "check network access to slack.com")
        return

    data = response.json()
    if not data.get("ok"):
        report.fail(f"Slack rejected the bot token — {data.get('error')}",
                    "regenerate the bot token in the Slack app's OAuth & Permissions page and reinstall the app")
        return

    report.ok(f"authenticated as {data.get('user')}", f"workspace: {data.get('team')}")

    granted = {s.strip() for s in response.headers.get("x-oauth-scopes", "").split(",") if s.strip()}
    if not granted:
        report.warn("Slack did not report the granted scopes", "cannot verify permissions — continuing")
        return

    missing = [s for s in REQUIRED_SCOPES if s not in granted]
    if missing:
        for scope in missing:
            report.fail(f"missing scope {scope}", f"needed to {REQUIRED_SCOPES[scope]} — add it in OAuth & Permissions, then reinstall the app")
    else:
        report.ok(f"all {len(REQUIRED_SCOPES)} required scopes granted")

    missing_optional = [s for s in OPTIONAL_SCOPES if s not in granted]
    if missing_optional:
        report.warn(f"optional scopes not granted: {', '.join(missing_optional)}",
                    "the demo runs without them")


def check_personas(report):
    print("\nDemo personas")
    import personas

    agents_set = [a for a in personas.PARTNER_AGENTS.values() if a["slack_id"]]
    staff_set = [p for p in personas.INTERNAL_STAFF.values() if p["slack_id"]]
    presenters = personas.PRESENTER_SLACK_IDS

    # The bot creates the journey channels privately. If nobody is invited,
    # setup appears to succeed and then no human can see a single channel.
    if presenters:
        report.ok(f"{len(presenters)} presenter account(s) will be invited to every journey channel",
                  "identity follows the channel they act in")
    elif agents_set or staff_set:
        report.warn("HFC_PRESENTER_SLACK_IDS is not set",
                    "only the mapped personas will be able to see the private channels")
    else:
        report.fail("nobody would be able to see the private channels",
                    "set HFC_PRESENTER_SLACK_IDS in .env to your own Slack member ID "
                    "(Slack → your profile → ⋮ → Copy member ID). Without it the bot is the "
                    "only member of every channel it creates.")

    if len(agents_set) == 2:
        report.ok("both sample partner agents mapped to Slack accounts",
                  "the two-sidebar isolation demo will work")
    elif len(agents_set) == 1:
        report.warn("only one partner agent has a Slack ID",
                    "the cross-agent access test still proves isolation from the server side")
    else:
        report.warn("no partner agent Slack IDs set (HFC_AGENT_A_SLACK_ID, HFC_AGENT_B_SLACK_ID)",
                    "relaxed access mode identifies agents by channel, so the journey still runs")

    if staff_set:
        report.ok(f"{len(staff_set)} internal persona(s) mapped")
    else:
        report.warn("no internal persona Slack IDs set", "channel invites will be skipped")

    mode = os.environ.get("HFC_ACCESS_MODE", "relaxed").lower()
    if mode == "strict" and not agents_set:
        report.fail("HFC_ACCESS_MODE=strict but no persona Slack IDs are set",
                    "set the HFC_*_SLACK_ID values, or use HFC_ACCESS_MODE=relaxed")
    else:
        report.ok(f"access mode: {mode}")


def check_salesforce(report):
    print("\nSalesforce")
    import sf_auth
    import sf_bridge

    missing = sf_auth.missing_config()
    if missing:
        report.warn(f"not configured — missing {', '.join(missing)}",
                    "the demo runs Slack-only; every write is shown as a simulated REST call")
        return

    ok, detail, instance = sf_bridge.probe()
    if ok:
        report.ok("connected over JWT Bearer Flow", instance)
        report.ok(f"write mode: {sf_bridge.WRITE_MODE}")
    else:
        report.warn(f"configured but the connection failed — {detail}",
                    "the Slack half of the demo is unaffected")


def check_demo_settings(report):
    print("\nDemo settings")
    fast = os.environ.get("HFC_DEMO_FAST", "false").lower() == "true"
    if fast:
        report.ok("HFC_DEMO_FAST=true", "promise-to-pay reminders arrive ~90 seconds later, so they are visible live")
    else:
        report.warn("HFC_DEMO_FAST is off",
                    "scheduled reminders will land on their real date and will not be seen during the session")

    import cpa_approvals as cpa
    if cpa.CPA_EXPANSION_CONFIRMED:
        report.ok(f"CPA expansion confirmed: {cpa.CPA_EXPANSION}")
    else:
        report.warn(f"CPA expansion unconfirmed (showing \"{cpa.CPA_EXPANSION}\")",
                    "confirm with HFCL, then set HFC_CPA_EXPANSION_CONFIRMED=true")


def run(include_slack=True):
    report = Report()
    have_token = check_env_file(report)
    if include_slack and have_token:
        check_slack(report)
    check_personas(report)
    check_salesforce(report)
    check_demo_settings(report)

    print("\n" + "-" * 62)
    if report.blocking:
        print(f"{RED}NOT READY{RESET} — {len(report.blocking)} blocking problem(s) above.")
    elif report.advisory:
        print(f"{GREEN}READY{RESET} — {len(report.advisory)} advisory note(s) above, none of them blocking.")
    else:
        print(f"{GREEN}READY{RESET} — everything checks out.")
    return not report.blocking


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
