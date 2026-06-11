"""Replay transport engine — play/pause, step, seek over a run's events.

Precomputes one ``SceneState`` per index on construction so seeking to any point
is O(1) with no recomputation lag (FR16); this is safe because the reducer is
pure (story 2.1). This is the model only — the visual transport bar and key
bindings are story 2.7; jump-to-marker is story 2.4. The engine holds the
``playing``/``speed`` state the UI clock reads; it runs no timer itself.
"""

from __future__ import annotations

from agentiq.events.models import Event
from agentiq.replay.markers import is_decision, is_failure
from agentiq.replay.reducer import reduce
from agentiq.replay.scene_state import SceneState, initial_state

_MIN_SPEED = 0.25
_MAX_SPEED = 8.0


class ReplayController:
    """Cursor over a run's events with O(1) seek to any precomputed scene state."""

    def __init__(self, events: list[Event]) -> None:
        self._events = list(events)
        self._states: list[SceneState] = []
        state = initial_state()
        for event in self._events:
            state = reduce(state, event)
            self._states.append(state)
        self._decision_indices = [
            i for i, e in enumerate(self._events) if is_decision(e.type)
        ]
        self._failure_indices = [
            i for i, e in enumerate(self._events) if is_failure(e.type)
        ]
        self._pos = 0 if self._events else -1
        self.playing = False
        self.speed = 1.0

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def decision_indices(self) -> list[int]:
        return list(self._decision_indices)

    @property
    def failure_indices(self) -> list[int]:
        return list(self._failure_indices)

    # --- position -----------------------------------------------------------
    @property
    def position(self) -> int:
        return self._pos

    @property
    def last_index(self) -> int:
        return len(self._events) - 1

    @property
    def current_event(self) -> Event | None:
        if self._pos < 0:
            return None
        return self._events[self._pos]

    @property
    def current_state(self) -> SceneState:
        if self._pos < 0:
            return initial_state()
        return self._states[self._pos]

    @property
    def at_start(self) -> bool:
        return self._pos <= 0

    @property
    def at_end(self) -> bool:
        return self._pos == self.last_index or self._pos < 0

    def seek(self, index: int) -> None:
        if not self._events:
            return
        self._pos = max(0, min(index, self.last_index))

    def seek_to_seq(self, seq: int) -> bool:
        for i, event in enumerate(self._events):
            if event.seq == seq:
                self._pos = i
                return True
        return False

    def step_forward(self) -> None:
        self.seek(self._pos + 1)

    def step_backward(self) -> None:
        self.seek(self._pos - 1)

    def to_start(self) -> None:
        self.seek(0)

    def to_end(self) -> None:
        self.seek(self.last_index)

    # --- marker navigation (story 2.4) --------------------------------------
    @property
    def last_good_index(self) -> int:
        """Index just before the current event (clamped) — the last-good state."""
        return max(0, self._pos - 1)

    def _jump_next(self, indices: list[int]) -> bool:
        for i in indices:
            if i > self._pos:
                self._pos = i
                return True
        return False

    def _jump_prev(self, indices: list[int]) -> bool:
        for i in reversed(indices):
            if i < self._pos:
                self._pos = i
                return True
        return False

    def next_decision(self) -> bool:
        return self._jump_next(self._decision_indices)

    def prev_decision(self) -> bool:
        return self._jump_prev(self._decision_indices)

    def next_failure(self) -> bool:
        return self._jump_next(self._failure_indices)

    def prev_failure(self) -> bool:
        return self._jump_prev(self._failure_indices)

    # --- playback -----------------------------------------------------------
    def play(self) -> None:
        self.playing = True

    def pause(self) -> None:
        self.playing = False

    def toggle_play(self) -> None:
        self.playing = not self.playing

    def faster(self) -> None:
        self.speed = min(self.speed * 2, _MAX_SPEED)

    def slower(self) -> None:
        self.speed = max(self.speed / 2, _MIN_SPEED)
