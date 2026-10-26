import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Optional

DB_PATH = "/tmp/dz_biometric.db"


@dataclass
class AuditRecord:
    id: Optional[int]
    timestamp: float
    status: str
    confidence: float
    face_similarity: Optional[float]
    liveness_score: Optional[float]
    antispoof_score: Optional[float]
    ocr_fields: Dict[str, Any]
    reasons: list
    client_ip: Optional[str] = None


class AuditDB:
    def __init__(self, path=DB_PATH):
        self.path = path
        self._init()

    def _init(self):
        with sqlite3.connect(self.path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL NOT NULL,
                status TEXT NOT NULL, confidence REAL, face_similarity REAL,
                liveness_score REAL, antispoof_score REAL, ocr_fields TEXT,
                reasons TEXT, client_ip TEXT)""")

    def log(self, r):
        with sqlite3.connect(self.path) as c:
            cur = c.execute(
                "INSERT INTO verifications VALUES (NULL,?,?,?,?,?,?,?,?,?)",
                (
                    r.timestamp,
                    r.status,
                    r.confidence,
                    r.face_similarity,
                    r.liveness_score,
                    r.antispoof_score,
                    json.dumps(r.ocr_fields),
                    json.dumps(r.reasons),
                    r.client_ip,
                ),
            )
            return cur.lastrowid

    def stats(self):
        with sqlite3.connect(self.path) as c:
            total = c.execute("SELECT COUNT(*) FROM verifications").fetchone()[0]
            by = dict(
                c.execute("SELECT status, COUNT(*) FROM verifications GROUP BY status").fetchall()
            )
            return {"total": total, "by_status": by}

    def recent(self, limit=20):
        with sqlite3.connect(self.path) as c:
            rows = c.execute(
                "SELECT id,timestamp,status,confidence,face_similarity,"
                "liveness_score,reasons FROM verifications "
                "ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "timestamp": r[1],
                    "status": r[2],
                    "confidence": r[3],
                    "face_similarity": r[4],
                    "liveness_score": r[5],
                    "reasons": json.loads(r[6]) if r[6] else [],
                }
                for r in rows
            ]
