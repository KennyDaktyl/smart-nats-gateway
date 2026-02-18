import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from app.core.config import settings

# ==============================
# Paths
# ==============================

LOG_DIR = Path(settings.LOG_DIR)
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE_PATH = LOG_DIR / "agent.log"

# ==============================
# Format
# ==============================

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

# ==============================
# File Handler (Daily rotation)
# ==============================

file_handler = TimedRotatingFileHandler(
    filename=str(LOG_FILE_PATH),
    when="midnight",  # rotate daily
    interval=1,
    backupCount=14,  # keep 14 days
    encoding="utf-8",
    utc=False,  # change to True if you want UTC rotation
)

file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Optional: better filename format
file_handler.suffix = "%Y-%m-%d"

# ==============================
# Console Handler
# ==============================

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# ==============================
# Root Logger Setup
# ==============================

root_logger = logging.getLogger()

if not root_logger.handlers:
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

# ==============================
# Uvicorn compatibility (if used)
# ==============================

for name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
    log = logging.getLogger(name)
    log.handlers = root_logger.handlers
    log.setLevel(logging.INFO)
    log.propagate = False

root_logger.info(f"Logging initialized. Writing logs to: {LOG_FILE_PATH}")

# App-level logger
logger = logging.getLogger("app")
