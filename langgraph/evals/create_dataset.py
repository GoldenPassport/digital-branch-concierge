"""Create or update the LangSmith dataset `concierge-12` from the shared test conversations.

New conversations are added, and changed ones (such as a corrected expected
skill) are updated in place.

    uv run python evals/create_dataset.py
"""

from dotenv import load_dotenv

load_dotenv()

from langsmith import Client  # noqa: E402

from concierge.conversations import cases  # noqa: E402

DATASET = "concierge-12"


def example(case: dict) -> dict:
    return {
        "inputs": {"test_id": case["test_id"], "customer_id": case["customer_id"], "message": case["message"]},
        "outputs": {"expected_route": case["expected_route"], "expected_skill": case["expected_skill"] or None},
        "metadata": {"test_id": case["test_id"], "note": case["note"]},
    }


def main() -> None:
    client = Client()
    if client.has_dataset(dataset_name=DATASET):
        dataset = client.read_dataset(dataset_name=DATASET)
    else:
        dataset = client.create_dataset(
            DATASET,
            description=(
                "The twelve shared test conversations for the digital branch concierge, "
                "v2 (T03 and T04 corrected after review; n8n used v1). Demo customers only."
            ),
        )
    existing = {e.metadata.get("test_id"): e for e in client.list_examples(dataset_id=dataset.id)}
    added, updated = [], []
    for case in cases():
        want = example(case)
        have = existing.get(case["test_id"])
        if have is None:
            added.append(want)
        else:
            # Keep metadata added in LangSmith, such as a note that a case was corrected.
            metadata = {**(have.metadata or {}), **want["metadata"]}
            if (have.inputs, have.outputs, have.metadata) != (want["inputs"], want["outputs"], metadata):
                # LangSmith versions the dataset on every change, so earlier
                # experiments still point at the examples they ran against.
                client.update_example(have.id, inputs=want["inputs"], outputs=want["outputs"], metadata=metadata)
                updated.append(case["test_id"])
    if added:
        client.create_examples(dataset_id=dataset.id, examples=added)
    print(f"{DATASET}: {len(existing) + len(added)} examples ({len(added)} added, {len(updated)} updated {updated})")


if __name__ == "__main__":
    main()
