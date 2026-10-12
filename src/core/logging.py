import sys
from loguru import logger


def setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        enqueue=True,
    )
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="14 days",
        level="INFO",
        enqueue=True,
    )


__all__ = ["logger", "setup_logging"]