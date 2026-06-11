"""Tests for the event model (story 1.2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentiq.events.models import Event


def _evt(**kw: object) -> Event:
    base: dict[str, object] = {
        "seq": 0,
        "ts": "2026-06-09T12:00:00.000000Z",
        "run_id": "01J",
        "type": "run.started",
        "payload": {"goal": "do x", "project": "."},
    }
    base.update(kw)
    return Event.model_validate(base)


def test_valid_event_constructs() -> None:
    e = _evt()
    assert e.seq == 0
    assert e.type == "run.started"
    assert e.payload["goal"] == "do x"


def test_unknown_type_rejected() -> None:
    with pytest.raises(ValidationError):
        _evt(type="run.exploded")


def test_missing_required_payload_field_rejected() -> None:
    with pytest.raises(ValidationError):
        _evt(type="run.started", payload={"goal": "x"})  # missing project


def test_forward_compat_extra_payload_keys_tolerated() -> None:
    e = _evt(type="vault.read", payload={"ref": "api-design", "future_field": 7})
    # Extra key preserved in the dict, validation ignores it.
    assert e.payload["ref"] == "api-design"
    assert e.payload["future_field"] == 7


def test_json_line_round_trips() -> None:
    e = _evt(type="vault.read", payload={"ref": "auth"})
    line = e.to_json_line()
    assert "\n" not in line
    assert Event.model_validate_json(line) == e
