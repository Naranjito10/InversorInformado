"""Estado en memoria del scraper — compartido entre runner y API."""
from __future__ import annotations
import threading
from datetime import datetime, timezone

_lock = threading.Lock()

_state: dict = {
    "running": False,
    "done": False,
    "event": None,
    "message": None,
    "portal": None,
    "new": 0,
    "updated": 0,
    "errors": 0,
    "queued": 0,
    "started_at": None,
    "finished_at": None,
}


def get() -> dict:
    with _lock:
        return dict(_state)


def set_running(portal: str | None = None, message: str = "Iniciando búsqueda...") -> None:
    with _lock:
        _state["running"] = True
        _state["done"] = False
        _state["event"] = "started"
        _state["message"] = message
        _state["portal"] = portal
        _state["new"] = 0
        _state["updated"] = 0
        _state["errors"] = 0
        _state["queued"] = max(0, _state["queued"] - 1)
        _state["started_at"] = datetime.now(timezone.utc).isoformat()
        _state["finished_at"] = None


def inc_queued() -> None:
    with _lock:
        _state["queued"] += 1


def update(event: str, message: str, portal: str | None = None) -> None:
    with _lock:
        _state["event"] = event
        _state["message"] = message
        if portal is not None:
            _state["portal"] = portal


def inc_new() -> None:
    with _lock:
        _state["new"] += 1


def inc_updated() -> None:
    with _lock:
        _state["updated"] += 1


def inc_error() -> None:
    with _lock:
        _state["errors"] += 1


def set_done(new: int = 0, updated: int = 0, errors: int = 0) -> None:
    with _lock:
        _state["running"] = False
        _state["done"] = True
        _state["event"] = "cycle_done"
        _state["message"] = "Búsqueda completada"
        _state["new"] = new
        _state["updated"] = updated
        _state["errors"] = errors
        _state["finished_at"] = datetime.now(timezone.utc).isoformat()


def dismiss() -> None:
    with _lock:
        _state["done"] = False
        _state["event"] = None
        _state["message"] = None
        _state["queued"] = 0
