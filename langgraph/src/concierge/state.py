"""Graph state: the contract every node reads from and writes to, and what the
checkpointer saves between turns and across a pause for a person."""

import operator
from typing import Annotated, Any, Literal, NotRequired, TypedDict

from langchain.agents import AgentState
from langgraph.graph.message import add_messages

from concierge.session import Session

Route = Literal["straight_through", "review", "refused"]


class ConciergeState(AgentState):
    messages: Annotated[list, add_messages]
    # Bound on the first turn from the run context; see session.py.
    session: NotRequired[Session]
    # Kept across turns: once a request names a policy area, later turns in the
    # conversation go to a person too.
    policy_seen: NotRequired[bool]
    # What the customer said and was told, masked. The only history returned to callers.
    transcript: NotRequired[Annotated[list[dict[str, str]], operator.add]]
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
    """What a caller gets back: the customer-facing conversation, the reply and how it was decided.

    The raw `messages` (model turns, tool calls and tool results, unmasked)
    stay in the checkpointed state for operators and are not returned here.
    """

    transcript: Annotated[list[dict[str, str]], operator.add]
    reply: str
    outcome: str
    route: Route
    reasons: list[str]
    skills_run: list[dict[str, str]]
    decision: dict[str, Any]
    guard_out: list[str]
