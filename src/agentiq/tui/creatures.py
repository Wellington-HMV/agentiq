"""Creature personalities (story 6.4).

The agents are little office creatures. This module gives them character — an
idle/active bob and a per-role personality tag — while keeping the cardinal rule:
**charm never costs legibility (UX-DR2)**. Every creature always leads with its
status glyph, which encodes the agent's real state unambiguously; personality only
adds a body that bobs while the agent is *active* (and stays still when it isn't,
so motion itself reads as "working") plus the role's initial.

`creature` is a pure function of `(AgentState, frame)`, so the same state always
renders the same face for a given frame — animation is just the frame advancing.
"""

from __future__ import annotations

from agentiq.replay.scene_state import AgentState, Status

# status -> (unicode glyph, ascii glyph). The glyph is authoritative: it is always
# present, so state is readable no matter the personality flourish.
_GLYPH: dict[str, tuple[str, str]] = {
    Status.IDLE: ("·", "."),
    Status.READING: ("◉", "o"),
    Status.THINKING: ("✺", "*"),
    Status.DELEGATING: ("➤", ">"),
    Status.WORKING: ("✦", "+"),
    Status.FAILED: ("✕", "x"),
    Status.DONE: ("✓", "v"),
}

# Statuses where the creature is busy → its body bobs (motion encodes activity).
_ACTIVE = {Status.READING, Status.THINKING, Status.DELEGATING, Status.WORKING}

_BOB = ("˄", "˅")  # unicode bob frames
_BOB_ASCII = ("^", "v")
_STILL = "–"
_STILL_ASCII = "-"


def status_glyph(status: str, *, ascii_only: bool = False) -> str:
    """The authoritative state glyph for a status (always shown)."""
    pair = _GLYPH.get(status, ("?", "?"))
    return pair[1] if ascii_only else pair[0]


def _body(status: str, frame: int, *, ascii_only: bool) -> str:
    if status in _ACTIVE:
        pair = _BOB_ASCII if ascii_only else _BOB
        return pair[frame % 2]  # bob while active
    return _STILL_ASCII if ascii_only else _STILL  # calm/terminal: no motion


def role_tag(role: str | None) -> str:
    """A one-character personality tag from the agent's role."""
    return (role or "?")[0]


def creature(agent: AgentState, frame: int = 0, *, ascii_only: bool = False) -> str:
    """Render an agent as a little creature: <state-glyph><body bob><role tag>.

    The state glyph is always first and never animates, so the real state stays
    legible; only the body bobs (and only while active) and the role tag adds flavor.
    """
    return (
        status_glyph(agent.status, ascii_only=ascii_only)
        + _body(agent.status, frame, ascii_only=ascii_only)
        + role_tag(agent.role)
    )
