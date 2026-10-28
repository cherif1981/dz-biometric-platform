import os, json, hashlib, sqlite3, time
from typing import Optional

AUDIT_DB = os.environ.get("AUDIT_DB", "/tmp/audit.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    event_type   TEXT NOT NULL,
    job_id       TEXT,
    nonce        TEXT,
    decision     TEXT,
    pad_score    REAL,
    receipt_hash TEXT,
    metadata     TEXT,
    prev_hash    TEXT NOT NULL,
    row_hash     TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS audit_no_update
BEFORE UPDATE ON audit_logs
BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete
BEFORE DELETE ON audit_logs
BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END;
CREATE INDEX IF NOT EXISTS idx_audit_ts  ON audit_logs(ts);
CREATE INDEX IF NOT EXISTS idx_audit_job ON audit_logs(job_id);
"""

def _conn():
    c = sqlite3.connect(AUDIT_DB)
    c.executescript(SCHEMA)
    return c

def _last_hash(conn):
    row = conn.execute(
        "SELECT row_hash FROM audit_logs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else "GENESIS"

def _canonical(p):
    return json.dumps(p, sort_keys=True, separators=(",",":")).encode()

def append_event(event_type, *, job_id=None, nonce=None, decision=None,
                 pad_score=None, receipt_hash=None, metadata=None) -> str:
    conn = _conn()
    try:
        prev = _last_hash(conn)
        ts = time.time()
        payload = {
            "event_type": event_type, "job_id": job_id, "nonce": nonce,
            "decision": decision, "pad_score": pad_score,
            "receipt_hash": receipt_hash, "metadata": metadata or {},
            "ts": ts,
        }
        payload_hash = hashlib.sha256(_canonical(payload)).hexdigest()
        row_hash = hashlib.sha256((prev + payload_hash).encode()).hexdigest()
        conn.execute(
            """INSERT INTO audit_logs
               (ts, event_type, job_id, nonce, decision, pad_score,
                receipt_hash, metadata, prev_hash, row_hash)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (ts, event_type, job_id, nonce, decision, pad_score,
             receipt_hash, json.dumps(metadata or {}), prev, row_hash)
        )
        conn.commit()
        return row_hash
    finally:
        conn.close()

def verify_chain() -> dict:
    conn = _conn()
    try:
        rows = conn.execute(
            """SELECT id, ts, event_type, job_id, nonce, decision, pad_score,
                      receipt_hash, metadata, prev_hash, row_hash
               FROM audit_logs ORDER BY id ASC"""
        ).fetchall()
    finally:
        conn.close()

    prev = "GENESIS"
    for (rid, ts, et, jid, nonce, dec, ps, rh, meta, stored_prev, stored_hash) in rows:
        if stored_prev != prev:
            return {"ok": False, "broken_at": rid, "reason": "prev_hash mismatch"}
        payload = {
            "event_type": et, "job_id": jid, "nonce": nonce,
            "decision": dec, "pad_score": ps, "receipt_hash": rh,
            "metadata": json.loads(meta) if meta else {}, "ts": ts,
        }
        payload_hash = hashlib.sha256(_canonical(payload)).hexdigest()
        expected = hashlib.sha256((prev + payload_hash).encode()).hexdigest()
        if expected != stored_hash:
            return {"ok": False, "broken_at": rid, "reason": "row_hash mismatch"}
        prev = stored_hash

    return {"ok": True, "records": len(rows), "head": prev}

def count() -> int:
    conn = _conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
    finally:
        conn.close()
