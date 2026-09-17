"""All twelve shared test conversations, run through the whole process with a
scripted model: no network, no API keys. The model's moves are scripted; the
process, both gates, the guardrails and the human decision are real.
"""

import csv

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from concierge import data
from concierge.audit import decision_log
from concierge.context import Context
from concierge.graph import build_graph
from tests.conftest import ScriptedModel, call, say

CASES = {r["test_id"]: r for r in csv.DictReader(open(data.TEST_CONVERSATIONS))}

SCRIPTS = {
    "T01": [call("print_statement", {"account_id": "ACC-7783", "period_months": 3}), say("Your statement is ready.")],
    "T02": [call("opening_hours", {"day": "saturday"}), say("We are open 09:00 to 13:00 on Saturday.")],
    "T03": [call("knowledge", {"query": "mortgage what to bring"}), say("Bring proof of income. Shall I book an adviser?")],
    "T04": [call("book_appointment", {"appointment_type": "mortgage adviser", "preferred_time": "tomorrow 14:00"}), say("Booked.")],
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
def test_expected_route(test_id):
    out, _ = run_case(test_id, APPROVE)
    assert out["route"] == CASES[test_id]["expected_route"], out.get("reasons")


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
    written = next(m.content for m in out["messages"] if getattr(m, "name", None) == "update_contact_details")
    assert "Ben Whitfield" in written
    [row] = decision_log.rows()
    assert row["customer_id"] == "C1002" and row["test_id"] == "T10"
    assert row["thread_id"] == "studio-thread-1"
