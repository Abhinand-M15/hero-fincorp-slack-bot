"""
One entry point for running the Hero FinCorp demo.

    python demo.py              check everything, set up if needed, start the bot
    python demo.py check        pre-flight only — no changes to the workspace
    python demo.py setup        create channels, invite people, post the opening cards
    python demo.py start        start the bot (assumes setup has been done)
    python demo.py reset        wipe the journey channels and re-post the cards
    python demo.py nudge 18:00  fire a nudge checkpoint on demand
    python demo.py review       read live channel membership back out of Slack
    python demo.py test         run the offline self-test only

    python demo.py --fresh      reset first, then set up and start

Everything is safe to re-run. Setup skips channels that already exist, and the
default command only posts the opening cards if they are not already there.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

GREEN, RED, BOLD, DIM, RESET = "\033[32m", "\033[31m", "\033[1m", "\033[2m", "\033[0m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    GREEN = RED = BOLD = DIM = RESET = ""


def banner(text):
    # Flushed, because the scripts below write to the same terminal directly —
    # without this the headings land out of order when the output is piped.
    print(f"\n{BOLD}{text}{RESET}", flush=True)
    print("=" * max(len(text), 62), flush=True)


def run_script(name, *args, check=True):
    """Run one of the repo's scripts as a subprocess and return its exit code."""
    result = subprocess.run([PYTHON, os.path.join(HERE, name), *args], cwd=HERE)
    if check and result.returncode != 0:
        print(f"\n{RED}{name} failed (exit {result.returncode}).{RESET}")
        sys.exit(result.returncode)
    return result.returncode


def already_set_up():
    """Have the opening cards been posted into this workspace already?"""
    import journey_state
    return bool(journey_state.get_card("activity_board"))


def cmd_test():
    banner("Offline self-test")
    run_script("selftest.py")


def cmd_check():
    banner("Pre-flight")
    import preflight
    if not preflight.run():
        print(f"\n{RED}Fix the blocking problems above, then run this again.{RESET}")
        sys.exit(1)


def cmd_setup():
    banner("Workspace setup")
    run_script("demo_assets.py")
    run_script("setup_journey.py")


def cmd_review():
    banner("Live access review")
    # Non-zero here means membership differs from the access matrix, which is
    # worth seeing but is not a reason to refuse to start.
    code = run_script("access_review.py", check=False)
    if code != 0:
        print(f"\n{RED}Membership does not match the access matrix — see the flagged rows above.{RESET}")
        print(f"{DIM}Run: python demo.py setup   to re-apply invites, or fix membership in Slack.{RESET}")


def cmd_reset():
    banner("Reset")
    run_script("reset_demo.py")


def cmd_nudge(checkpoint=None):
    banner(f"Nudge checkpoint{f' — {checkpoint}' if checkpoint else ''}")
    args = ["--at", checkpoint] if checkpoint else []
    run_script("nudge_engine.py", *args, check=False)


def cmd_start():
    banner("Starting the bot")
    print(f"{DIM}Socket Mode — no public URL needed. Ctrl-C to stop.{RESET}\n")
    print(f"{BOLD}Try this first:{RESET}")
    print("  1. Open  #collections-agent-pune-01   and click  ▶️  Start my day")
    print("  2. Click  📝  Record visit outcome    and log a Payment collected")
    print("  3. Watch  #collections-control-room   and  #salesforce-sync-log  update")
    print("  4. Open   #admin-security-console     and run the cross-agent access test")
    print(f"\n{DIM}Full runbook: DEMO_SCRIPT.md{RESET}\n", flush=True)

    try:
        code = subprocess.call([PYTHON, os.path.join(HERE, "app.py")], cwd=HERE)
    except KeyboardInterrupt:
        code = 0
    print(f"\n{DIM}Bot stopped.{RESET}")
    sys.exit(code)


def cmd_up(fresh=False):
    cmd_test()
    cmd_check()

    if fresh:
        cmd_reset()
    elif already_set_up():
        banner("Workspace setup")
        print(f"  {GREEN}✓{RESET} already set up — the opening cards are posted.")
        print(f"    {DIM}To start over from a clean workspace: python demo.py --fresh{RESET}", flush=True)
    else:
        cmd_setup()

    cmd_review()
    cmd_start()


COMMANDS = {
    "up": cmd_up,
    "check": cmd_check,
    "setup": cmd_setup,
    "start": cmd_start,
    "reset": cmd_reset,
    "review": cmd_review,
    "test": cmd_test,
}


def main():
    args = [a for a in sys.argv[1:]]
    fresh = "--fresh" in args
    args = [a for a in args if a != "--fresh"]

    if args and args[0] in {"-h", "--help", "help"}:
        print(__doc__)
        return

    command = args[0] if args else "up"

    if command == "nudge":
        cmd_nudge(args[1] if len(args) > 1 else None)
        return

    if command not in COMMANDS:
        print(f"{RED}Unknown command: {command}{RESET}")
        print(__doc__)
        sys.exit(2)

    if command == "up":
        cmd_up(fresh=fresh)
    else:
        if fresh and command in {"setup", "start"}:
            cmd_reset()
        COMMANDS[command]()


if __name__ == "__main__":
    main()
