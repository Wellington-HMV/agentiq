# agentiq Exit Codes

Deterministic exit codes for non-interactive / scripted use (NFR8). Kept in sync
with `src/agentiq/core/exit_codes.py`.

| Code | Name            | Meaning |
|------|-----------------|---------|
| 0    | SUCCESS         | Run completed successfully |
| 1    | FAILED          | Run aborted / failed (terminal `run.aborted`) |
| 2    | USAGE           | Invalid command-line usage (argparse) |
| 3    | BLOCKED         | Run blocked on an unresolved decision (reserved — Epic 4) |
| 4    | BUDGET_EXCEEDED | Cost ceiling hit; fan-out halted (reserved — Epic 4) |

A finished run's status maps to a code via `status_to_exit_code`:
`completed → 0`, `aborted → 1`, `blocked → 3`, `budget_exceeded → 4`,
any other → 1. Headless runs always terminate with one of these codes — they
never hang waiting on input.
