"""Output guardrail: masks sensitive numbers before a reply leaves the process.

Mirrors the n8n Guardrails out node (card numbers, IBANs, bank account
numbers and secret keys).
"""

import re

RULES = [
    ("card number", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,4})?\b")),
    ("sort code and account", re.compile(r"\b\d{2}-\d{2}-\d{2}\s+\d{8}\b")),
    ("secret key", re.compile(r"\b(?:sk|pk|xox[bp])-[A-Za-z0-9-]{16,}\b")),
]


def sanitise(text: str) -> tuple[str, list[str]]:
    found = []
    for label, pattern in RULES:
        if pattern.search(text):
            found.append(label)
            text = pattern.sub(f"[{label} removed]", text)
    return text, found
