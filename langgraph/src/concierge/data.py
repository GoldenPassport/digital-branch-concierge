"""Demo customers and knowledge documents, shared with the n8n and Camunda builds."""

import csv
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

SHARED = Path(__file__).resolve().parents[3] / "shared"
# v2 corrects T03 and T04 after the LangGraph review (ask before booking when
# the customer has not chosen a slot). The n8n build uses the original file.
TEST_CONVERSATIONS = SHARED / "evaluations" / "test-conversations-v2.csv"


@dataclass(frozen=True)
class Customer:
    customer_id: str
    name: str
    account_id: str
    balance: float
    phone: str
    email: str
    open_complaint: bool
    vulnerability_flag: bool
    segment: str


@cache
def customers() -> dict[str, Customer]:
    with open(SHARED / "data" / "customers.csv", newline="") as f:
        rows = csv.DictReader(f)
        return {
            r["customer_id"]: Customer(
                customer_id=r["customer_id"],
                name=r["name"],
                account_id=r["account_id"],
                balance=float(r["balance"]),
                phone=r["phone"],
                email=r["email"],
                open_complaint=r["open_complaint"].strip().lower() == "true",
                vulnerability_flag=r["vulnerability_flag"].strip().lower() == "true",
                segment=r["segment"],
            )
            for r in rows
        }


def customer(customer_id: str | None) -> Customer | None:
    return customers().get(customer_id or "")


def account_owner(account_id: str | None) -> Customer | None:
    return next((c for c in customers().values() if c.account_id == account_id), None)


@dataclass(frozen=True)
class Section:
    document: str
    heading: str
    text: str


@cache
def knowledge_sections() -> tuple[Section, ...]:
    """Split each knowledge document into its ## sections."""
    sections: list[Section] = []
    for path in sorted((SHARED / "knowledge").glob("*.md")):
        document = path.stem.replace("-", " ")
        for block in re.split(r"^## ", path.read_text(), flags=re.M)[1:]:
            heading, _, body = block.partition("\n")
            sections.append(Section(document, heading.strip(), body.strip()))
    return tuple(sections)
