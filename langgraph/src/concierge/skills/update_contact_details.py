"""Update contact details: the one medium-risk write, behind pre-action approval.

Simulated for the demo: it returns a confirmation but does not change the
customer record, so the build tests authorisation and the pause, not
persistence or reversal. The new value is validated before a person is asked
to approve it.
"""

import re
from typing import Literal, Self

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field, model_validator

from concierge import data
from concierge.context import Context
from concierge.gates.authorise import authorise
from concierge.session import customer_id
from concierge.skills.result import done, refused

NAME = "update_contact_details"
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE = re.compile(r"^\+?[0-9][0-9 ()-]{6,19}$")


class UpdateContactDetailsInput(BaseModel):
    field: Literal["phone", "email"] = Field(description="Which field to change: phone or email")
    new_value: str = Field(description="The new value: a phone number such as +44 7700 900999, or an email address")

    @model_validator(mode="after")
    def check_value(self) -> Self:
        self.new_value = self.new_value.strip()
        pattern = PHONE if self.field == "phone" else EMAIL
        digits = sum(ch.isdigit() for ch in self.new_value)
        if not pattern.match(self.new_value) or (self.field == "phone" and digits < 7):
            raise ValueError(f"{self.new_value!r} is not a valid {self.field}. Ask the customer to check it.")
        return self


@tool(NAME, args_schema=UpdateContactDetailsInput)
def update_contact_details(field: str, new_value: str, runtime: ToolRuntime[Context]) -> str:
    """Update the customer's phone or email. Risk: medium, writes data. A named decision owner
    approves before it runs, so tell the customer it may take a moment.
    Demo build: the change is simulated and no record is stored.
    Returns a confirmation, a declined notice, or a refusal."""
    auth = authorise(NAME, customer_id(runtime))
    if not auth.authorised:
        return refused(NAME, auth.risk, auth.reason)
    customer = data.customer(customer_id(runtime))
    previous = getattr(customer, field)
    return done(
        NAME,
        auth.risk,
        f"Updated {field} for {customer.name} to {new_value} (demo: simulated, no record stored). "
        f"In a live system the previous value, {previous}, would be kept for 30 days so the change could be reversed.",
    )
