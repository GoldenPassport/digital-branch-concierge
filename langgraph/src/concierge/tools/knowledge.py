import re

from langchain.tools import tool

from concierge import data


@tool
def knowledge(query: str) -> str:
    """Search the bank's own documents: fees and product terms, opening hours, what to bring,
    appointments, complaints policy, what the concierge may and may not do. Input: a short search
    phrase. Returns the most relevant sections. Use it before answering any policy or product question."""
    words = [w for w in re.split(r"[^a-z0-9]+", query.lower()) if len(w) > 2]
    scored = []
    for section in data.knowledge_sections():
        haystack = f"{section.document} {section.heading} {section.text}".lower()
        score = sum(1 for w in words if w in haystack)
        if score:
            scored.append((score, section))
    if not scored:
        return "No matching section in the bank documents. Say so rather than guessing."
    top = sorted(scored, key=lambda s: -s[0])[:3]
    return "\n\n".join(f"[{s.document} / {s.heading}]\n{s.text}" for _, s in top)
