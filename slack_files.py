"""
File uploads, using Slack's current external-upload flow
(files.getUploadURLExternal -> PUT -> files.completeUploadExternal).

Where a file lands is the whole point for this demo: a customer document or a
payment-proof screenshot is completed *into a specific channel*, and in this
workspace those channels are private. A file shared into #cpa-approvals-l1 is
reachable only by the members of #cpa-approvals-l1 — an external partner agent
is not one of them, so the document never becomes visible to them.
"""
import os

import requests

from app_config import SLACK_BOT_TOKEN
from slack_client import api_call

BASE = "https://slack.com/api"


def _form_call(method, params):
    """
    files.getUploadURLExternal rejects a JSON body — it only reads
    form-encoded parameters, unlike almost every other Web API method. Hence
    this rather than the shared JSON helper in slack_client.py.
    """
    response = requests.post(
        f"{BASE}/{method}",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        data=params,
    )
    result = response.json()
    if not result.get("ok"):
        print(f"SLACK API ERROR [{method}]: {result.get('error')} | {result}")
    return result


def upload_to_channel(path, channel_id, title=None, initial_comment=None, thread_ts=None):
    """
    Upload one local file into one channel. Returns the Slack file object, or
    None if any step failed (the error is printed by api_call).
    """
    if not os.path.exists(path):
        print(f"UPLOAD SKIPPED — missing file: {path}")
        return None

    filename = os.path.basename(path)
    length = os.path.getsize(path)

    ticket = _form_call("files.getUploadURLExternal", {"filename": filename, "length": length})
    if not ticket.get("ok"):
        return None

    with open(path, "rb") as f:
        put = requests.post(ticket["upload_url"], files={"file": (filename, f)})
    if put.status_code >= 400:
        print(f"UPLOAD FAILED [{filename}]: HTTP {put.status_code}")
        return None

    payload = {
        "files": [{"id": ticket["file_id"], "title": title or filename}],
        "channel_id": channel_id,
    }
    if initial_comment:
        payload["initial_comment"] = initial_comment
    if thread_ts:
        payload["thread_ts"] = thread_ts

    completed = api_call("files.completeUploadExternal", payload)
    if not completed.get("ok"):
        return None
    files = completed.get("files") or []
    return files[0] if files else None


def upload_many(paths, channel_id, initial_comment=None, thread_ts=None):
    uploaded = []
    for index, path in enumerate(paths):
        result = upload_to_channel(
            path, channel_id,
            initial_comment=initial_comment if index == 0 else None,
            thread_ts=thread_ts,
        )
        if result:
            uploaded.append(result)
    return uploaded


def file_permalink(file_obj):
    return (file_obj or {}).get("permalink", "")
