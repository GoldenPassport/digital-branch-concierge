"""Create (or update) the LangSmith dataset `concierge-12` from the shared test conversations.

    uv run python evals/create_dataset.py
"""

from dotenv import load_dotenv

load_dotenv()

from langsmith import Client  # noqa: E402

from concierge.conversations import cases  # noqa: E402

DATASET = "concierge-12"


def main() -> None:
    client = Client()
    if client.has_dataset(dataset_name=DATASET):
        dataset = client.read_dataset(dataset_name=DATASET)
        existing = {e.metadata.get("test_id") for e in client.list_examples(dataset_id=dataset.id)}
    else:
        dataset = client.create_dataset(
            DATASET,
            description=(
                "The twelve shared test conversations for the digital branch concierge, "
                "v2 (T03 and T04 corrected after review; n8n used v1). Demo customers only."
            ),
        )
        existing = set()
    new = [c for c in cases() if c["test_id"] not in existing]
    if new:
        client.create_examples(
            dataset_id=dataset.id,
            examples=[
                {
                    "inputs": {"test_id": c["test_id"], "customer_id": c["customer_id"], "message": c["message"]},
                    "outputs": {"expected_route": c["expected_route"], "expected_skill": c["expected_skill"] or None},
                    "metadata": {"test_id": c["test_id"], "note": c["note"]},
                }
                for c in new
            ],
        )
    print(f"{DATASET}: {len(existing) + len(new)} examples ({len(new)} added)")


if __name__ == "__main__":
    main()
