"""The skill and tool registry: the agent's whole reach, with risk ratings.

The pre-action gate and the impact and policy gate read this, never the model.
Anything not listed here is refused.
"""

from dataclasses import dataclass
from typing import Literal

Risk = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class Capability:
    name: str
    kind: Literal["skill", "tool"]
    risk: Risk
    writes: bool
    reversible: bool
    needs_approval: bool


REGISTRY: dict[str, Capability] = {
    c.name: c
    for c in [
        Capability("print_statement", "skill", "low", writes=False, reversible=True, needs_approval=False),
        Capability("fetch_balance", "skill", "low", writes=False, reversible=True, needs_approval=False),
        Capability("book_appointment", "skill", "low", writes=True, reversible=True, needs_approval=False),
        Capability("update_contact_details", "skill", "medium", writes=True, reversible=True, needs_approval=True),
        Capability("opening_hours", "tool", "low", writes=False, reversible=True, needs_approval=False),
        Capability("find_slots", "tool", "low", writes=False, reversible=True, needs_approval=False),
        Capability("knowledge", "tool", "low", writes=False, reversible=True, needs_approval=False),
    ]
}

RISK_RANK: dict[str, int] = {"none": 0, "low": 1, "medium": 2, "high": 3}
