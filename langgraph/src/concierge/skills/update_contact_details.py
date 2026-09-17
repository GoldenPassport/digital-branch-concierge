from typing import Literal

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from concierge import data
from concierge.context import Context
from concierge.gates.authorise import authorise
from concierge.session import customer_id
from concierge.skills.result import done, refused

NAME = "update_contact_details"


class UpdateContactDetailsInput(BaseModel):
    field: Literal["phone", "email"] = Field(description="Which field to change: phone or email")
    new_value: str = Field(description="The new value")


@tool(NAME, args_schema=UpdateContactDetailsInput)
def update_contact_details(field: str, new_value: str, runtime: ToolRuntime[Context]) -> str:
    """Update the customer's phone or email. Risk: medium, writes data. A named decision owner
    approves before it runs, so tell the customer it may take a moment.
    Returns a confirmation, a declined notice, or a refusal."""
    auth = authorise(NAME, customer_id(runtime))
    if not auth.authorised:
        return refused(NAME, auth.risk, auth.reason)
    customer = data.customer(customer_id(runtime))
    previous = getattr(customer, field)
    return done(
        NAME,
        auth.risk,
        f"Updated {field} for {customer.name} to {new_value}. "
        f"Previous value {previous} retained for 30 days so the change can be reversed.",
    )
