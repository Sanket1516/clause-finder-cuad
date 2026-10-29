"""Logging and timing helpers (stdlib only)."""
import logging
import sys
import time
from contextlib import contextmanager
from pathlib import Path


def get_logger(name: str = "contract_intel", log_file: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    log = logging.getLogger(name)
    if not log.handlers:
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(fmt)
        log.addHandler(h)
        log.setLevel(level)
        log.propagate = False
    if log_file is not None and not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(Path(log_file).resolve())
                                        for h in log.handlers):
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        log.addHandler(fh)
    return log


@contextmanager
def timed(bucket: dict, key: str):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        bucket[key] = round((time.perf_counter() - t0) * 1000, 3)
