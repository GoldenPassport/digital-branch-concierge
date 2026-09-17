"""Book an appointment: a low-risk, reversible action.

Simulated for the demo: it returns a reference but does not store a booking.
"""

from uuid import uuid4

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from concierge.context import Context
from concierge.gates.authorise import authorise
from concierge.session import customer_id
from concierge.skills.result import done, refused

NAME = "book_appointment"


class BookAppointmentInput(BaseModel):
    appointment_type: str = Field(description="What the appointment is for, e.g. mortgage adviser")
    preferred_time: str | None = Field(default=None, description="The slot the customer chose, if any")


@tool(NAME, args_schema=BookAppointmentInput)
def book_appointment(appointment_type: str, preferred_time: str | None, runtime: ToolRuntime[Context]) -> str:
    """Book a 45-minute branch appointment. Risk: low, reversible.
    Demo build: the booking is simulated and nothing is stored.
    Returns a confirmation with a reference, or a refusal."""
    auth = authorise(NAME, customer_id(runtime))
    if not auth.authorised:
        return refused(NAME, auth.risk, auth.reason)
    when = preferred_time or "next available slot"
    return done(
        NAME,
        auth.risk,
        f"Booked: {appointment_type} appointment, {when}, 45 minutes. Reference APT-{uuid4().hex[:6].upper()} "
        "(demo: simulated, nothing stored). The customer can cancel or move it at any time.",
    )
