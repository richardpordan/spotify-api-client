"""Custom logger setup."""

import datetime
import logging
from pathlib import Path


def _get_timestamp() -> str:
    """Get a timestamp suitable for filenames: YYYYMMDDHHMMSS."""
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")


def setup_logger(
    name: str = __name__,
    logs_folder_path: Path | str | None = None,
    stream: bool = True,
    level: int = logging.INFO,
    fmt: str | None = None,
) -> logging.Logger:
    """Set up a custom logger.

    Args:
        name: Logger name.
        logs_folder_path: If provided, writes logs to this folder.
        stream: If True, logs are also printed to stdout.
        level: Logging level.
        fmt: Optional log message format.

    Returns:
        Configured logger instance.

    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if fmt is None:
        fmt = (
            "%(asctime)s %(levelname)s %(threadName)s %(module)s "
            "%(funcName)s %(lineno)d: %(message)s"
        )

    formatter = logging.Formatter(fmt)

    # Stream handler
    if stream:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    # File handler
    if logs_folder_path:
        logs_path = Path(logs_folder_path)
        logs_path.mkdir(parents=True, exist_ok=True)
        filename = logs_path / f"{_get_timestamp()}.log"
        file_handler = logging.FileHandler(filename, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
