"""The chat model used by the agent, the guardrail classifier and evaluations.

DeepSeek flash runs with thinking disabled. With thinking on, DeepSeek requires
every earlier `reasoning_content` to be sent back on requests that carry tools,
and returns HTTP 400 otherwise (api-docs.deepseek.com/guides/thinking_mode).
The concierge does not need extended reasoning, so the simplest governed
choice is to switch it off.
"""

import os

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

load_dotenv()

MODEL_NAME = os.getenv("CONCIERGE_MODEL", "deepseek-flash")


def get_model(temperature: float = 0.0) -> ChatDeepSeek:
    return ChatDeepSeek(
        model=MODEL_NAME,
        temperature=temperature,
        max_retries=2,
        extra_body={"thinking": {"type": "disabled"}},
    )
