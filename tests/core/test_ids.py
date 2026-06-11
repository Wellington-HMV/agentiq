"""Tests for sortable ULID generation (story 1.4)."""

from __future__ import annotations

from agentiq.core.ids import new_ulid


def test_ulid_length() -> None:
    assert len(new_ulid()) == 26


def test_ulid_sorts_by_time() -> None:
    earlier = new_ulid(timestamp_ms=1, randomness=0)
    later = new_ulid(timestamp_ms=2, randomness=0)
    assert earlier < later


def test_ulid_uses_crockford_alphabet() -> None:
    allowed = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    assert set(new_ulid()) <= allowed
