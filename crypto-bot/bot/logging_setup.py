"""Logging configuration: human-readable console + a rolling file log."""
from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(state_dir: str, level: int = logging.INFO) -> None:
    Path(state_dir).mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(console)

    fileh = logging.FileHandler(Path(state_dir) / "bot.log")
    fileh.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(fileh)
