"""Assemble facts: the structured inputs the impact and policy gate reads.

Every fact comes from a source the model cannot write to: the customer record
found at identification, the registry's risk ratings, the skills' own typed
results and the customer's own messages. The model's reply is read only by
fixed rules: whether it is empty, and whether it claims an outcome the
concierge must never decide.

Anything the process cannot read fails safe: a tool result that does not
match the expected shape is a reason for review, and a tool the registry does
not know counts as high risk.
"""

import json
import re

from langchain_core.messages import AIMessage, ToolMessage

from concierge.data import Customer
from concierge.registry import REGISTRY, RISK_RANK

POLICY_KEYWORDS = re.compile(
    r"\b(loan|lend|lending|borrow|overdraft|credit|mortgage decision|complaint|complain"
    r"|close my account|close the account|closure|vulnerab)",
    re.I,
)

# A reply that reports a decision the concierge may never make: an account
# closed, lending granted or refused, a complaint outcome.
OUTCOME_CLAIMS = re.compile(
    r"\b(account (is|has been|was) (now )?closed|closed your account"
    r"|(overdraft|loan|credit|lending|borrowing)\b[^.]{0,40}\b(approved|agreed|granted|increased|declined|refused)"
    r"|(approved|agreed|granted|increased) (your|the|an?) (overdraft|loan|credit)"
    r"|complaint\b[^.]{0,40}\b(upheld|resolved|rejected|closed))",
    re.I,
)

POLICY_REASON = "policy keyword in request"
EARLIER_POLICY_REASON = "policy request earlier in this conversation"
UNRECOGNISED_REASON = "unrecognised tool result"


def _status(message: ToolMessage, kind: str | None) -> str:
    try:
        body = json.loads(message.content)
    except (TypeError, ValueError):
        body = None
    if isinstance(body, dict) and body.get("status") in ("done", "refused"):
        return body["status"]
    if message.status == "error":
        # Rejected at pre-action approval, or arguments that failed validation:
        # the tool did not run.
        return "not run"
    if kind == "tool" and body is None:
        # Read-only tools answer in plain text.
        return "done"
    return "unrecognised"


def skills_run(turn_messages: list) -> tuple[list[dict[str, str]], str]:
    """Every tool call this turn, with its risk taken from the registry, not the result."""
    runs, max_risk = [], "none"
    for m in turn_messages:
        if not isinstance(m, ToolMessage):
            continue
        capability = REGISTRY.get(m.name or "")
        risk = capability.risk if capability else "high"
        runs.append({"tool": m.name or "", "risk": risk, "status": _status(m, capability and capability.kind)})
        if RISK_RANK[risk] > RISK_RANK[max_risk]:
            max_risk = risk
    return runs, max_risk


def final_reply(turn_messages: list) -> str:
    for m in reversed(turn_messages):
        if isinstance(m, AIMessage) and not m.tool_calls:
            return m.text.strip()
    return ""


def reasons(
    customer: Customer | None,
    request: str,
    max_risk: str,
    reply: str,
    *,
    runs: list[dict[str, str]] | None = None,
    policy_earlier: bool = False,
) -> list[str]:
    found = []
    if RISK_RANK.get(max_risk, RISK_RANK["high"]) >= RISK_RANK["medium"]:
        found.append(f"skill risk {max_risk}")
    if any(r["status"] == "unrecognised" for r in runs or []):
        found.append(UNRECOGNISED_REASON)
    if customer is None:
        found.append("no identified customer")
    else:
        if customer.open_complaint:
            found.append("open complaint on record")
        if customer.vulnerability_flag:
            found.append("vulnerability flag on record")
    if POLICY_KEYWORDS.search(request):
        found.append(POLICY_REASON)
    elif policy_earlier:
        # "Yes, please do that" after "close my account" carries the same intent.
        found.append(EARLIER_POLICY_REASON)
    if not reply:
        found.append("empty reply")
    elif OUTCOME_CLAIMS.search(reply):
        found.append("outcome claim in reply")
    return found
