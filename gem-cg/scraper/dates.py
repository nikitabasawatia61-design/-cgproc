import re
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

DATE_FORMATS = [
    "%d %b, %Y %I:%M:%S %p IST",
    "%d %b, %Y %I:%M:%S %p",
    "%d %b %Y %I:%M:%S %p IST",
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
]


def parse_last_date(value):
    if not value:
        return None

    text = re.sub(r"\s+", " ", str(value).strip())
    if not text:
        return None

    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=IST)
        except ValueError:
            continue

    return None


def is_tender_closed(last_date, now=None):
    parsed = parse_last_date(last_date)
    if parsed is None:
        return False

    current = now or datetime.now(IST)
    return parsed < current
