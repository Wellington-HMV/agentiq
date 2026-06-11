"""Tests for secret scrubbing (story 1.6)."""

from __future__ import annotations

from agentiq.agent.scrub import collect_secrets, scrub


def test_masks_known_literal_in_nested_payload() -> None:
    secret = "supersecretvalue123"
    payload = {
        "note": f"used key {secret} here",
        "nested": {"items": [f"x {secret}", "clean"]},
        "count": 3,
    }
    out = scrub(payload, {secret})
    assert secret not in str(out)
    assert out["note"] == "used key *** here"
    assert out["nested"]["items"][0] == "x ***"
    assert out["nested"]["items"][1] == "clean"
    assert out["count"] == 3


def test_masks_api_key_pattern_without_known_literal() -> None:
    payload = {"text": "token sk-ant-AbC123_def-456 trailing"}
    out = scrub(payload, set())
    assert "sk-ant-" not in out["text"]
    assert "***" in out["text"]


def test_collect_secrets_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-zzz")
    secrets = collect_secrets()
    assert "sk-ant-zzz" in secrets


def test_masks_secret_used_as_dict_key() -> None:
    # A secret can appear as a key, not only a value (NFR9).
    secret = "supersecretvalue123"
    out = scrub({secret: "v", "clean": "sk-ant-AbC1_2"}, {secret})
    assert secret not in str(out)
    assert "sk-ant-" not in str(out)  # key + value patterns both masked
    assert out["***"] == "v"  # the secret key is masked
