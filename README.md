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

## Interface Web (Fábrica)

```bash
uv run agentiq web                # sobe a fábrica em http://127.0.0.1:8642/ e abre o browser
uv run agentiq web --port 9000    # porta customizada
uv run agentiq web --no-browser   # não abre o browser automaticamente
```

- **Nova demanda**: clique em `+ nova demanda`, descreva o objetivo, informe o
  repositório alvo (vazio = diretório atual) e marque `agentes reais (Claude)`
  para usar agentes de verdade — desmarcado, roda a estratégia determinística
  offline. `▶ iniciar demanda` cria o run e já abre a visão ao vivo.
- **Modo LIVE**: runs em execução são acompanhados em tempo real via WebSocket —
  o pill `● LIVE · N events` indica o streaming; ao terminar vira `■ finished`.
  Clicar num run `running`/`pending` na sidebar também entra em LIVE.
- **Modo cinema**: clicar num run finalizado reproduz o log de eventos em ritmo
  natural (`▶ reprise`). `Espaço` pausa/retoma.
- **Decisões pendentes**: em LIVE, um card `◆ DECISION` aparece com as opções.
  Responda clicando numa opção, com `1`–`9`, ou `Enter` para o default.

## Architecture (one-liner)

An event-sourced core: the headless orchestrator is the sole producer of an
append-only JSONL event log; everything else (replay, TUI, cost meter) is a pure
subscriber. The core never blocks on or imports the render layer. See
`_bmad-output/planning-artifacts/` for the full PRD, architecture, UX spec, and
epics.
