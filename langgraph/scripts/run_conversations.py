"""Run the shared test conversations against the live model, end to end, locally.

A quick behavioural check (the LangSmith experiment is the evaluation):

    uv run python scripts/run_conversations.py            # all twelve
    uv run python scripts/run_conversations.py T06 T09    # selected
    uv run python scripts/run_conversations.py T09 --hold
"""

import sys

from langgraph.checkpoint.memory import InMemorySaver

from concierge.conversations import cases, run_case
from concierge.graph import build_graph
from concierge.guardrails.guard_in import model_classifier
from concierge.model import get_model
from concierge.tracing import configure_tracing


def main(selected: list[str], hold: bool) -> None:
    configure_tracing()
    model = get_model()
    graph = build_graph(model, classifier=model_classifier(model), checkpointer=InMemorySaver())
    rows = [c for c in cases() if not selected or c["test_id"] in selected]
    passed = 0
    for case in rows:
        r = run_case(graph, case, hold=hold)
        s = r.state
        ok = s["route"] == case["expected_route"]
        passed += ok
        tools = [t["tool"] + ("(refused)" if t["status"] == "refused" else "") for t in s.get("skills_run", [])]
        print(
            f"{case['test_id']} {'PASS' if ok else 'MISS'} turns={r.turns} route={s['route']} "
            f"expected={case['expected_route']} outcome={s['outcome']} tools={tools} pauses={r.pauses} "
            f"reasons={s.get('reasons')} {r.seconds:.1f}s"
        )
    print(f"\n{passed}/{len(rows)} routes as expected")


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")], hold="--hold" in sys.argv)
