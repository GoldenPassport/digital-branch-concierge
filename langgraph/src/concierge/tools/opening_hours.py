from datetime import date

from langchain.tools import tool

HOURS = {
    "monday": "09:00 to 17:00",
    "tuesday": "09:00 to 17:00",
    "wednesday": "09:00 to 17:00",
    "thursday": "09:00 to 17:00",
    "friday": "09:00 to 17:00",
    "saturday": "09:00 to 13:00",
    "sunday": "closed",
}


@tool
def opening_hours(day: str = "today") -> str:
    """Read-only lookup of branch opening hours. Input: a day name or 'today'. Returns the hours as text."""
    today = date.today().strftime("%A").lower()
    key = next((d for d in HOURS if d in day.lower()), today)
    return f"{key.capitalize()}: {HOURS[key]}. Closed on bank holidays."
