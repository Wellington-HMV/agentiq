"""Sortable ULID generation (no external dependency).

128 bits = 48-bit millisecond timestamp (high) + 80-bit randomness (low),
encoded as 26 Crockford base32 chars. Lexicographic string order tracks time,
so run ids sort chronologically — which is how ``agentiq runs`` orders runs without
a database. Timestamp and randomness are injectable for deterministic tests.
"""

from __future__ import annotations

import os
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ULID_LEN = 26


def new_ulid(timestamp_ms: int | None = None, randomness: int | None = None) -> str:
    """Return a 26-char Crockford base32 ULID."""
    if timestamp_ms is None:
        timestamp_ms = int(time.time() * 1000)
    if randomness is None:
        randomness = int.from_bytes(os.urandom(10), "big")

    value = ((timestamp_ms & ((1 << 48) - 1)) << 80) | (randomness & ((1 << 80) - 1))
    chars = []
    for _ in range(_ULID_LEN):
        chars.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))
