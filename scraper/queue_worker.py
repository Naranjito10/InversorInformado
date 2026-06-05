"""Cola de tareas del scraper — garantiza ejecución secuencial."""
from __future__ import annotations
import queue
import threading
import logging

log = logging.getLogger(__name__)

_q: queue.Queue = queue.Queue()
_lock = threading.Lock()
_thread: threading.Thread | None = None


def submit(fn, *args) -> None:
    """Encola una tarea. Si no hay worker activo, lo arranca."""
    _q.put((fn, args))
    _ensure_worker()


def _ensure_worker() -> None:
    global _thread
    with _lock:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_loop, daemon=True, name="scraper-queue")
            _thread.start()


def _loop() -> None:
    while True:
        try:
            fn, args = _q.get(timeout=60)
            try:
                fn(*args)
            except Exception as exc:
                log.error("queue_worker_task_failed", extra={"error": str(exc)})
            finally:
                _q.task_done()
        except queue.Empty:
            break
