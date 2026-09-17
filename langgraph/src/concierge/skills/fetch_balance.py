from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from concierge import data
from concierge.context import Context
from concierge.gates.authorise import authorise
from concierge.session import customer_id
from concierge.skills.result import done, refused

NAME = "fetch_balance"


class FetchBalanceInput(BaseModel):
    account_id: str = Field(description="The account id of the identified customer, e.g. ACC-7783")


@tool(NAME, args_schema=FetchBalanceInput)
def fetch_balance(account_id: str, runtime: ToolRuntime[Context]) -> str:
    """Fetch the available balance on the customer's own account. Risk: low, read only.
    Returns the balance, or a refusal."""
    auth = authorise(NAME, customer_id(runtime), account_id)
    if not auth.authorised:
        return refused(NAME, auth.risk, auth.reason)
    balance = data.account_owner(account_id).balance
    sign = "-" if balance < 0 else ""
    return done(NAME, auth.risk, f"Available balance on {account_id}: {sign}£{abs(balance):,.2f}.")
