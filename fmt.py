"""Small shared formatters, so dates and amounts read the same on every card."""
from datetime import date, datetime, timezone


def human_date(value):
    """dd MMM yyyy — e.g. 29 Aug 2026."""
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value[:10])
        except ValueError:
            return value
    return value.strftime("%d %b %Y")


def human_time(iso_string):
    """dd MMM yyyy, HH:MM from an ISO timestamp."""
    if not iso_string:
        return "—"
    try:
        stamp = datetime.fromisoformat(iso_string)
    except ValueError:
        return iso_string
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.strftime("%d %b %Y, %H:%M")


def rupees(amount):
    """Indian digit grouping: 1,24,000 rather than 124,000."""
    try:
        amount = int(round(float(amount)))
    except (TypeError, ValueError):
        return f"₹{amount}"
    sign = "-" if amount < 0 else ""
    digits = str(abs(amount))
    if len(digits) <= 3:
        return f"{sign}₹{digits}"
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return f"{sign}₹{','.join(parts)},{tail}"


def today():
    return date.today()
