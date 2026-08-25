"""
Posts the assignment-queue cards into each channel — this is the "what to
work on" view for each role, with a button that opens the real logging form.
"""
from slack_client import post_message, find_channel_id
from slack_blocks import bucket_queue_card, deviation_queue_card, lead_queue_card
from queues import BUCKET_QUEUES, BUCKET_LABELS, DEVIATION_QUEUE, LEAD_QUEUE
from queue_state import remember_queue_message

if __name__ == "__main__":
    for name, label in BUCKET_LABELS.items():
        ch = find_channel_id(name)
        text, blocks = bucket_queue_card(label, BUCKET_QUEUES[name])
        post_message(ch, text=text, blocks=blocks)
        print(f"Posted assignment queue to #{name}")

    ch = find_channel_id("credit-deviation-approvals")
    text, blocks = deviation_queue_card(DEVIATION_QUEUE)
    post_message(ch, text=text, blocks=blocks)
    print("Posted deviation queue to #credit-deviation-approvals")

    ch = find_channel_id("lead-swarming")
    text, blocks = lead_queue_card(LEAD_QUEUE)
    result = post_message(ch, text=text, blocks=blocks)
    if result.get("ok"):
        remember_queue_message("lead_queue", ch, result["ts"])
    print("Posted lead queue to #lead-swarming")
