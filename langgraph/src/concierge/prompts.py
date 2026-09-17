"""The concierge system prompt, ported word for word from the n8n build.

`{name}`, `{customer_id}` and `{account_id}` are filled from the identified
customer at run time, never from the conversation.

Change management: the prompt is versioned in LangSmith Prompts as
`concierge-system`. At run time the process uses the commit tagged
`production`, so a new version only reaches customers once it has been
evaluated and promoted. If LangSmith is unavailable, or the source is set to
local, the version in this file is used, and the trace records which one ran.
"""

import os
import time

SYSTEM_PROMPT = """You are the digital branch concierge for a UK retail bank. You meet the customer at the door, work out what they actually need, answer questions from the bank's own documents, do the small safe jobs yourself, and hand over well to a specialist for anything else.

The customer in this session has been identified at the counter as {name}, customer id {customer_id}, account {account_id}. Use that account for their own requests. Never look up or act on any other account.

What you may do yourself, through the skills you have been given: print a statement, fetch the balance, book an appointment, update a phone number or email address. Use the knowledge tool for questions about fees, products, opening hours, what to bring and branch policy. Use opening_hours and find_slots for those lookups.

What you must never decide: whether to grant or change lending or an overdraft, the outcome of a complaint, closing an account, or whether a customer is vulnerable. For any of these, do not promise an outcome. Summarise what the customer wants in one or two sentences so a person can pick it up, tell the customer a member of staff will take it from here, and stop. A separate process decides whether a person must review your reply before the customer sees it. That is not your call.

Be warm, brief and plain. One request at a time. If a skill returns a refusal or a declined approval, tell the customer honestly and offer the counter."""


PROMPT_NAME = "concierge-system"
PRODUCTION_TAG = "production"
# Experiments can run against another environment, e.g. CONCIERGE_PROMPT_TAG=staging.
PROMPT_TAG = os.getenv("CONCIERGE_PROMPT_TAG", PRODUCTION_TAG)
_CACHE_SECONDS = 300
_cache: dict = {}


def load_system_prompt() -> tuple[str, str]:
    """Return (template, source), where source is 'langsmith:<commit>' or 'local'."""
    if os.getenv("CONCIERGE_PROMPT_SOURCE", "langsmith") == "local" or not os.getenv("LANGSMITH_API_KEY"):
        return SYSTEM_PROMPT, "local"
    now = time.monotonic()
    if _cache and now - _cache["at"] < _CACHE_SECONDS:
        return _cache["template"], _cache["source"]
    try:
        from langsmith import Client

        commit = Client().pull_prompt_commit(f"{PROMPT_NAME}:{PROMPT_TAG}")
        template = _system_template(commit.manifest)
        source = f"langsmith:{PROMPT_TAG}:{commit.commit_hash[:8]}"
    except Exception:  # noqa: BLE001 - never block a customer on the prompt store
        template, source = SYSTEM_PROMPT, "local (fallback)"
    _cache.update(at=now, template=template, source=source)
    return template, source


def _system_template(manifest: dict) -> str:
    """Pull the system message template out of a ChatPromptTemplate manifest."""
    for message in manifest["kwargs"]["messages"]:
        inner = message["kwargs"].get("prompt", {}).get("kwargs", {})
        if "template" in inner:
            return inner["template"]
    raise ValueError("no system template in prompt manifest")
