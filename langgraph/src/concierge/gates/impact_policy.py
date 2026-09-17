"""The impact and policy gate: a pure function over structured facts.

No model call. Only an explicit, positive classification goes straight
through; any reason at all, or anything unrecognised, goes to a person.
"""

from concierge.state import Route


def classify(guard_passed: bool, reasons: list[str]) -> Route:
    if not guard_passed:
        return "refused"
    return "straight_through" if not reasons else "review"
