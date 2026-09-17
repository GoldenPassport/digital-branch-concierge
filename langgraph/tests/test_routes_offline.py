"""All twelve shared test conversations, run through the whole process with a
scripted model: no network, no API keys. The model's moves are scripted; the
process, both gates, the guardrails and the human decision are real.
"""

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from concierge.audit import decision_log
from concierge.context import Context
from concierge.conversations import cases
from concierge.graph import build_graph
from concierge.registry import REGISTRY
from tests.conftest import ScriptedModel, call, say

CASES = {r["test_id"]: r for r in cases()}

SCRIPTS = {
    "T01": [call("print_statement", {"account_id": "ACC-7783", "period_months": 3}), say("Your statement is ready.")],
    "T02": [call("opening_hours", {"day": "saturday"}), say("We are open 09:00 to 13:00 on Saturday.")],
    "T03": [call("knowledge", {"query": "mortgage what to bring"}), say("Bring proof of income. Shall I book an adviser?")],
    "T04": [call("find_slots", {"appointment_type": "mortgage adviser"}), say("I have 14:00 and 15:30. Which suits you?")],
    "T05": [call("fetch_balance", {"account_id": "ACC-7783"}), say("Your balance is £15,980.75.")],
    "T06": [call("update_contact_details", {"field": "phone", "new_value": "+44 7700 900999"}), say("Your phone number is updated.")],
    "T07": [say("I cannot see the outcome of your complaint. A colleague will update you.")],
    "T08": [say("A member of staff will help you close your account.")],
    "T09": [say("I cannot decide on overdrafts. A colleague will pick this up.")],
    "T10": [call("update_contact_details", {"field": "email", "new_value": "ben.new@example.com"}), say("Email updated.")],
    "T11": [],
    "T12": [call("fetch_balance", {"account_id": "ACC-7781"}), say("I can only help with your own account.")],
}


@pytest.fixture(autouse=True)
def decisions_db(tmp_path, monkeypatch):
    monkeypatch.setenv("CONCIERGE_DECISIONS_DB", str(tmp_path / "decisions.sqlite"))


def run_case(test_id: str, owner_decision: dict | None = None):
    case = CASES[test_id]
    graph = build_graph(ScriptedModel(responses=SCRIPTS[test_id]), classifier=None, checkpointer=InMemorySaver())
    context = Context(customer_id=case["customer_id"], session_id=test_id, test_id=test_id)
    config = {"configurable": {"thread_id": f"{case['customer_id']}:{test_id}"}}
    out = graph.invoke({"messages": [{"role": "user", "content": case["message"]}]}, config, context=context)
    pauses = []
    while "__interrupt__" in out:
        value = out["__interrupt__"][0].value
        pauses.append("pre_action_approval" if "action_requests" in value else "human_decision")
        resume = {"decisions": [{"type": "approve"}]} if "action_requests" in value else owner_decision
        out = graph.invoke(Command(resume=resume), config, context=context)
    return out, pauses


APPROVE = {"decision": "approve", "approver": "Test Owner"}


@pytest.mark.parametrize("test_id", sorted(CASES))
def test_expected_route_and_skill(test_id):
    out, _ = run_case(test_id, APPROVE)
    case = CASES[test_id]
    assert out["route"] == case["expected_route"], out.get("reasons")
    done = [s["tool"] for s in out["skills_run"] if s["status"] == "done"]
    if case["expected_skill"]:
        assert case["expected_skill"] in done
    # No skill beyond the expected one completed; read-only tools may run.
    skills = {name for name, c in REGISTRY.items() if c.kind == "skill"}
    assert set(done) & skills <= {case["expected_skill"]}


def test_t06_pauses_twice_approval_then_review():
    out, pauses = run_case("T06", APPROVE)
    assert pauses == ["pre_action_approval", "human_decision"]
    assert out["reasons"] == ["skill risk medium"]
    assert out["outcome"] == "review_approved"


def test_t09_held_by_owner_gets_holding_reply_and_a_record():
    out, _ = run_case("T09", {"decision": "hold", "approver": "Test Owner", "note": "Lending team"})
    assert out["outcome"] == "review_held"
    assert out["reply"].startswith("Thank you. A member of staff")
    [row] = decision_log.rows()
    assert row["decision"] == "hold" and row["approver"] == "Test Owner" and row["test_id"] == "T09"


def test_invalid_owner_decision_fails_safe_to_hold():
    out, _ = run_case("T08", {"decision": "yes please"})
    assert out["outcome"] == "review_held"
    assert out["decision"]["valid"] is False


def test_owner_can_change_the_reply():
    out, _ = run_case("T07", {**APPROVE, "edited_reply": "Your complaint handler will call you tomorrow."})
    assert out["reply"] == "Your complaint handler will call you tomorrow."


def test_t11_never_reaches_the_agent():
    out, pauses = run_case("T11")
    assert out["outcome"] == "refused" and pauses == []
    assert out["reasons"][0].startswith("input guardrail")


def test_resume_without_context_keeps_the_identified_customer():
    """Studio resumes a pause without the run context. The customer identified at
    the start of the conversation must still own the write and the decision record."""
    case = CASES["T10"]  # Ben Whitfield, C1002: not the default customer
    graph = build_graph(ScriptedModel(responses=SCRIPTS["T10"]), classifier=None, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "studio-thread-1"}}
    context = Context(customer_id=case["customer_id"], session_id="T10", test_id="T10")
    out = graph.invoke({"messages": [{"role": "user", "content": case["message"]}]}, config, context=context)
    while "__interrupt__" in out:
        value = out["__interrupt__"][0].value
        resume = {"decisions": [{"type": "approve"}]} if "action_requests" in value else APPROVE
        out = graph.invoke(Command(resume=resume), config)  # no context, as Studio sends it
    assert out["outcome"] == "review_approved"
    [update] = [s for s in out["skills_run"] if s["tool"] == "update_contact_details"]
    assert update["status"] == "done"
    messages = graph.get_state(config).values["messages"]
    written = next(m.content for m in messages if getattr(m, "name", None) == "update_contact_details")
    assert "Ben Whitfield" in written
    [row] = decision_log.rows()
    assert row["customer_id"] == "C1002" and row["test_id"] == "T10"
    assert row["thread_id"] == "studio-thread-1"


def run_turns(responses: list, turns: list[str], customer_id: str = "C1003", decision: dict | None = None):
    """Several customer turns on one thread, answering every pause."""
    graph = build_graph(ScriptedModel(responses=responses), classifier=None, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": f"multi-{customer_id}"}}
    context = Context(customer_id=customer_id, session_id="multi")
    outs = []
    for message in turns:
        out = graph.invoke({"messages": [{"role": "user", "content": message}]}, config, context=context)
        while "__interrupt__" in out:
            value = out["__interrupt__"][0].value
            resume = {"decisions": [{"type": "approve"}]} if "action_requests" in value else decision or APPROVE
            out = graph.invoke(Command(resume=resume), config, context=context)
        outs.append(out)
    return outs


def test_policy_intent_carries_to_the_next_turn():
    first, second = run_turns(
        [say("A colleague will help you close your account."), say("Understood, a colleague is taking this on.")],
        ["I want to close my account.", "Yes, please do that."],
    )
    assert first["route"] == "review"
    assert second["route"] == "review"
    assert "policy request earlier in this conversation" in second["reasons"]


def test_a_reply_claiming_a_consequential_outcome_goes_to_a_person():
    [out] = run_turns([say("Done. Your account is now closed.")], ["Thanks for your help today."])
    assert out["route"] == "review"
    assert "outcome claim in reply" in out["reasons"]


def test_an_edited_reply_is_masked_before_release():
    out, _ = run_case("T07", {**APPROVE, "edited_reply": "Your card 4111 1111 1111 1111 is fine."})
    assert "4111" not in out["reply"]
    assert "card number" in out["guard_out"]


def test_callers_get_a_masked_transcript_not_the_raw_messages():
    [out] = run_turns([say("Your card 4111 1111 1111 1111 is active.")], ["Is my card 4111 1111 1111 1111 active?"])
    assert "messages" not in out
    assert out["transcript"] == [
        {"role": "customer", "content": "Is my card [card number removed] active?"},
        {"role": "concierge", "content": "Your card [card number removed] is active."},
    ]


def test_a_rejected_write_still_goes_to_review():
    graph = build_graph(
        ScriptedModel(responses=[call("update_contact_details", {"field": "phone", "new_value": "+44 7700 900999"}),
                                 say("That change was not approved.")]),
        classifier=None,
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "reject"}}
    out = graph.invoke({"messages": [{"role": "user", "content": "Change my phone"}]}, config, context=Context())
    out = graph.invoke(Command(resume={"decisions": [{"type": "reject", "message": "Not verified"}]}), config)
    [run] = out["skills_run"]
    assert run["status"] == "not run" and out["route"] == "review"
