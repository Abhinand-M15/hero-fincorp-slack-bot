#!/usr/bin/env bash
#
# Hero FinCorp demo launcher.
#
#   ./run.sh              set everything up if needed, then start the bot
#   ./run.sh check        pre-flight only — touches nothing
#   ./run.sh setup        create the channels, invite people, post the cards
#   ./run.sh start        start the bot
#   ./run.sh reset        wipe the journey channels and re-post the cards
#   ./run.sh nudge 18:00  fire a nudge checkpoint on demand
#   ./run.sh review       read live channel membership out of Slack
#   ./run.sh test         offline self-test only — no Slack, no Salesforce
#   ./run.sh --fresh      reset first, then set up and start
#
# Creates the virtualenv and installs dependencies on first run.
# On Windows, skip this script and use:  python demo.py

set -euo pipefail

cd "$(dirname "$0")"

BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'
if [ ! -t 1 ]; then BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; RESET=""; fi

# --- find a usable Python -----------------------------------------------------

PY_BIN=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      PY_BIN="$candidate"
      break
    fi
  fi
done

if [ -z "$PY_BIN" ]; then
  echo "${RED}No Python 3.9+ found on PATH.${RESET}"
  echo "  Install it from https://www.python.org/downloads/ and run this again."
  exit 1
fi

# --- virtualenv ---------------------------------------------------------------

VENV_PY="venv/bin/python"
[ -x "$VENV_PY" ] || VENV_PY="venv/Scripts/python.exe"   # Git Bash on Windows

if [ ! -x "$VENV_PY" ]; then
  echo "${BOLD}Creating the virtualenv${RESET} ${DIM}(first run only)${RESET}"
  "$PY_BIN" -m venv venv
  VENV_PY="venv/bin/python"
  [ -x "$VENV_PY" ] || VENV_PY="venv/Scripts/python.exe"
fi

# Cheap check: reinstall only when a dependency is actually missing or
# requirements.txt has changed since the last successful install.
STAMP="venv/.requirements-stamp"
NEED_INSTALL=0
if ! "$VENV_PY" -c "import slack_bolt, slack_sdk, jwt, dotenv, requests" >/dev/null 2>&1; then
  NEED_INSTALL=1
elif [ ! -f "$STAMP" ] || [ requirements.txt -nt "$STAMP" ]; then
  NEED_INSTALL=1
fi

if [ "$NEED_INSTALL" -eq 1 ]; then
  echo "${BOLD}Installing dependencies${RESET}"
  "$VENV_PY" -m pip install --quiet --disable-pip-version-check --upgrade pip
  "$VENV_PY" -m pip install --quiet --disable-pip-version-check -r requirements.txt
  touch "$STAMP"
  echo "  ${GREEN}✓${RESET} dependencies ready"
fi

# --- .env ---------------------------------------------------------------------

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "${YELLOW}Created .env from .env.example.${RESET}"
  echo ""
  echo "Fill in these two before anything can talk to Slack:"
  echo "  ${BOLD}SLACK_BOT_TOKEN${RESET}   starts with xoxb-   (Slack app → OAuth & Permissions)"
  echo "  ${BOLD}SLACK_APP_TOKEN${RESET}   starts with xapp-   (Slack app → Basic Information → App-Level Tokens,"
  echo "                                       with the connections:write scope)"
  echo ""
  echo "Everything else in .env is optional — the demo runs Slack-only without Salesforce."
  echo "For a live session also set ${BOLD}HFC_DEMO_FAST=true${RESET} so scheduled reminders arrive during it."
  echo ""
  echo "Then run this again:  ${BOLD}./run.sh${RESET}"
  exit 1
fi

# --- hand over to the Python orchestrator ------------------------------------

exec "$VENV_PY" demo.py "$@"
