from datetime import date, timedelta

from langchain.tools import tool


@tool
def find_slots(appointment_type: str = "general") -> str:
    """Read-only lookup of the next available appointment slots. Input: the appointment type,
    e.g. 'mortgage adviser'. Returns up to three slots as text. Booking is a separate skill."""
    tomorrow = date.today() + timedelta(days=1)
    day_after = tomorrow + timedelta(days=1)
    return (
        f"Next {appointment_type} slots: {tomorrow} 14:00, {tomorrow} 15:30, {day_after} 10:00. "
        "Each slot is 45 minutes."
    )
