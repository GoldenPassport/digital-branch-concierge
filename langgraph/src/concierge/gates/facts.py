"""Assemble facts: the structured inputs the impact and policy gate reads.

Every fact comes from a source the model cannot write to: the customer record
found at identification, the skills' own typed results, and the customer's
own message. The model's reply is checked only for being empty.
"""

import json
import re

from langchain_core.messages import AIMessage, ToolMessage

from concierge.data import Customer
from concierge.registry import RISK_RANK

POLICY_KEYWORDS = re.compile(
    r"\b(loan|lend|lending|borrow|overdraft|credit|mortgage decision|complaint|complain"
    r"|close my account|close the account|closure|vulnerab)",
    re.I,
)


def skills_run(turn_messages: list) -> tuple[list[dict[str, str]], str]:
    runs, max_risk = [], "none"
    for m in turn_messages:
        if not isinstance(m, ToolMessage):
            continue
        try:
            body = json.loads(m.content)
        except (TypeError, ValueError):
            body = {}
        risk = body.get("risk", "n/a")
        runs.append({"tool": m.name or "", "risk": risk, "status": body.get("status", "n/a")})
        if RISK_RANK.get(risk, 0) > RISK_RANK[max_risk]:
            max_risk = risk
    return runs, max_risk


def final_reply(turn_messages: list) -> str:
    for m in reversed(turn_messages):
        if isinstance(m, AIMessage) and not m.tool_calls:
            return m.text.strip()
    return ""


def reasons(customer: Customer | None, request: str, max_risk: str, reply: str) -> list[str]:
    found = []
    if RISK_RANK.get(max_risk, 0) >= RISK_RANK["medium"]:
        found.append(f"skill risk {max_risk}")
    if customer is None:
        found.append("no identified customer")
    else:
        if customer.open_complaint:
            found.append("open complaint on record")
        if customer.vulnerability_flag:
            found.append("vulnerability flag on record")
    if POLICY_KEYWORDS.search(request):
        found.append("policy keyword in request")
    if not reply:
        found.append("empty reply")
    return found
