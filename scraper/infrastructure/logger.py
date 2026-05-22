"""Logging estructurado en JSON para auditoria y debugging."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import config, ROOT_DIR


class JsonFormatter(logging.Formatter):
    """Formateador JSON: una linea por evento."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Anadir extras
        for key, value in record.__dict__.items():
            if key in {
                "args", "msg", "levelname", "levelno", "pathname", "filename",
                "module", "exc_info", "exc_text", "stack_info", "lineno",
                "funcName", "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "name", "message",
                "taskName",
            }:
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def _ensure_log_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def setup_logging() -> logging.Logger:
    """Configura logging global con salida JSON a fichero y stdout."""
    log_path = Path(config.logs.file)
    if not log_path.is_absolute():
        log_path = ROOT_DIR / log_path
    _ensure_log_dir(log_path)

    root = logging.getLogger("scraper")
    root.setLevel(getattr(logging, config.logs.level.upper(), logging.INFO))
    root.handlers.clear()

    # Handler fichero JSONL
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)

    # Handler stdout (legible)
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s :: %(message)s")
    )
    root.addHandler(stdout)

    root.propagate = False
    return root


def get_logger(name: str) -> logging.Logger:
    """Logger con prefijo del paquete principal."""
    return logging.getLogger(f"scraper.{name}")


# Inicializar al importar
setup_logging()