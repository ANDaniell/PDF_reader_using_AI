
import os
import sys
import logging
import logging.config
import logging.handlers

# --- Базовые пути ---

# Пытаемся найти корень проекта как папку, где лежит этот файл
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Папка для логов: <корень_проекта>/logs
LOG_DIR = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "app.log")


# --- Конфиг логирования ---

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "standard": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": sys.stdout,
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": LOG_FILE,
            "maxBytes": 5_000_000,
            "backupCount": 5,        # хранить 5 старых файлов
            "encoding": "utf-8",
        },
    },

    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
}


def setup_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Удобный способ получить логгер в других файлах.

    Пример:
        from logging_config import get_logger
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)