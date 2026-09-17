"""Graph state: the contract every node reads from and writes to, and what the
checkpointer saves between turns and across a pause for a person."""

from typing import Annotated, Any, Literal, NotRequired, TypedDict

from langchain.agents import AgentState
from langgraph.graph.message import add_messages

from concierge.session import Session

Route = Literal["straight_through", "review", "refused"]


class ConciergeState(AgentState):
    messages: Annotated[list, add_messages]
    # Bound on the first turn from the run context; see session.py.
    session: NotRequired[Session]
    # Set per turn by the process, never by the model.
    turn_id: NotRequired[str]
    request: NotRequired[str]
    turn_start: NotRequired[int]
    guard_in: NotRequired[dict[str, Any]]
    skills_run: NotRequired[list[dict[str, str]]]
    max_risk: NotRequired[str]
    reasons: NotRequired[list[str]]
    route: NotRequired[Route]
    draft_reply: NotRequired[str]
    guard_out: NotRequired[list[str]]
    decision: NotRequired[dict[str, Any]]
    reply: NotRequired[str]
    outcome: NotRequired[str]


class ConciergeAgentState(AgentState):
    """The agent sees the bound session so its gate and skills act for the right customer."""

    session: NotRequired[Session]


class ConciergeInput(TypedDict):
    """What a caller sends: the customer's message. Everything else is the process's."""

    messages: Annotated[list, add_messages]


class ConciergeOutput(TypedDict):
    """What a caller gets back: the conversation, the reply and how it was decided."""

    messages: Annotated[list, add_messages]
    reply: str
    outcome: str
    route: Route
    reasons: list[str]
    skills_run: list[dict[str, str]]
    decision: dict[str, Any]
