"""Central visual token layer for the TUI (UX-DR7).

All glyphs/markers live here with ASCII fallbacks so terminals without wide
Unicode still render meaning. The scene (2.6) and transport bar (2.7) consume
these — one source of truth. The `◆`/`✕`/`▶` glyphs are the TUI's; the plain
timeline (2.2) uses ASCII `D`/`F` instead.
"""

from __future__ import annotations

# Unicode glyph tokens.
GLYPHS: dict[str, str] = {
    "decision": "◆",
    "failure": "✕",
    "playhead": "▶",
    "library": "📚",
    "desk": "▔",
    "done": "✓",
    "agent": "●",
}

# ASCII fallbacks (terminals without wide-Unicode).
ASCII_FALLBACK: dict[str, str] = {
    "decision": "D",
    "failure": "X",
    "playhead": ">",
    "library": "[lib]",
    "desk": "_",
    "done": "v",
    "agent": "o",
}

# Semantic color-role names — the vocabulary TCSS classes map to. Colour is always
# paired with a glyph/label (never colour-only) so meaning survives no-colour modes.
COLOR_ROLES: tuple[str, ...] = (
    "bg",
    "surface",
    "text",
    "text-dim",
    "accent",  # reserved for pending decisions
    "success",
    "warning",
    "error",
    "zone",
)


def glyph(name: str, *, ascii_only: bool = False) -> str:
    """Return a glyph token, or its ASCII fallback when ``ascii_only``."""
    if ascii_only:
        return ASCII_FALLBACK.get(name, "?")
    return GLYPHS.get(name, "?")
