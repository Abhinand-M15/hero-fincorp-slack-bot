"""
Create the knowledge base Canvas and attach it to #branch-support-escalations
as that channel's Canvas tab.
"""
from slack_client import api_call, find_channel_id
from canvas_content import CANVAS_MARKDOWN

if __name__ == "__main__":
    branch_support = find_channel_id("branch-support-escalations")
    bucket2 = find_channel_id("collections-bucket2")
    bucket3 = find_channel_id("collections-bucket3")
    npa = find_channel_id("collections-npa")
    deviation = find_channel_id("credit-deviation-approvals")

    markdown = CANVAS_MARKDOWN.format(
        branch_support_channel=branch_support,
        bucket2_channel=bucket2,
        bucket3_channel=bucket3,
        npa_channel=npa,
        deviation_channel=deviation,
    )

    result = api_call("canvases.create", {
        "title": "Hero FinCorp Branch Knowledge Base",
        "document_content": {"type": "markdown", "markdown": markdown},
        "channel_id": branch_support,
    })

    if result.get("ok"):
        print("CANVAS CREATED:", result.get("canvas_id"))
    else:
        print("CANVAS FAILED:", result.get("error"), result)
