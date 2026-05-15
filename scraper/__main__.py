"""Permite `python -m scraper.scheduler [once]`."""
import sys
from .scheduler import _run_safely, start

if len(sys.argv) > 1 and sys.argv[1] == "once":
    _run_safely()
else:
    start()
