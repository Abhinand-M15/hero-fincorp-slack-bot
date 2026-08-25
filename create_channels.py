"""
One-time setup: create all channels needed across the 4 Hero FinCorp use cases.
Safe to re-run — create_channel() skips channels that already exist.
"""
from slack_client import create_channel

CHANNELS = [
    # Use case 1: Knowledge base bot
    ("branch-support-escalations", False),

    # Use case 2: Field collections coordination
    ("collections-bucket2", False),
    ("collections-bucket3", False),
    ("collections-npa", False),
    ("legal-escalations", False),

    # Use case 3: Credit deviation approval
    ("credit-deviation-approvals", False),

    # Use case 4: Lead swarming
    ("lead-swarming", False),
    ("field-collections-intake", False),
]

if __name__ == "__main__":
    for name, is_private in CHANNELS:
        create_channel(name, is_private)
