"""Structured logging: loguru → console + JSON file (logs/audit.jsonl)."""
import logging, pathlib, sys
from loguru import logger


class _InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


_configured = False


def setup_logging(level: str = "INFO", log_dir: str = "logs") -> None:
    global _configured
    if _configured:
        return
    _configured = True

    d = pathlib.Path(log_dir); d.mkdir(exist_ok=True)
    audit = d / "audit.jsonl"

    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> "
               "| {name}:{function}:{line} - {message}",
    )
    logger.add(
        audit,
        level=level,
        format="{message}",
        serialize=True,          # JSON per line
        rotation="10 MB",
        retention="30 days",
        enqueue=False,
    )

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "httpx", "httpcore"):
        lg = logging.getLogger(name)
        lg.handlers = [_InterceptHandler()]
        lg.propagate = False


def audit_event(event: str, **fields) -> None:
    """Log an audit event as structured JSON (extra fields appear in audit.jsonl)."""
    logger.bind(**fields).info(event)
