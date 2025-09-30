# utilities/logger_setup.py
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(level=logging.INFO, log_dir: str | Path = None) -> logging.Logger:
    # Default to a 'logs' directory next to the project root (one level above utilities/)
    here = Path(__file__).resolve().parent
    default_log_dir = here.parent / "logs"
    log_dir = Path(log_dir) if log_dir else default_log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "app.log"

    fmt = "%(asctime)s %(levelname)-5s %(name)s:%(lineno)d | %(message)s"
    root = logging.getLogger()
    # Avoid duplicate handlers on re-imports
    if root.handlers:
        root.handlers.clear()

    root.setLevel(level)

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(fmt))
    root.addHandler(sh)

    # RotatingFileHandler: 5 MB per file, keep 3 backups
    fh = RotatingFileHandler(
        str(log_file), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(logging.Formatter(fmt))
    root.addHandler(fh)

    # Print where we are logging (helpful in debugging)
    print(f"Logging to {log_file.resolve()}")

    return root
