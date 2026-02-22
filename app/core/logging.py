import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from app.core.config import settings


LOG_DIR = Path(settings.LOG_DIR).expanduser().resolve()
LOG_DIR.mkdir(parents=True, exist_ok=True)

APP_LOG_FILE_PATH = LOG_DIR / "gateway.log"
ERROR_LOG_FILE_PATH = LOG_DIR / "gateway.error.log"

LOG_FORMAT = (
    "[%(asctime)s] [%(levelname)s] [%(name)s] "
    "[pid=%(process)d] %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _resolve_log_level() -> int:
    configured_level = settings.LOG_LEVEL.upper()
    return getattr(logging, configured_level, logging.INFO)


def _build_rotating_handler(log_file: Path, level: int) -> TimedRotatingFileHandler:
    handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
        utc=False,
    )
    handler.suffix = "%Y-%m-%d"
    handler.setLevel(level)
    return handler


def setup_logging() -> logging.Logger:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_gateway_logging_configured", False):
        return logging.getLogger("app")

    log_level = _resolve_log_level()
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    app_file_handler = _build_rotating_handler(APP_LOG_FILE_PATH, log_level)
    app_file_handler.setFormatter(formatter)

    error_file_handler = _build_rotating_handler(
        ERROR_LOG_FILE_PATH,
        logging.ERROR,
    )
    error_file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(app_file_handler)
    root_logger.addHandler(error_file_handler)
    root_logger.addHandler(console_handler)
    root_logger._gateway_logging_configured = True

    logging.captureWarnings(True)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = root_logger.handlers
        uvicorn_logger.setLevel(log_level)
        uvicorn_logger.propagate = False

    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    app_logger.info(
        "Logging initialized. log_dir=%s level=%s",
        LOG_DIR,
        logging.getLevelName(log_level),
    )
    return app_logger


logger = setup_logging()
