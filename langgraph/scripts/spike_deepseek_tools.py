"""Phase 1 spike: can DeepSeek flash (thinking off) run multi-turn tool calls
and return structured output through LangChain? Run with:

    uv run python scripts/spike_deepseek_tools.py
"""

from langchain.agents import create_agent
from langchain.tools import tool
from pydantic import BaseModel

from concierge.model import MODEL_NAME, get_model


@tool
def opening_hours(day: str) -> str:
    """Branch opening hours for a day of the week."""
    return {"saturday": "09:00 to 13:00", "sunday": "closed"}.get(day.lower(), "09:00 to 17:00")


@tool
def find_slots(adviser: str) -> str:
    """Free appointment slots for an adviser type, e.g. mortgage."""
    return f"{adviser} adviser: tomorrow 14:00, tomorrow 15:00, Friday 10:00"


class Summary(BaseModel):
    answered: bool
    tools_used: list[str]
    reply: str


def main() -> None:
    model = get_model()
    print(f"model: {MODEL_NAME}, thinking disabled")

    agent = create_agent(model, tools=[opening_hours, find_slots])
    thread = {"messages": [{"role": "user", "content": "When are you open on Saturday?"}]}
    first = agent.invoke(thread)
    thread["messages"] = first["messages"] + [
        {"role": "user", "content": "And can I see a mortgage adviser? Check both Saturday hours and slots."}
    ]
    second = agent.invoke(thread)
    calls = [c["name"] for m in second["messages"] if getattr(m, "tool_calls", None) for c in m.tool_calls]
    print("turn 1:", first["messages"][-1].content[:160])
    print("turn 2:", second["messages"][-1].content[:200])
    print("tool calls across both turns:", calls)

    structured = create_agent(model, tools=[opening_hours], response_format=Summary)
    out = structured.invoke({"messages": [{"role": "user", "content": "What are Saturday hours?"}]})
    print("structured:", out["structured_response"])


if __name__ == "__main__":
    main()
