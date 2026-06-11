"""Paced synthetic run for watching the AGENTIQ factory live.

Writes a believable multi-agent story into the real run store, one event at a
time with delays, so the web view (``agentiq web``) can be watched growing in
real time. Pure store writes — no agents, no network, no cost.

Usage:
    python -m uv run python scripts/web_demo.py [--fast]
"""

from __future__ import annotations

import json
import sys
import time

from agentiq.core.decision import DecisionRequest, parse_choice
from agentiq.core.decision_bridge import answer_path, pending_path
from agentiq.core.run import start_run
from agentiq.replay.summary import write_summary

PACE = 0.4 if "--fast" in sys.argv else 1.6
ASK = "--ask" in sys.argv  # decision answered from the browser (file bridge)


def beat(run, type_: str, payload: dict, agent_id: str | None = None) -> None:
    run.writer.write(type_, payload, run_id=run.run_id, agent_id=agent_id)
    print(f"  -> {type_} {agent_id or ''}")
    time.sleep(PACE)


def main() -> None:
    run = start_run("Construir o módulo de pagamentos", project=".")
    print(f"demo run {run.run_id} — watch it at http://127.0.0.1:8642/?follow=1")
    time.sleep(PACE)

    beat(run, "agent.spawned", {"role": "orchestrator"}, "parent")
    beat(run, "vault.read", {"ref": "architecture"}, "parent")
    beat(run, "vault.read", {"ref": "payment-rules"}, "parent")

    # the factory grows: three workers, one at a time
    beat(run, "agent.spawned", {"role": "backend", "parent_id": "parent"}, "a1")
    beat(
        run, "task.delegated", {"task": "modelar entidades", "to_agent": "a1"}, "parent"
    )
    beat(
        run,
        "agent.usage",
        {"input_tokens": 1200, "output_tokens": 600, "cost_usd": 0.07},
        "a1",
    )

    beat(run, "agent.spawned", {"role": "api", "parent_id": "parent"}, "a2")
    beat(run, "task.delegated", {"task": "endpoints REST", "to_agent": "a2"}, "parent")
    beat(run, "vault.read", {"ref": "api-conventions"}, "a2")

    beat(run, "agent.spawned", {"role": "tests", "parent_id": "parent"}, "a3")
    beat(
        run, "task.delegated", {"task": "cobrir com testes", "to_agent": "a3"}, "parent"
    )
    beat(
        run,
        "agent.usage",
        {"input_tokens": 2000, "output_tokens": 900, "cost_usd": 0.11},
        "a2",
    )

    # a human decision pauses the world. With --ask, the answer comes from the
    # BROWSER through the file bridge (click an option in the decision card).
    options = ["stripe", "adyen", "pix-direto"]
    beat(
        run,
        "decision.pending",
        {
            "prompt": "Qual gateway de pagamento usar?",
            "options": options,
            "default": "stripe",
        },
        "parent",
    )
    if ASK:
        request = DecisionRequest(
            agent_id="parent",
            prompt="Qual gateway de pagamento usar?",
            options=options,
            default="stripe",
        )
        pending_path(run.root_dir).write_text(
            json.dumps(
                {
                    "agent_id": request.agent_id,
                    "prompt": request.prompt,
                    "options": options,
                    "default": request.default,
                }
            ),
            encoding="utf-8",
        )
        print("  .. aguardando resposta no browser (ate 180s)")
        choice, resolved_by = "stripe", "default"
        deadline = time.time() + 180
        try:
            while time.time() < deadline:
                if answer_path(run.root_dir).is_file():
                    raw = json.loads(
                        answer_path(run.root_dir).read_text(encoding="utf-8")
                    )
                    choice = parse_choice(request, str(raw.get("choice", "")))
                    resolved_by = "human"
                    break
                time.sleep(0.3)
        finally:
            pending_path(run.root_dir).unlink(missing_ok=True)
            answer_path(run.root_dir).unlink(missing_ok=True)
        beat(
            run,
            "decision.resolved",
            {"choice": choice, "resolved_by": resolved_by},
            "parent",
        )
    else:
        time.sleep(PACE * 2)
        beat(
            run,
            "decision.resolved",
            {"choice": "stripe", "resolved_by": "default"},
            "parent",
        )

    # one worker stumbles
    beat(run, "agent.failed", {"cause": "testes de contrato falharam"}, "a3")
    beat(run, "agent.spawned", {"role": "tests", "parent_id": "parent"}, "a4")
    beat(
        run, "task.delegated", {"task": "refazer contratos", "to_agent": "a4"}, "parent"
    )
    beat(
        run,
        "agent.usage",
        {"input_tokens": 1500, "output_tokens": 700, "cost_usd": 0.09},
        "a4",
    )
    beat(run, "vault.read", {"ref": "payment-rules"}, "a4")

    run.complete()
    write_summary(run.events_path, run.root_dir / "summary.json")
    print("demo run completed.")


if __name__ == "__main__":
    main()
