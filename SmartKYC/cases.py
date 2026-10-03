"""Local SQLite case history. One connection per operation."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from settings import ROOT


@contextmanager
def connect():
    (ROOT / "data").mkdir(exist_ok=True)
    db = sqlite3.connect(ROOT / "data/cases.sqlite3", timeout=10)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
        with db:
            yield db
    finally:
        db.close()


def save(case):
    with connect() as db:
        db.execute("INSERT INTO cases VALUES (?, ?)", (case["id"], json.dumps(case)))


def get(case_id):
    with connect() as db:
        row = db.execute("SELECT body FROM cases WHERE id = ?", (case_id,)).fetchone()
    return json.loads(row[0]) if row else None


def list_cases():
    with connect() as db:
        rows = db.execute("SELECT body FROM cases ORDER BY rowid DESC LIMIT 100").fetchall()
    items = [json.loads(row[0]) for row in rows]
    return [{k: c[k] for k in ("id", "created_at", "applicant", "risk", "status", "source")} for c in items]


def review(case_id, action, note, reviewer):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT body FROM cases WHERE id = ?", (case_id,)).fetchone()
        if not row:
            raise ValueError("Case not found")
        case = json.loads(row[0])
        case["status"] = action
        case["reviews"].append(dict(action=action, note=note, reviewer=reviewer,
                                    at=datetime.now(timezone.utc).isoformat()))
        db.execute("UPDATE cases SET body = ? WHERE id = ?", (json.dumps(case), case_id))
    return case
