"""The concierge process: structure at the edges, freedom in the middle.

    identify -> guard_in -> agent -> guard_out -> assemble_facts -> impact_policy_gate
                   |                                                   |           |
                   +--(refused)----------------------------> release <-+  human_decision
                                                                ^                   |
                                                                +-- record_decision <+

Everything except the `agent` node is deterministic. The agent is a LangChain
`create_agent` subgraph with the pre-action gate as middleware (agent.py).
"""

from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.config import get_config
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from concierge import data
from concierge.agent import build_agent
from concierge.audit import decision_log
from concierge.context import Context
from concierge.gates import facts
from concierge.gates.impact_policy import classify
from concierge.guardrails.guard_in import Classifier, check_input, model_classifier
from concierge.guardrails.guard_out import sanitise
from concierge.human.decision import HELD_REPLY, read_decision, review_payload
from concierge.session import bind
from concierge.state import ConciergeInput, ConciergeOutput, ConciergeState
from concierge.tracing import configure_tracing, customer_ref, tag_trace

REFUSAL = (
    "I can't help with that request here. If you need support with your account, "
    "a member of staff at the counter can help."
)


def identify(state: ConciergeState, runtime: Runtime[Context]) -> dict:
    """Identification is the process's job: the customer comes from the session, not the chat."""
    messages = state["messages"]
    session = bind(state, runtime.context)
    tag_trace(
        test_id=session["test_id"], customer_ref=customer_ref(session["customer_id"]), session_id=session["session_id"]
    )
    request = next((m.text for m in reversed(messages) if isinstance(m, HumanMessage)), "")
    return {
        "session": session,
        "turn_id": uuid4().hex,
        "request": request,
        "turn_start": len(messages),
        "skills_run": [],
        "max_risk": "none",
        "reasons": [],
        "decision": {},
        "draft_reply": "",
        "reply": "",
        "outcome": "",
    }


def make_guard_in(classifier: Classifier | None):
    def guard_in(state: ConciergeState) -> dict:
        return {"guard_in": check_input(state["request"], classifier)}

    return guard_in


def after_guard_in(state: ConciergeState) -> str:
    return "agent" if state["guard_in"]["passed"] else "assemble_facts"


def guard_out(state: ConciergeState) -> dict:
    turn = state["messages"][state["turn_start"] :]
    reply, removed = sanitise(facts.final_reply(turn))
    return {"draft_reply": reply, "guard_out": removed}


def assemble_facts(state: ConciergeState) -> dict:
    if not state["guard_in"]["passed"]:
        return {"route": "refused", "reasons": [f"input guardrail: {state['guard_in']['reason']}"], "draft_reply": REFUSAL}
    turn = state["messages"][state["turn_start"] :]
    runs, max_risk = facts.skills_run(turn)
    customer = data.customer(state["session"]["customer_id"])
    why = facts.reasons(customer, state["request"], max_risk, state.get("draft_reply", ""))
    return {"skills_run": runs, "max_risk": max_risk, "reasons": why, "route": classify(True, why)}


def after_gate(state: ConciergeState) -> str:
    return "human_decision" if state["route"] == "review" else "release"


def human_decision(state: ConciergeState) -> dict:
    # Nothing with side effects happens before interrupt(): this node runs
    # again from the top when the decision owner resumes it.
    customer = data.customer(state["session"]["customer_id"])
    payload = review_payload(customer, state["request"], state["reasons"], state["skills_run"], state["draft_reply"])
    return {"decision": read_decision(interrupt(payload))}


def record_decision(state: ConciergeState) -> dict:
    d, session = state["decision"], state["session"]
    decision_log.record(
        {
            # The conversation's own thread, so the record points at the checkpoints.
            "thread_id": get_config()["configurable"]["thread_id"],
            "turn_id": state["turn_id"],
            "customer_id": session["customer_id"],
            "test_id": session["test_id"],
            "request": state["request"],
            "reasons": state["reasons"],
            "skills_run": state["skills_run"],
            "proposed_reply": state["draft_reply"],
            **{k: d.get(k) for k in ("decision", "approver", "note", "edited_reply", "decided_at")},
        }
    )
    return {}


def release(state: ConciergeState) -> dict:
    route, d = state["route"], state.get("decision") or {}
    if route == "refused":
        reply, outcome = REFUSAL, "refused"
    elif route == "straight_through":
        reply, outcome = state["draft_reply"], "straight_through"
    elif d.get("decision") == "approve":
        reply, outcome = d.get("edited_reply") or state["draft_reply"], "review_approved"
    else:
        reply, outcome = HELD_REPLY, "review_held"
    return {"reply": reply, "outcome": outcome, "messages": [AIMessage(content=reply, name="concierge")]}


def build_graph(model, classifier: Classifier | None = None, checkpointer=None):
    builder = StateGraph(
        ConciergeState, context_schema=Context, input_schema=ConciergeInput, output_schema=ConciergeOutput
    )
    builder.add_node("identify", identify)
    builder.add_node("guard_in", make_guard_in(classifier))
    builder.add_node("agent", build_agent(model))
    builder.add_node("guard_out", guard_out)
    builder.add_node("assemble_facts", assemble_facts)
    builder.add_node("human_decision", human_decision)
    builder.add_node("record_decision", record_decision)
    builder.add_node("release", release)

    builder.add_edge(START, "identify")
    builder.add_edge("identify", "guard_in")
    builder.add_conditional_edges("guard_in", after_guard_in, ["agent", "assemble_facts"])
    builder.add_edge("agent", "guard_out")
    builder.add_edge("guard_out", "assemble_facts")
    builder.add_conditional_edges(
        "assemble_facts", after_gate, {"human_decision": "human_decision", "release": "release"}
    )
    builder.add_edge("human_decision", "record_decision")
    builder.add_edge("record_decision", "release")
    builder.add_edge("release", END)
    return builder.compile(checkpointer=checkpointer, name="concierge")


def make_graph():
    """Entry point for `langgraph dev` and LangSmith Studio (see langgraph.json)."""
    from concierge.model import get_model

    configure_tracing()
    model = get_model()
    return build_graph(model, classifier=model_classifier(model))
