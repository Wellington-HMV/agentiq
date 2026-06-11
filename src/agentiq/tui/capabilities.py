"""Terminal capability detection: representation tier, ASCII fallback, motion.

Pure `detect`/`choose_representation` (inputs in) plus a thin `from_environment`
wrapper. Colour tiers (truecolor→256→16→no-colour) are handled by Textual's own
renderer and `NO_COLOR`; the explicit, testable controls here are the size-based
representation tier, ASCII glyph fallback, and reduced motion.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass

# Representation breakpoints (UX-DR9), in terminal cells.
_FULL_COLS, _FULL_ROWS = 120, 40
_COMPACT_COLS, _COMPACT_ROWS = 80, 24


def choose_representation(cols: int, rows: int) -> str:
    """Pick the scene representation tier from terminal size."""
    if cols >= _FULL_COLS and rows >= _FULL_ROWS:
        return "full"
    if cols >= _COMPACT_COLS and rows >= _COMPACT_ROWS:
        return "compact"
    return "minimal"


@dataclass(frozen=True)
class Capabilities:
    representation: str  # "full" | "compact" | "minimal"
    ascii_only: bool
    reduced_motion: bool


def detect(
    cols: int,
    rows: int,
    *,
    unicode_ok: bool = True,
    ascii_only: bool = False,
    reduced_motion: bool = False,
) -> Capabilities:
    """Pure capability resolution from explicit inputs."""
    return Capabilities(
        representation=choose_representation(cols, rows),
        ascii_only=ascii_only or not unicode_ok,
        reduced_motion=reduced_motion,
    )


def _stdout_unicode_ok() -> bool:
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower()
    return "utf" in encoding


def from_environment(
    *, ascii_only: bool = False, reduced_motion: bool = False
) -> Capabilities:
    """Detect capabilities from the current terminal."""
    size = shutil.get_terminal_size((80, 24))
    return detect(
        size.columns,
        size.lines,
        unicode_ok=_stdout_unicode_ok(),
        ascii_only=ascii_only,
        reduced_motion=reduced_motion,
    )
