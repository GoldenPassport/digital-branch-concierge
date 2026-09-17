"""Run one shared test conversation on the local LangGraph server (`langgraph dev`),
resuming any pauses, so the run appears in LangSmith Studio and in traces.

    uv run python scripts/run_on_server.py T06 [--hold] [--approver "Name"]
"""

import asyncio
import sys

from langgraph_sdk import get_client

from concierge.conversations import FOLLOW_UPS, cases


async def main(test_id: str, hold: bool, approver: str) -> None:
    case = next(r for r in cases() if r["test_id"] == test_id)
    client = get_client(url="http://127.0.0.1:2024")
    thread = await client.threads.create(metadata={"test_id": test_id})
    ctx = {"customer_id": case["customer_id"], "session_id": f"server-{test_id}", "test_id": test_id}
    tid = thread["thread_id"]

    async def send(message: str):
        await client.runs.wait(tid, "concierge", input={"messages": [{"role": "user", "content": message}]}, context=ctx)
        await resume_all()

    async def resume_all():
        for _ in range(5):
            state = await client.threads.get_state(tid)
            if not state["next"]:
                return
            value = state["tasks"][0]["interrupts"][0]["value"]
            if "action_requests" in value:
                resume = {"decisions": [{"type": "approve"}]}
            else:
                resume = {"decision": "hold" if hold else "approve", "approver": approver, "note": f"{test_id} run"}
            await client.runs.wait(tid, "concierge", command={"resume": resume}, context=ctx)

    await send(case["message"])
    state = await client.threads.get_state(tid)
    ran = [s["tool"] for s in state["values"].get("skills_run", [])]
    if test_id in FOLLOW_UPS and case["expected_skill"] and case["expected_skill"] not in ran:
        await send(FOLLOW_UPS[test_id])
        state = await client.threads.get_state(tid)
    v = state["values"]
    print(f"{test_id} thread={tid} route={v.get('route')} expected={case['expected_route']} outcome={v.get('outcome')}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    approver = sys.argv[sys.argv.index("--approver") + 1] if "--approver" in sys.argv else "Luke Audie"
    asyncio.run(main(args[0], "--hold" in sys.argv, approver))
