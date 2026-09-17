"""The identified customer, bound to the conversation.

The run context says who the customer is when a conversation starts. `identify`
copies it into graph state on the first turn, and from then on every node,
middleware and skill reads the customer from state. A later turn or a resumed
pause (Studio sends no run context on resume) can never switch the customer
or fall back to the demo default.
"""

from typing import Any, TypedDict

from concierge.context import Context


class Session(TypedDict):
    customer_id: str
    session_id: str
    test_id: str | None


def bind(state: dict[str, Any], context: Context | None) -> Session:
    """The session already bound to this conversation, or a new one from the context."""
    if state.get("session"):
        return state["session"]
    ctx = context or Context()
    return {"customer_id": ctx.customer_id, "session_id": ctx.session_id, "test_id": ctx.test_id}


def customer_id(runtime: Any) -> str:
    """The bound customer for a node, middleware request or tool runtime."""
    return bind(getattr(runtime, "state", None) or {}, getattr(runtime, "context", None))["customer_id"]
