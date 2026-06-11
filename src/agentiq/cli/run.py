"""``agentiq run`` — start a headless orchestration run."""

from __future__ import annotations

import argparse
import asyncio
import sys

from agentiq.config.settings import (
    ConfigError,
    Settings,
    find_config,
    load_config,
)
from agentiq.core.exit_codes import status_to_exit_code
from agentiq.core.orchestrator import (
    DeterministicStrategy,
    OrchestrationStrategy,
    run_orchestration,
)
from agentiq.policy.policy import PolicyResolver
from agentiq.vault.harness import HarnessVaultProvider
from agentiq.vault.provider import VaultProvider


def _load_settings(args: argparse.Namespace) -> Settings:
    cfg_path = find_config(".")
    return load_config(cfg_path) if cfg_path is not None else Settings()


def _resolve_project(args: argparse.Namespace, settings: Settings) -> str:
    """Project precedence: --project flag > config file > current dir."""
    if args.project is not None:
        return str(args.project)
    return settings.project.path


def _resolve_vault(settings: Settings) -> VaultProvider | None:
    """Use the first configured vault path, if any."""
    if settings.vault.paths:
        return HarnessVaultProvider(settings.vault.paths[0])
    return None


def _resolve_strategy(
    args: argparse.Namespace, settings: Settings, project: str
) -> OrchestrationStrategy:
    """`--live` drives real Claude agents (ANTHROPIC_API_KEY); else deterministic.

    The live strategy carries the cost ceiling and a safety guard (scope + denied
    ops) from config, so the SDK loop meters spend and confines tool actions.
    """
    if getattr(args, "live", False):
        from agentiq.agent.claude_strategy import ClaudeStrategy
        from agentiq.policy.safety import SafetyGuard

        guard = SafetyGuard(
            project,
            vault_paths=settings.vault.paths,
            denied_ops=settings.safety.denied_ops,
        )
        return ClaudeStrategy(cost_ceiling_usd=settings.cost.ceiling_usd, safety=guard)
    return DeterministicStrategy()


def run_command(args: argparse.Namespace) -> int:
    """Execute a run (headless, or live with --watch on a TTY)."""
    try:
        settings = _load_settings(args)
    except ConfigError as e:
        print(str(e), file=sys.stderr)
        return status_to_exit_code("aborted")
    project = _resolve_project(args, settings)
    vault = _resolve_vault(settings)
    strategy = _resolve_strategy(args, settings, project)

    if getattr(args, "watch", False) and sys.stdout.isatty():
        from agentiq.tui.live import LiveWatchApp

        LiveWatchApp(
            args.goal, project, strategy=strategy, autonomy=settings.autonomy
        ).run()
        return status_to_exit_code("completed")

    # `--web`: serve the factory view, open the browser on this run, and route
    # `ask` decisions to it (FileDecisionResolver). Otherwise headless: `ask`
    # has no human, so PolicyResolver raises -> abort rather than hang (NFR8).
    run_id: str | None = None
    ask_resolver = None
    if getattr(args, "web", False):
        import threading

        from agentiq.cli.web import DEFAULT_PORT
        from agentiq.core.decision_bridge import FileDecisionResolver
        from agentiq.core.ids import new_ulid
        from agentiq.core.run import default_runs_root

        run_id = new_ulid()
        ask_resolver = FileDecisionResolver(default_runs_root() / run_id)

        def _serve() -> None:
            import uvicorn

            from agentiq.web.server import create_app

            uvicorn.run(
                create_app(), host="127.0.0.1", port=DEFAULT_PORT, log_level="error"
            )

        threading.Thread(target=_serve, daemon=True).start()
        import webbrowser

        webbrowser.open(f"http://127.0.0.1:{DEFAULT_PORT}/?run={run_id}&live=1")

    resolver = PolicyResolver(settings.autonomy, ask_resolver)
    run = asyncio.run(
        run_orchestration(
            args.goal,
            project,
            strategy=strategy,
            vault=vault,
            run_id=run_id,
            resolver=resolver,
            isolation_mode=settings.isolation.mode,
        )
    )
    print(f"run {run.run_id} {run.status} ({run.root_dir})")
    return status_to_exit_code(run.status)
