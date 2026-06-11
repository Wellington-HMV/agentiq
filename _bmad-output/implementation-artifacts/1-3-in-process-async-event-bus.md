# Story 1.3: In-process async event bus

Status: review

## Story

As a developer,
I want a non-blocking async pub/sub bus,
so that the core can emit events without ever waiting on a consumer (NFR2).

## Acceptance Criteria

1. **Given** the bus with one producer and multiple subscribers (bounded queues),
   **When** the core publishes an event, **Then** publish returns without awaiting
   any subscriber.
2. **Given** a slow or overflowing subscriber, **When** the producer keeps
   publishing, **Then** the subscriber does not back-pressure the producer.
3. **Given** an overflowed subscriber, **When** it needs the events it missed,
   **Then** it can resync from the JSONL log rather than losing events.
4. **Given** multiple subscribers, **When** events are published, **Then** each
   subscriber receives the events independently and in publish order.

## Tasks / Subtasks

- [x] Task 1: EventBus + Subscription (`events/bus.py`) (AC: #1, #2, #4)
  - [x] `Subscription`: bounded `asyncio.Queue[Event]` + `overflowed` flag + `last_seq`.
  - [x] `EventBus.subscribe(maxsize=...)` / `unsubscribe(sub)`.
  - [x] `EventBus.publish(event)` is a plain (non-async) method: `put_nowait` per
        sub; `QueueFull` → `overflowed = True` (never blocks/raises).
  - [x] `Subscription` async-iterable; `get()` advances `last_seq`.
- [x] Task 2: Resync-from-log helper (`events/bus.py`) (AC: #3)
  - [x] `resync_from_log(sub, log_path)` yields events with `seq > last_seq` from
        the JSONL log, advances `last_seq`, clears `overflowed`.
- [x] Task 3: Tests (`tests/events/test_bus.py`) (AC: all) — 4 async tests:
  - [x] Non-blocking publish with `maxsize=1` → overflow flagged, first event still readable.
  - [x] Slow consumer (nothing consuming) → 5 publishes all return, overflow flagged.
  - [x] Two subscribers receive events independently and in publish order.
  - [x] Resync after overflow yields exactly the missed events and clears overflow.

## Dev Notes

Builds on 1.2 (`events/models.py`, `events/reader.py`). Implements ONLY the async
bus + resync helper in `events/bus.py`. Do NOT implement run store (1.4),
adapter (1.6), orchestration, the TUI, or the cost meter — they are consumers
that arrive later.

**Architecture (from Core Architectural Decisions → Event Architecture):**
- In-process async pub/sub. The core is the SOLE producer; subscribers (JSONL
  writer, cost meter, TUI, replay) consume independently.
- Publish is non-blocking with bounded per-subscriber queues. A slow/overflowing
  subscriber must NOT back-pressure the producer (NFR2) — on overflow it drops to
  a "catch up from log" path (the JSONL log is the source of truth).
- The log (1.2) is authoritative; the bus is a live fan-out convenience. This is
  why an overflowed subscriber can always recover via `resync_from_log`.

**Why publish is a plain `def`, not `async def`:** making it synchronous is the
strongest guarantee it cannot await a consumer. The async core calls
`bus.publish(event)` inline; delivery to consumers happens via their own queue
reads. (In 1.x the 1.2 writer remains the synchronous source-of-truth writer; the
bus feeds the *other*, async consumers.)

**Patterns:** `asyncio` only; classes `PascalCase` (`EventBus`, `Subscription`);
no blocking calls in async paths; `events/` must not import `tui` (import-linter).
Keep `Subscription` cheap and independent — one queue per subscriber, no shared
mutable cursor.

### Project Structure Notes

- New file: `src/well_corp_sw/events/bus.py`. Tests: `tests/events/test_bus.py`.
- Reuses `read_events` from `events/reader.py` for resync.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Event Architecture (Data Architecture, adapted)] — in-process async pub/sub, bounded queues, non-blocking publish, resync-from-log on overflow.
- [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements] — NFR2 (core never blocks on render/consumer), NFR17 (separable modules via event bus).
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3: In-process async event bus] — acceptance criteria.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story workflow

### Debug Log References

- Gates (via `python -m uv run`): pytest 21 passed (4 cli + 17 events, incl 4 bus);
  ruff check + format clean; ty check clean; lint-imports KEPT.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented ONLY `events/bus.py` (EventBus, Subscription, resync_from_log). No
  consumers (cost meter/TUI), run store, adapter, or orchestration — scope held.
- `publish` is deliberately a plain `def` (not `async`) — strongest guarantee it
  never awaits a consumer (NFR2). On `QueueFull` it flags `overflowed` rather than
  blocking, losing silently, or raising.
- Resync ties to story 1.2: an overflowed subscriber recovers missed events from
  the authoritative JSONL log via `resync_from_log` (reuses `read_events`).
- `events/bus.py` imports only `events.models` + `events.reader` — no tui/cross-boundary.
- All 4 ACs satisfied; status → review.

### File List

- src/well_corp_sw/events/bus.py (new)
- tests/events/test_bus.py (new)

### Change Log

- 2026-06-09: Implemented story 1.3 — in-process async pub/sub EventBus with
  bounded per-subscriber queues, non-blocking synchronous publish, overflow
  flagging, and resync-from-log recovery. 4 async tests. All ACs satisfied;
  status → review.
