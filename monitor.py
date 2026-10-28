"""مراقبة دورية لسلسلة التدقيق — تكتشف أول كسر فورًا."""
import os, json, hashlib, sqlite3, threading, logging, time
from typing import Callable, Optional

log = logging.getLogger("audit.monitor")
if not log.handlers:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

def verify_chain(db_path: str) -> dict:
    """يعيد {'ok': True, 'records': N, 'head': hash} أو
    {'ok': False, 'broken_at': id, 'reason': str, 'records': N}."""
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        rows = conn.execute(
            """SELECT id, ts, event_type, job_id, nonce, decision, pad_score,
                      receipt_hash, metadata, prev_hash, row_hash
               FROM audit_logs ORDER BY id ASC"""
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {"ok": True, "records": 0, "head": "GENESIS"}

    prev = "GENESIS"
    for row in rows:
        rid, ts, et, jid, nonce, dec, ps, rh, meta, stored_prev, stored_hash = row
        if stored_prev != prev:
            return {"ok": False, "broken_at": rid,
                    "reason": "prev_hash mismatch", "records": len(rows)}
        payload = {
            "event_type": et, "job_id": jid, "nonce": nonce,
            "decision": dec, "pad_score": ps, "receipt_hash": rh,
            "metadata": json.loads(meta) if meta else {}, "ts": ts,
        }
        c = json.dumps(payload, sort_keys=True, separators=(",",":")).encode()
        ph = hashlib.sha256(c).hexdigest()
        expected = hashlib.sha256((prev + ph).encode()).hexdigest()
        if expected != stored_hash:
            return {"ok": False, "broken_at": rid,
                    "reason": "row_hash mismatch", "records": len(rows)}
        prev = stored_hash

    return {"ok": True, "records": len(rows), "head": prev}


def monitor(db_path: str, interval: int = 5,
            on_tamper: Optional[Callable[[dict], None]] = None,
            on_check: Optional[Callable[[dict], None]] = None,
            stop_event: Optional[threading.Event] = None,
            max_consecutive_errors: int = 3):
    """حلقة مراقبة. تستدعي on_tamper عند أول كسر، وتتوقف فورًا.
    عند تعذّر قراءة القاعدة N مرات متتالية، يُعتبر ذلك تلاعبًا."""
    stop_event = stop_event or threading.Event()
    prev_head = None
    errors = 0

    while not stop_event.is_set():
        try:
            v = verify_chain(db_path)
            errors = 0
        except Exception as e:
            errors += 1
            log.warning(f"verify_chain فشل ({errors}/{max_consecutive_errors}): {e}")
            if errors >= max_consecutive_errors:
                info = {"ok": False, "reason": f"db_unreachable: {e}",
                        "broken_at": None, "records": 0}
                if on_tamper: on_tamper(info)
                return
            stop_event.wait(interval); continue

        if not v["ok"]:
            log.error(f"🚨 TAMPER DETECTED: {v}")
            if on_tamper: on_tamper(v)
            return  # توقف — لا مزيد من الدورات بعد كسر مؤكد

        if on_check: on_check(v)
        if prev_head and prev_head != v["head"]:
            log.info(f"سجل جديد: records={v['records']}")
        prev_head = v["head"]
        stop_event.wait(interval)
