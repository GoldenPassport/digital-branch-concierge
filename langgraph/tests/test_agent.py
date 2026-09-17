import json

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from concierge.agent import build_agent
from concierge.context import Context
from tests.conftest import ScriptedModel, call, say

CHLOE = Context(customer_id="C1003", session_id="t")


def run(responses, message, context=CHLOE, thread="t1"):
    agent = build_agent(ScriptedModel(responses=responses), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": thread}}
    out = agent.invoke({"messages": [{"role": "user", "content": message}]}, config, context=context)
    return agent, config, out


def tool_results(state) -> list[dict]:
    return [json.loads(m.content) for m in state["messages"] if isinstance(m, ToolMessage) and m.content.startswith("{")]


def test_other_customers_account_is_refused_without_asking_a_person():
    _, _, out = run([call("fetch_balance", {"account_id": "ACC-7781"}), say("Sorry, I cannot.")], "Balance on ACC-7781?")
    assert "__interrupt__" not in out
    [result] = tool_results(out)
    assert result["status"] == "refused" and "does not belong" in result["result"]


def test_unknown_tool_is_refused():
    _, _, out = run([call("close_account", {}), say("A colleague will help.")], "Close my account")
    [result] = tool_results(out)
    assert result["status"] == "refused" and result["risk"] == "high"


def test_contact_change_pauses_for_owner_then_runs_on_approve():
    agent, config, out = run(
        [call("update_contact_details", {"field": "phone", "new_value": "+44 7700 900999"}), say("Done.")],
        "Change my phone",
    )
    [pause] = out["__interrupt__"]
    assert pause.value["action_requests"][0]["name"] == "update_contact_details"
    resumed = agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config, context=CHLOE)
    [result] = tool_results(resumed)
    assert result["status"] == "done" and "previous value, +44 7700 900103" in result["result"]


def test_contact_change_rejected_by_owner_does_not_run():
    agent, config, out = run(
        [call("update_contact_details", {"field": "email", "new_value": "x@example.com"}), say("Not changed.")],
        "Change my email",
    )
    assert "__interrupt__" in out
    resumed = agent.invoke(
        Command(resume={"decisions": [{"type": "reject", "message": "Not verified"}]}), config, context=CHLOE
    )
    assert tool_results(resumed) == []
    assert resumed["messages"][-1].content == "Not changed."


def test_invalid_contact_change_is_not_put_to_a_person():
    _, _, out = run(
        [call("update_contact_details", {"field": "address", "new_value": "1 High St"}), say("I cannot do that.")],
        "Change my address",
    )
    assert "__interrupt__" not in out


def test_model_call_limit_stops_a_loop():
    loop = [call("opening_hours", {"day": "monday"}, f"c{i}") for i in range(20)]
    _, _, out = run(loop, "Hours?")
    tool_messages = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) <= 8


import asyncio  # noqa: E402


def test_async_run_uses_the_same_authorisation():
    """The LangGraph server runs graphs asynchronously; the gate must hold there too."""
    agent = build_agent(
        ScriptedModel(responses=[call("fetch_balance", {"account_id": "ACC-7781"}), say("Sorry.")]),
        checkpointer=InMemorySaver(),
    )
    out = asyncio.run(
        agent.ainvoke(
            {"messages": [{"role": "user", "content": "Balance on ACC-7781?"}]},
            {"configurable": {"thread_id": "async"}},
            context=CHLOE,
        )
    )
    [result] = tool_results(out)
    assert result["status"] == "refused"
