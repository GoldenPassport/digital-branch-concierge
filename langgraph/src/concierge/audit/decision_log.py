"""The decision record: one row per human decision, the evidence an auditor gets.

SQLite for the demo. Idempotent on (thread_id, turn_id), so a node that runs
again after a resume does not write a second row.
"""

import json
import os
import sqlite3
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "decisions.sqlite"


def _connect() -> sqlite3.Connection:
    path = Path(os.getenv("CONCIERGE_DECISIONS_DB", DEFAULT_PATH))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS human_decisions (
            thread_id TEXT, turn_id TEXT, customer_id TEXT, test_id TEXT,
            decision_point TEXT, request TEXT, reasons TEXT, skills_run TEXT,
            proposed_reply TEXT, decision TEXT, approver TEXT, note TEXT,
            edited_reply TEXT, decided_at TEXT, recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (thread_id, turn_id)
        )"""
    )
    return conn


def record(row: dict) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO human_decisions
               (thread_id, turn_id, customer_id, test_id, decision_point, request, reasons, skills_run,
                proposed_reply, decision, approver, note, edited_reply, decided_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["thread_id"], row["turn_id"], row["customer_id"], row.get("test_id"),
                "reply review", row["request"], json.dumps(row["reasons"]), json.dumps(row["skills_run"]),
                row["proposed_reply"], row["decision"], row["approver"], row["note"],
                row.get("edited_reply"), row["decided_at"],
            ),
        )


def rows() -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute("SELECT * FROM human_decisions ORDER BY recorded_at")]
