---
id: conventions
title: Conventions & Dev Workflow
tags: [conventions, workflow, dev]
type: rule
---

# Conventions & Dev Workflow

**Run everything via uv (invoked as a module — uv is not on the bash PATH here):**
```
python -m uv run pytest
python -m uv run ruff check .
python -m uv run ruff format --check .
python -m uv run ty check
python -m uv run lint-imports
```
A story is "done" only when ALL five gates are green.

**Dependency rule (NFR17, import-linter contract):** `core`, `events`, `agent`,
`vault`, `policy`, `cost` MUST NOT import `tui`. Import direction is one-way toward
`events` (the event vocabulary is the only inter-module contract). `tui`/`cli` may
import inward; `cli` may import `tui`.

**Event vocabulary (`events/models.py`):** the frozen contract — extend only
ADDITIVELY (new event type or new optional payload field); update the reducer in
the same change. Event `type` is `lower.dotted` (`run.started`, `agent.spawned`,
`vault.read`, `decision.pending`/`resolved`, `agent.usage`, `budget.exceeded`).

**Naming:** PEP 8 (Ruff-enforced). Failures are EVENTS (`*.failed`), not exceptions
that escape the core. Secrets never logged. Live and replay share ONE reducer.

**BMad story flow:** create-story -> dev-story -> (code-review) -> next. Status in
`_bmad-output/implementation-artifacts/sprint-status.yaml`; stories live beside it.

See [[architecture]] and [[learnings]].
