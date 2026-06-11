"""Secret scrubbing at the agent boundary.

Runs on every event payload before it is written to the log or published, so no
API credential ever reaches the event log, the run summary, or a vault (NFR9).
Masks exact secret literals (from the environment) and the ``sk-ant-…`` API-key
pattern.
"""

from __future__ import annotations

import os
import re
from typing import Any

_MASK = "***"
# Anthropic API keys look like ``sk-ant-...``; redact any such token.
_API_KEY_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9_-]+")

# Environment variables whose *values* are secrets (we never log the value).
_SECRET_ENV_VARS = ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY")


def collect_secrets() -> set[str]:
    """Gather secret literal values from the environment."""
    return {value for name in _SECRET_ENV_VARS if (value := os.environ.get(name))}


def _scrub_text(text: str, secrets: set[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, _MASK)
    return _API_KEY_PATTERN.sub(_MASK, text)


def scrub(value: Any, secrets: set[str]) -> Any:
    """Recursively mask secrets in a payload (dict/list/str); other scalars pass."""
    if isinstance(value, str):
        return _scrub_text(value, secrets)
    if isinstance(value, dict):
        # Scrub keys too — a secret can appear as a key, not just a value (NFR9).
        return {scrub(k, secrets): scrub(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v, secrets) for v in value]
    return value
