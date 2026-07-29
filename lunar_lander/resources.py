"""Locate bundled data files in source checkouts and frozen builds."""

import sys
from pathlib import Path


def resource_path(relative: str) -> str:
    """Return the absolute path to a data file under the lunar_lander package."""
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "lunar_lander"
    else:
        base = Path(__file__).resolve().parent
    return str(base / relative)
