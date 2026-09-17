import json
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def local_prompt(monkeypatch):
    """Offline tests use the prompt in the repository, never LangSmith."""
    monkeypatch.setenv("CONCIERGE_PROMPT_SOURCE", "local")

from concierge.context import Context


@pytest.fixture
def runtime():
    """A stand-in for ToolRuntime: skills only read runtime.context."""

    def make(customer_id: str | None = "C1003") -> SimpleNamespace:
        return SimpleNamespace(context=Context(customer_id=customer_id))

    return make


def result(raw: str) -> dict:
    return json.loads(raw)


from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402


class ScriptedModel(FakeMessagesListChatModel):
    """A fake chat model that replays scripted AI messages and accepts bound tools."""

    def bind_tools(self, tools, **kwargs):
        return self


def call(name: str, args: dict, call_id: str = "call-1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


def say(text: str) -> AIMessage:
    return AIMessage(content=text)
