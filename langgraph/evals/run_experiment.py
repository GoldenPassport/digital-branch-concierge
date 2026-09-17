"""Run the concierge over `concierge-12` in LangSmith and score it.

    uv run python evals/run_experiment.py --prefix baseline

Evaluators are plain code, no model-as-judge:
- route_correct: the gate took the expected route (the n8n metric)
- gate_triggered: a person was asked exactly when the expected route is review
- skill_correct: the expected skill or read-only tool ran (and was not refused), when one is expected
"""

import argparse

from dotenv import load_dotenv

load_dotenv()

from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langsmith import Client  # noqa: E402

from concierge.conversations import cases, run_case  # noqa: E402
from concierge.graph import build_graph  # noqa: E402
from concierge.guardrails.guard_in import model_classifier  # noqa: E402
from concierge.model import MODEL_NAME, get_model  # noqa: E402
from concierge.prompts import load_system_prompt  # noqa: E402
from concierge.tracing import configure_tracing  # noqa: E402

configure_tracing()
_model = get_model()
_graph = build_graph(_model, classifier=model_classifier(_model), checkpointer=InMemorySaver())


EXPECTED_SKILL = {c["test_id"]: c["expected_skill"] for c in cases()}


def target(inputs: dict) -> dict:
    # The follow-up rule needs the expected skill, which is a reference output,
    # so it is looked up from the shared set rather than passed to the target.
    case = {**inputs, "expected_skill": EXPECTED_SKILL[inputs["test_id"]]}
    r = run_case(_graph, case, session="experiment")
    s = r.state
    return {
        "route": s["route"],
        "outcome": s["outcome"],
        "reply": s["reply"],
        "skills_run": [t["tool"] for t in s.get("skills_run", []) if t["status"] == "done"],
        "pauses": r.pauses,
        "turns": r.turns,
    }


def route_correct(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "route_correct", "score": int(outputs["route"] == reference_outputs["expected_route"])}


def gate_triggered(outputs: dict, reference_outputs: dict) -> dict:
    asked = "human_decision" in outputs["pauses"]
    return {"key": "gate_triggered", "score": int(asked == (reference_outputs["expected_route"] == "review"))}


def skill_correct(outputs: dict, reference_outputs: dict) -> dict:
    expected = reference_outputs.get("expected_skill")
    if not expected:
        return {"key": "skill_correct", "score": None, "comment": "no skill expected"}
    return {"key": "skill_correct", "score": int(expected in outputs["skills_run"])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="baseline")
    parser.add_argument("--description", default="")
    args = parser.parse_args()
    results = Client().evaluate(
        target,
        data="concierge-12",
        evaluators=[route_correct, gate_triggered, skill_correct],
        experiment_prefix=args.prefix,
        description=args.description or f"Concierge on {MODEL_NAME}, thinking off",
        metadata={"model": MODEL_NAME, "thinking": "disabled", "prompt": load_system_prompt()[1]},
        max_concurrency=1,
    )
    print(results)


if __name__ == "__main__":
    main()
