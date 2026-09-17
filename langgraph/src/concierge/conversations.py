"""The shared test conversations and one way to run them, used by the local
scripts and by the LangSmith evaluation so both behave identically.

Pauses are answered by a scripted decision owner: approve at pre-action
approval, and approve (or hold) at the human decision. Two conversations
need the customer's second message, because the agent rightly confirms or
asks for a detail before writing.
"""

import csv
import time
from dataclasses import dataclass, field

from langgraph.types import Command

from concierge import data
from concierge.context import Context

FOLLOW_UPS = {
    "T06": "Yes, that's right, please go ahead.",
    "T10": "ben.whitfield.new@example.com please.",
}


def cases() -> list[dict]:
    with open(data.TEST_CONVERSATIONS, newline="") as f:
        return list(csv.DictReader(f))


@dataclass
class Result:
    state: dict
    pauses: list[str] = field(default_factory=list)
    turns: int = 1
    seconds: float = 0.0


def run_case(graph, case: dict, *, hold: bool = False, approver: str = "Scripted decision owner", session: str = "local") -> Result:
    tid = case["test_id"]
    context = Context(customer_id=case["customer_id"], session_id=f"{session}-{tid}", test_id=tid)
    config = {"configurable": {"thread_id": f"{case['customer_id']}:{session}-{tid}"}}
    result = Result(state={})
    started = time.perf_counter()

    def resume_all(out):
        while "__interrupt__" in out:
            value = out["__interrupt__"][0].value
            if "action_requests" in value:
                result.pauses.append("pre_action_approval")
                resume = {"decisions": [{"type": "approve"}]}
            else:
                result.pauses.append("human_decision")
                resume = {"decision": "hold" if hold else "approve", "approver": approver, "note": f"{tid} scripted"}
            out = graph.invoke(Command(resume=resume), config, context=context)
        return out

    out = resume_all(graph.invoke({"messages": [{"role": "user", "content": case["message"]}]}, config, context=context))
    ran = [s["tool"] for s in out.get("skills_run", [])]
    if tid in FOLLOW_UPS and case["expected_skill"] and case["expected_skill"] not in ran:
        result.turns = 2
        out = resume_all(graph.invoke({"messages": [{"role": "user", "content": FOLLOW_UPS[tid]}]}, config, context=context))
    result.state = out
    result.seconds = time.perf_counter() - started
    return result
