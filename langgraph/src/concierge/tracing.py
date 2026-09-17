"""Observability with privacy built in.

Traces go to LangSmith, but personal data is masked on this machine before
anything is sent: the LangSmith client's anonymizer rewrites every string in a
run's inputs and outputs. Configured once at start-up (`configure_tracing`),
it covers the graph, the agent, model calls and tools, because LangChain's
tracer uses LangSmith's shared client.

Each trace is also tagged the way the n8n build tagged executions: test id,
a pseudonymous customer reference and session on the identify step, and the
gate's route and final outcome in the trace's outputs, where LangSmith rules
and filters can use them.
"""

import hashlib
import re

import langsmith as ls
from langsmith.anonymizer import DEFAULT_SECRET_RULES, create_anonymizer
from langsmith.run_helpers import get_current_run_tree

from concierge import data

_configured = False


def customer_ref(customer_id: str | None) -> str:
    """A stable pseudonym, so traces for one customer can be grouped without naming them."""
    if not customer_id:
        return "unidentified"
    return "cust-" + hashlib.sha256(customer_id.encode()).hexdigest()[:8]


def masking_rules() -> list[dict]:
    names = sorted({c.name for c in data.customers().values()}, key=len, reverse=True)
    rules = [
        {"pattern": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "replace": "[email]"},
        {"pattern": re.compile(r"\+44\s?\d{4}\s?\d{6}|\b07\d{3}\s?\d{6}\b"), "replace": "[phone]"},
        {"pattern": re.compile(r"\bACC-\d{4}\b"), "replace": "[account]"},
        {"pattern": re.compile(r"\b\d(?:[ -]?\d){12,18}\b"), "replace": "[card]"},
    ]
    if names:
        rules.append({"pattern": re.compile("|".join(re.escape(n) for n in names)), "replace": "[customer name]"})
    return rules + list(DEFAULT_SECRET_RULES)


def configure_tracing() -> None:
    """Install a LangSmith client that masks personal data before upload. Safe to call twice."""
    global _configured
    if _configured:
        return
    ls.configure(client=ls.Client(anonymizer=create_anonymizer(masking_rules())))
    _configured = True


def tag_trace(**metadata) -> None:
    """Record metadata on the current node's run in the trace.

    LangSmith does not link a node's run object to the root run in memory, so
    anything the whole trace should be filterable by belongs in the graph's
    output (route and outcome are part of ConciergeOutput).
    """
    run = get_current_run_tree()
    if run is not None:
        run.add_metadata({k: v for k, v in metadata.items() if v is not None})
