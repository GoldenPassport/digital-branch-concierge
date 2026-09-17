"""Pre-action authorisation: a deterministic check before any skill runs.

Used twice, on purpose: by the agent middleware before a call is executed and
again inside each skill (defence in depth, like the n8n skills' first node).
"""

from dataclasses import dataclass

from concierge import data
from concierge.registry import REGISTRY


@dataclass(frozen=True)
class Authorisation:
    authorised: bool
    reason: str
    risk: str


def authorise(name: str, session_customer_id: str | None, account_id: str | None = None) -> Authorisation:
    capability = REGISTRY.get(name)
    if capability is None:
        return Authorisation(False, f"{name} is not an allowed skill or tool.", "high")
    if capability.kind == "tool":
        return Authorisation(True, "Read-only lookup.", capability.risk)
    session = data.customer(session_customer_id)
    if session is None:
        return Authorisation(
            False,
            "No identified customer in this session. Identification happens before any account action.",
            capability.risk,
        )
    if account_id:
        owner = data.account_owner(account_id)
        if owner is None or owner.customer_id != session.customer_id:
            return Authorisation(False, "The account does not belong to the identified customer.", capability.risk)
    return Authorisation(True, "Within policy for this customer.", capability.risk)
