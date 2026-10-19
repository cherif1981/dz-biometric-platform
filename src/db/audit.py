"""Immutable audit log: SHA3-256 hash chain + SQLite/Postgres triggers."""
import hashlib, json
from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import AuditLog

GENESIS = "0" * 64

async def append_audit(session: AsyncSession, *, actor_id=None, action,
                       resource_type, resource_id=None, metadata=None) -> AuditLog:
    last = (await session.execute(
        select(AuditLog).order_by(desc(AuditLog.id)).limit(1)
    )).scalar_one_or_none()
    prev_hash = last.row_hash if last else GENESIS
    ts = datetime.now(timezone.utc).isoformat()
    payload = json.dumps({
        "actor_id": actor_id, "action": action,
        "resource_type": resource_type, "resource_id": resource_id,
        "metadata": metadata or {}, "prev_hash": prev_hash, "ts": ts,
    }, sort_keys=True, default=str).encode()
    row_hash = hashlib.sha3_256(payload).hexdigest()
    row = AuditLog(actor_id=actor_id, action=action, resource_type=resource_type,
                   resource_id=resource_id, metadata_json=metadata or {},
                   prev_hash=prev_hash, row_hash=row_hash,
                   timestamp=datetime.now(timezone.utc))
    session.add(row); await session.flush()
    return row

async def verify_chain(session: AsyncSession) -> dict:
    """Recompute all hashes; return first broken row (or ok=True)."""
    rows = (await session.execute(select(AuditLog).order_by(AuditLog.id))).scalars().all()
    prev = GENESIS
    for r in rows:
        if r.prev_hash != prev:
            return {"ok": False, "broken_at": r.id, "reason": "prev_hash mismatch"}
        payload = json.dumps({
            "actor_id": r.actor_id, "action": r.action,
            "resource_type": r.resource_type, "resource_id": r.resource_id,
            "metadata": r.metadata_json or {},
            "prev_hash": r.prev_hash,
            "ts": r.timestamp.isoformat() if r.timestamp else None,
        }, sort_keys=True, default=str).encode()
        if hashlib.sha3_256(payload).hexdigest() != r.row_hash:
            return {"ok": False, "broken_at": r.id, "reason": "row_hash mismatch"}
        prev = r.row_hash
    return {"ok": True, "rows": len(rows)}
