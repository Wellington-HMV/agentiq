"""Tests for the Textual app shell + token layer (story 2.5)."""

from __future__ import annotations

from textual.widgets import Footer

from agentiq.tui.app import WcsApp
from agentiq.tui.scene import SceneWidget
from agentiq.tui.tokens import glyph


async def test_app_composes_and_quits() -> None:
    app = WcsApp(app_title="test-run")
    async with app.run_test() as pilot:
        # Scene widget and footer are present (UX-DR8 persistent footer).
        assert app.query_one(SceneWidget)
        assert app.query_one(Footer)
        assert app.title == "test-run"
        # Quit binding works headlessly.
        await pilot.press("q")


def test_glyph_tokens_have_ascii_fallback() -> None:
    assert glyph("decision") == "◆"
    assert glyph("decision", ascii_only=True) == "D"
    assert glyph("failure", ascii_only=True) == "X"
    assert glyph("unknown") == "?"
