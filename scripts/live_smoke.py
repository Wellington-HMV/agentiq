"""Live smoke test for the Claude SDK strategy (manual; needs ANTHROPIC_API_KEY).

Spends real tokens — never wired into CI. Two modes:

    python scripts/live_smoke.py            # run a tiny goal end-to-end through
                                            # the orchestration; report the log
    python scripts/live_smoke.py --dump     # print RAW SDK message shapes, for
                                            # calibrating the translation layer

See docs/live-calibration.md for how to read --dump output and what to adjust in
`agent/claude_strategy.py`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path


def _auth_note() -> None:
    """Report which auth path the SDK will use (it drives the Claude Code CLI)."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "auth: ANTHROPIC_API_KEY set (external API key / credits).",
            file=sys.stderr,
        )
    else:
        print(
            "auth: no ANTHROPIC_API_KEY - using Claude Code CLI login (subscription).",
            file=sys.stderr,
        )


def _attrs(obj: object) -> list[str]:
    return sorted(getattr(obj, "__dict__", {}) or {})


async def _dump(goal: str) -> int:
    """Print the raw SDK message/block shapes — the ground truth to calibrate to."""
    import claude_agent_sdk as sdk

    opts = sdk.ClaudeAgentOptions(
        system_prompt="Decompose the goal and delegate subtasks via the Task tool.",
        allowed_tools=["Task"],
    )
    count = 0
    try:
        async for msg in sdk.query(prompt=goal, options=opts):
            count += 1
            print(f"[{count}] {type(msg).__name__}: attrs={_attrs(msg)}")
            if type(msg).__name__ == "ResultMessage":
                for field in ("subtype", "is_error", "total_cost_usd", "stop_reason"):
                    print(f"      {field}={getattr(msg, field, '<none>')!r}")
                print(f"      result={str(getattr(msg, 'result', ''))[:80]!r}")
            for block in getattr(msg, "content", None) or []:
                line = f"      block {type(block).__name__}: attrs={_attrs(block)}"
                if type(block).__name__ == "ToolUseBlock":
                    inp = getattr(block, "input", {}) or {}
                    line += (
                        f"  name={getattr(block, 'name', None)!r}"
                        f"  id={getattr(block, 'id', None)!r}"
                        f"  input_keys={sorted(inp)}"
                    )
                print(line)
    except Exception as e:  # noqa: BLE001 - the SDK may raise on stream teardown
        print(f"\n(SDK raised after {count} messages: {type(e).__name__}: {e})")
    print(f"\n{count} messages total.")
    return 0


class _DenyResolver:
    """Cancels every confirm — proves the safety gate actually blocks tools."""

    async def resolve(self, request: object) -> tuple[str, str]:
        return "cancel", "human"


async def _run(goal: str, ceiling: float | None, guard: bool) -> int:
    """Run the full orchestration live and report what the translation produced."""
    from agentiq.agent.claude_strategy import ClaudeStrategy
    from agentiq.core.orchestrator import run_orchestration
    from agentiq.events.reader import read_events
    from agentiq.policy.safety import SafetyGuard

    # --guard demo: confine to cwd + hard-block Bash (disallowed_tools), and deny
    # every confirm. Bash is refused by the CLI regardless; other irreversible
    # tools are gated by the deny resolver when the CLI consults can_use_tool.
    safety = SafetyGuard(".", denied_ops=["Bash"]) if guard else None
    resolver = _DenyResolver() if guard else None
    with tempfile.TemporaryDirectory() as tmp:
        run = await run_orchestration(
            goal,
            ".",
            strategy=ClaudeStrategy(cost_ceiling_usd=ceiling, safety=safety),
            runs_root=Path(tmp) / "runs",
            resolver=resolver,
        )
        events = list(read_events(run.events_path))

    hist = Counter(e.type for e in events)
    cost = sum(
        float(e.payload.get("cost_usd", 0.0)) for e in events if e.type == "agent.usage"
    )
    spawned = [e.agent_id for e in events if e.type == "agent.spawned"]
    print(f"run {run.run_id} -> {run.status}")
    aborted = [e for e in events if e.type == "run.aborted"]
    if aborted:
        print(f"abort reason: {aborted[0].payload.get('reason')}")
    print(f"events:  {dict(hist)}")
    print(f"cost_usd: {cost:.4f}")
    print(f"spawned:  {spawned}")

    ok = (
        bool(events)
        and events[0].type == "run.started"
        and events[-1].type
        in (
            "run.completed",
            "run.aborted",
        )
    )
    print("SMOKE OK" if ok else "SMOKE FAIL")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live smoke test for ClaudeStrategy.")
    parser.add_argument("--goal", default="Say hello, then stop. Do not delegate.")
    parser.add_argument(
        "--dump", action="store_true", help="print raw SDK message shapes"
    )
    parser.add_argument(
        "--ceiling", type=float, default=0.50, help="cost ceiling in USD"
    )
    parser.add_argument(
        "--guard",
        action="store_true",
        help="enable the SafetyGuard + a deny resolver (proves tools are blocked)",
    )
    args = parser.parse_args(argv)
    _auth_note()
    if args.dump:
        return asyncio.run(_dump(args.goal))
    return asyncio.run(_run(args.goal, args.ceiling, args.guard))


if __name__ == "__main__":
    raise SystemExit(main())
