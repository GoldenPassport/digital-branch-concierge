"""The meaningful human decision: what the decision owner sees and returns.

The graph pauses with `interrupt(payload)`. The owner resumes it (in LangSmith
Studio for this demo) with a decision, their name and, optionally, an edited
reply. A resume without a recognised decision or a named approver fails safe
to hold.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ValidationError

HELD_REPLY = "Thank you. A member of staff is taking this from here and will be with you shortly."


class OwnerDecision(BaseModel):
    decision: Literal["approve", "hold"]
    approver: str
    note: str = ""
    edited_reply: str | None = None


def review_payload(customer, request: str, reasons: list[str], skills_run: list, draft_reply: str) -> dict:
    return {
        "decision_point": "reply review",
        "question": "Review before the customer sees this.",
        "customer": {"name": customer.name, "customer_id": customer.customer_id} if customer else None,
        "request": request,
        "why_the_gate_fired": reasons,
        "skills_run": skills_run,
        "proposed_reply": draft_reply,
        "resume_with": {
            "decision": "approve | hold",
            "approver": "your name",
            "note": "optional",
            "edited_reply": "optional replacement reply",
        },
    }


def read_decision(raw) -> dict:
    """Validate the owner's resume value and stamp when it was decided."""
    decided_at = datetime.now(UTC).isoformat(timespec="seconds")
    try:
        d = OwnerDecision.model_validate(raw)
        if not d.approver.strip():
            raise ValueError("approver is required")
        return {**d.model_dump(), "decided_at": decided_at, "valid": True}
    except (ValidationError, ValueError, TypeError) as err:
        return {
            "decision": "hold",
            "approver": "",
            "note": f"Invalid decision, held by default: {err}",
            "edited_reply": None,
            "decided_at": decided_at,
            "valid": False,
        }
