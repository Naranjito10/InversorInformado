"""Scheduler: ejecuta el ciclo de scraping cada N minutos."""
from __future__ import annotations

import signal
import sys
import time

from .config import config
from .logger import get_logger
from .runner import run_cycle

log = get_logger("scheduler")


def _run_safely() -> None:
    try:
        run_cycle()
    except Exception as exc:  # noqa: BLE001
        log.error("cycle_unhandled_error", extra={"error": str(exc)}, exc_info=True)


def start() -> None:
    """Arranca el scheduler con APScheduler. Bloquea hasta SIGINT/SIGTERM."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError:
        log.error("apscheduler_not_installed_running_loop_fallback")
        _loop_fallback()
        return

    interval = config.scraper.interval_minutes
    log.info("scheduler_start", extra={"interval_minutes": interval})

    sched = BlockingScheduler(timezone="UTC")
    # Primer run inmediato
    sched.add_job(_run_safely, "interval", minutes=interval, next_run_time=None)

    # Run inmediato al arrancar
    sched.add_job(_run_safely, "date", id="initial_run")

    def shutdown(signum, frame):  # noqa: ARG001
        log.info("scheduler_stop")
        sched.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("scheduler_interrupted")


def _loop_fallback() -> None:
    """Loop simple si APScheduler no esta disponible."""
    interval = config.scraper.interval_minutes * 60
    log.info("loop_fallback_start", extra={"interval_seconds": interval})
    while True:
        _run_safely()
        log.info("loop_sleep", extra={"seconds": interval})
        time.sleep(interval)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        log.info("running_once")
        _run_safely()
    else:
        start()
