from datetime import date
from uuid import uuid4

from dateutil.relativedelta import relativedelta
from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from concierge.context import Context
from concierge.gates.authorise import authorise
from concierge.session import customer_id
from concierge.skills.result import done, refused

NAME = "print_statement"


class PrintStatementInput(BaseModel):
    account_id: str = Field(description="The account id of the identified customer, e.g. ACC-7783")
    period_months: int = Field(default=3, ge=1, le=24, description="How many months the statement should cover")


@tool(NAME, args_schema=PrintStatementInput)
def print_statement(account_id: str, period_months: int, runtime: ToolRuntime[Context]) -> str:
    """Print a statement for the customer's own account. Risk: low, read only.
    Returns a confirmation with a reference, or a refusal."""
    auth = authorise(NAME, customer_id(runtime), account_id)
    if not auth.authorised:
        return refused(NAME, auth.risk, auth.reason)
    end = date.today()
    start = end - relativedelta(months=period_months)
    return done(
        NAME,
        auth.risk,
        f"Statement printed for {account_id} covering {start} to {end} ({period_months} months). "
        f"Stamped copy handed to the customer at the concierge desk. Reference STM-{uuid4().hex[:6].upper()}.",
    )
