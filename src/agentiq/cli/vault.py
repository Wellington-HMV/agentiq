"""``agentiq vault validate|info`` — check and explore a vault outside a run."""

from __future__ import annotations

import argparse
import sys

from agentiq.core.exit_codes import ExitCode
from agentiq.vault.harness import HarnessVaultProvider
from agentiq.vault.provider import VaultError


def vault_command(args: argparse.Namespace) -> int:
    """Validate or summarize a harness vault. Read-only, pipeable, no TTY needed."""
    provider = HarnessVaultProvider(args.path)

    if args.vault_action == "validate":
        try:
            provider.validate()
        except VaultError as e:
            print(f"invalid: {e}", file=sys.stderr)
            return ExitCode.FAILED
        print(f"valid: {args.path}")
        return ExitCode.SUCCESS

    # info
    try:
        meta = provider.metadata()
        entries = provider.entries()
    except VaultError as e:
        print(f"invalid: {e}", file=sys.stderr)
        return ExitCode.FAILED

    print(f"vault: {meta['name']}  (schema {meta['schema_version']})")
    if meta.get("description"):
        print(f"  {meta['description']}")
    print(f"entries: {meta['entry_count']}")
    for entry in entries:
        tags = f"  [{', '.join(entry.tags)}]" if entry.tags else ""
        print(f"  {entry.id}  {entry.title}{tags}")
    return ExitCode.SUCCESS
