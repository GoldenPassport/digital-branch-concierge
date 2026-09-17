"""Run context: trusted values set by the process, never chosen by the model.

LangGraph passes this to the run. `identify` binds the customer to the
conversation on the first turn (session.py), so skills know who the identified
customer is without the model supplying it, and a resume cannot change it.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Context:
    # In a real branch this comes from the identity check at the counter. The
    # demo defaults to Chloe Martin (C1003), as the n8n build does; set
    # customer_id in the run context to switch customer.
    customer_id: str = "C1003"
    session_id: str = "demo"
    test_id: str | None = None
