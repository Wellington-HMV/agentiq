# agentiq

A personal CLI/TUI tool for a solo developer to orchestrate Claude multi-agent
work across their own projects. Hand off a goal; agents (parent → subagents)
self-organize, consult harness-standard knowledge vaults, decide autonomously,
and run headless. Afterwards (or live) review everything as a **legible replay**
rendered as a living spatial scene — library (vault), desks (thinking), paths
(delegation). Reliable autonomy + legible replay is the product.

> Status: early development. This is the project scaffold (story 1.1). The
> orchestration core, replay, vaults, and TUI land in subsequent stories.

## Requirements

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) (package manager / runner)

## Dev quickstart

```bash
uv sync                       # create venv + install deps from the lockfile
uv run agentiq --version          # smoke test the CLI
uv run agentiq --help

# quality gates (must all pass)
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run lint-imports
uv run pytest
```

## Architecture (one-liner)

An event-sourced core: the headless orchestrator is the sole producer of an
append-only JSONL event log; everything else (replay, TUI, cost meter) is a pure
subscriber. The core never blocks on or imports the render layer. See
`_bmad-output/planning-artifacts/` for the full PRD, architecture, UX spec, and
epics.
