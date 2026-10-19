"""Immutable audit triggers — SQLite-compatible."""
TRIGGERS = [
    """CREATE TRIGGER IF NOT EXISTS audit_no_update
       BEFORE UPDATE ON audit_log
       BEGIN SELECT RAISE(ABORT, 'audit_log is immutable (UPDATE blocked)'); END""",
    """CREATE TRIGGER IF NOT EXISTS audit_no_delete
       BEFORE DELETE ON audit_log
       BEGIN SELECT RAISE(ABORT, 'audit_log is immutable (DELETE blocked)'); END""",
]

async def install(engine):
    async with engine.begin() as conn:
        for stmt in TRIGGERS:
            await conn.exec_driver_sql(stmt)
