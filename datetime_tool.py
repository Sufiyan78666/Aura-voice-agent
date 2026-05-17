"""
datetime_tool.py  Voice Agent Date/Time Tool
Returns current time, date, or day based on user query.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
import pytz

IST = pytz.timezone("Asia/Kolkata")

def get_date_time(request_text: Optional[str] = None) -> str:
    now = datetime.now(IST)

    wants_time = False
    wants_date = False

    if request_text:
        t = request_text.lower()
        time_keywords = ["time", "samay", "baje", "clock"]
        date_keywords = ["date", "day", "today", "aaj", "din", "tareekh", "tarikh"]

        wants_time = any(k in t for k in time_keywords)
        wants_date = any(k in t for k in date_keywords)

    if wants_time and wants_date:
        date_part = now.strftime("%A, %d %B %Y")
        time_part = now.strftime("%I:%M %p")
        return f"Today is {date_part}. The time is {time_part}."

    if wants_date:
        date_part = now.strftime("%A, %d %B %Y")
        return f"Today is {date_part}."

    time_part = now.strftime("%I:%M %p")
    return f"Current time is {time_part}."

if __name__ == "__main__":
    print(get_date_time("what time is it"))
    print(get_date_time("what day is today"))