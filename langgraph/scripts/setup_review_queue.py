"""Create the learning-loop review queue in LangSmith: "Concierge review".

    uv run python scripts/setup_review_queue.py

Two LangSmith rules (set up in the UI) send traces whose output `outcome`
contains `review_held` or `refused` into this queue. A reviewer scores each case against the
rubric and writes any improvement as a proposal. Proposals change nothing on
their own: a corrected case is added to the `concierge-12` dataset, and a
change to a skill, tool, knowledge or the prompt is only promoted after its
experiment passes. The agent never changes itself.
"""

from dotenv import load_dotenv

load_dotenv()

from langsmith import Client  # noqa: E402

QUEUE = "Concierge review"

CONFIGS = {
    "routing_correct": {
        "config": {"type": "continuous", "min": 0, "max": 1},
        "item": {
            "description": "Was it right to send this conversation to a person, or to refuse it? 1 yes, 0 no.",
            "score_descriptions": {"0": "Wrong route", "1": "Right route"},
            "is_required": True,
        },
    },
    "reply_within_policy": {
        "config": {"type": "continuous", "min": 0, "max": 1},
        "item": {
            "description": "Does the reply avoid promising an outcome the concierge must never decide "
            "(lending, complaints, closures, vulnerability)? 1 yes, 0 no.",
            "score_descriptions": {"0": "Promises or decides", "1": "Within policy"},
            "is_required": True,
        },
    },
    "improvement": {
        "config": {"type": "categorical", "categories": [
            {"value": 0, "label": "none"},
            {"value": 1, "label": "knowledge gap"},
            {"value": 2, "label": "skill or tool"},
            {"value": 3, "label": "prompt"},
            {"value": 4, "label": "gate rule (policy owner only)"},
        ]},
        "item": {
            "description": "Is there an improvement to propose? Pick the area and explain in the comment. "
            "Proposals are reviewed and evaluated before anything changes.",
            "is_required": False,
        },
    },
}

INSTRUCTIONS = (
    "You are the reviewer for the concierge's learning loop. Read the conversation, the gate's route "
    "and reasons, and the final reply. Score the rubric. If something should improve, choose the area "
    "and describe the proposal in the comment. If the case is a good test, add it to the concierge-12 "
    "dataset with the corrected expected outcome. Nothing you propose changes the concierge until it "
    "has passed an experiment and been promoted."
)


def main() -> None:
    client = Client()
    existing = {c.feedback_key for c in client.list_feedback_configs()}
    for key, spec in CONFIGS.items():
        if key not in existing:
            client.create_feedback_config(key, feedback_config=spec["config"])
    items = [{"feedback_key": key, **spec["item"]} for key, spec in CONFIGS.items()]
    queues = list(client.list_annotation_queues(name=QUEUE))
    if queues:
        client.update_annotation_queue(queues[0].id, rubric_instructions=INSTRUCTIONS, rubric_items=items)
        print(f"updated {QUEUE}: {queues[0].id}")
    else:
        q = client.create_annotation_queue(
            name=QUEUE,
            description="Learning loop: concierge conversations routed to review or refused.",
            rubric_instructions=INSTRUCTIONS,
            rubric_items=items,
        )
        print(f"created {QUEUE}: {q.id}")


if __name__ == "__main__":
    main()
