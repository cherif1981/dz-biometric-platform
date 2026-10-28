"""Append-only audit log. SQLite for dev; Postgres for prod.

FIX: ":memory:" in SQLite creates a NEW database per connection. We
translate it to a unique temp file so schema persists across connections.
"""
import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AuditEvent:
    event_type: str
    actor_id: Optional[str] = None
    subject_id: Optional[str] = None
    outcome: str = "info"
    metadata: dict = field(default_factory=dict)


SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_id TEXT,
    subject_id TEXT,
    outcome TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    row_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_events(ts);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_events(event_type);

CREATE TRIGGER IF NOT EXISTS trg_audit_no_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit_events is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_no_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit_events is append-only');
END;
"""


def _resolve_path(db_path: str) -> str:
    """Translate ':memory:' to a unique temp file (SQLite :memory: is per-conn)."""
    if db_path == ":memory:":
        fd, path = tempfile.mkstemp(prefix="audit_", suffix=".sqlite")
        os.close(fd)
        return path
    return db_path


class AuditLog:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = _resolve_path(db_path)
        self._last_hash = "0" * 64
        self._init_db()

    def _init_db(self):
        with self._conn() as c:
            c.executescript(SCHEMA)
            row = c.execute(
                "SELECT row_hash FROM audit_events ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                self._last_hash = row[0]

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record(self, event: AuditEvent) -> int:
        ts = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(
            {"ts": ts, **asdict(event)}, sort_keys=True, ensure_ascii=False
        )
        row_hash = hashlib.sha256(
            (self._last_hash + payload).encode()
        ).hexdigest()
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO audit_events "
                "(ts, event_type, actor_id, subject_id, outcome, "
                " metadata_json, prev_hash, row_hash) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (ts, event.event_type, event.actor_id, event.subject_id,
                 event.outcome, json.dumps(event.metadata, ensure_ascii=False),
                 self._last_hash, row_hash),
            )
            new_id = cur.lastrowid
        self._last_hash = row_hash
        return new_id

    def verify_chain(self) -> bool:
        with self._conn() as c:
            rows = c.execute(
                "SELECT ts, event_type, actor_id, subject_id, outcome, "
                "metadata_json, prev_hash, row_hash FROM audit_events ORDER BY id"
            ).fetchall()
        expected_prev = "0" * 64
        for ts, et, ac, su, oc, mj, ph, rh in rows:
            if ph != expected_prev:
                return False
            payload = json.dumps({
                "ts": ts, "event_type": et, "actor_id": ac,
                "subject_id": su, "outcome": oc,
                "metadata": json.loads(mj),
            }, sort_keys=True, ensure_ascii=False)
            calc = hashlib.sha256((expected_prev + payload).encode()).hexdigest()
            if calc != rh:
                return False
            expected_prev = rh
        return True

    def count(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]

    def cleanup(self):
        """Delete temp file if we created one."""
        if self.db_path != ":memory:" and "audit_" in os.path.basename(self.db_path):
            try:
                os.remove(self.db_path)
            except FileNotFoundError:
                pass
