"""The agent: freedom in the middle, bounded on both sides.

A LangChain `create_agent` with the concierge's skills and read-only tools and
middleware for the pre-action gate:

1. `authorise` (wrap_tool_call) checks every proposed call against the
   registry and the identified customer before it runs. A refusal comes back
   as a ToolMessage the agent observes, carrying the skill's risk rating.
2. `HumanInTheLoopMiddleware` pauses before `update_contact_details` so a
   named decision owner can approve or reject it. Its `when` condition only
   asks for approval on calls that are authorised and have valid arguments,
   so a person is never asked to approve a call the gate would refuse.
3. Call limits stop runaway loops; model retries cover transient errors.
   Tools are not retried: a skill that writes must not run twice.
"""

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    ModelRequest,
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
    ToolCallRequest,
    dynamic_prompt,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage
from pydantic import ValidationError

from concierge import data
from concierge.context import Context
from concierge.gates.authorise import authorise
from concierge.prompts import load_system_prompt
from concierge.session import customer_id
from concierge.skills import SKILLS
from concierge.skills.result import refused
from concierge.state import ConciergeAgentState
from concierge.tools import TOOLS
from concierge.tracing import tag_trace

ALL_TOOLS = [*SKILLS, *TOOLS]
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}
MAX_MODEL_CALLS = 8  # matches the n8n agent's max iterations


@dynamic_prompt
def concierge_prompt(request: ModelRequest) -> str:
    template, source = load_system_prompt()
    tag_trace(prompt_source=source)
    customer = data.customer(customer_id(request))
    if customer is None:
        return template.format(name="an unidentified customer", customer_id="none", account_id="none")
    return template.format(name=customer.name, customer_id=customer.customer_id, account_id=customer.account_id)


def _check(request: ToolCallRequest):
    call = request.tool_call
    return authorise(call["name"], customer_id(request), call["args"].get("account_id"))


class AuthoriseToolCalls(AgentMiddleware):
    """Pre-action authorisation on every proposed call, sync and async.

    The LangGraph server (and Studio) run the graph asynchronously, so the
    async hook is required as well as the sync one.
    """

    @staticmethod
    def _refusal(request: ToolCallRequest) -> ToolMessage | None:
        auth = _check(request)
        if auth.authorised:
            return None
        call = request.tool_call
        return ToolMessage(
            content=refused(call["name"], auth.risk, auth.reason),
            tool_call_id=call["id"],
            name=call["name"],
            status="error",
        )

    def wrap_tool_call(self, request, handler):
        return self._refusal(request) or handler(request)

    async def awrap_tool_call(self, request, handler):
        return self._refusal(request) or await handler(request)


def needs_owner_approval(request: ToolCallRequest) -> bool:
    """Only pause for a person when the call would otherwise be allowed to run."""
    # The approval middleware runs before the tool node, so it passes no tool
    # object: look the tool up to validate its arguments.
    tool = TOOLS_BY_NAME.get(request.tool_call["name"])
    if tool is None or not _check(request).authorised:
        return False
    try:
        tool.args_schema.model_validate(request.tool_call["args"])
    except ValidationError:
        return False
    return True


def build_agent(model: BaseChatModel, checkpointer=None):
    return create_agent(
        model,
        tools=ALL_TOOLS,
        state_schema=ConciergeAgentState,
        context_schema=Context,
        middleware=[
            concierge_prompt,
            AuthoriseToolCalls(),
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "update_contact_details": {
                        "allowed_decisions": ["approve", "reject"],
                        "when": needs_owner_approval,
                        "description": "Pre-action approval: a medium-risk write to the customer's contact details.",
                    }
                },
            ),
            ModelCallLimitMiddleware(run_limit=MAX_MODEL_CALLS, exit_behavior="end"),
            ToolCallLimitMiddleware(run_limit=MAX_MODEL_CALLS, exit_behavior="continue"),
            ModelRetryMiddleware(max_retries=2),
        ],
        checkpointer=checkpointer,
        name="concierge_agent",
    )
