"""Per-project configuration: ``agentiq.config.toml`` → typed settings + CLI overrides.

Precedence is CLI > file > defaults. Invalid config fails fast with a specific
message (which key/section/type is wrong) rather than a bare stack trace. The
full autonomy policy rule engine is story 4.2; here ``autonomy.default`` is the
only policy field that must parse.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

CONFIG_FILENAME = "agentiq.config.toml"
LEGACY_CONFIG_FILENAME = "wcs.config.toml"  # pre-rebrand name, still honored

AutonomyAction = Literal["allow", "deny", "ask"]
IsolationMode = Literal["serialize", "worktree"]


class ConfigError(Exception):
    """Raised when configuration is missing, malformed, or invalid."""


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectSection(_Section):
    path: str = "."


class VaultSection(_Section):
    paths: list[str] = []


class AutonomyRule(_Section):
    kind: str
    action: AutonomyAction


class AutonomySection(_Section):
    default: AutonomyAction = "ask"
    rules: list[AutonomyRule] = []


class CostSection(_Section):
    ceiling_usd: float | None = None


class IsolationSection(_Section):
    mode: IsolationMode = "serialize"


class SafetySection(_Section):
    denied_ops: list[str] = []


class Settings(_Section):
    """The full, typed per-project configuration."""

    project: ProjectSection = ProjectSection()
    vault: VaultSection = VaultSection()
    autonomy: AutonomySection = AutonomySection()
    cost: CostSection = CostSection()
    isolation: IsolationSection = IsolationSection()
    safety: SafetySection = SafetySection()


def find_config(project_root: str | Path) -> Path | None:
    """Return the path to ``agentiq.config.toml`` under ``project_root``, or None.

    Falls back to the legacy ``wcs.config.toml`` so pre-rebrand projects keep
    working unchanged.
    """
    root = Path(project_root)
    for name in (CONFIG_FILENAME, LEGACY_CONFIG_FILENAME):
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def load_config(path: str | Path) -> Settings:
    """Load and validate config from a TOML file. Fails fast with ConfigError."""
    p = Path(path)
    try:
        data = tomllib.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ConfigError(f"config file not found: {p}") from e
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"invalid TOML in {p}: {e}") from e
    except UnicodeDecodeError as e:
        raise ConfigError(f"config file is not valid UTF-8: {p}") from e
    except OSError as e:  # permission denied, is-a-directory, etc.
        raise ConfigError(f"cannot read config file {p}: {e}") from e

    try:
        return Settings.model_validate(data)
    except ValidationError as e:
        raise ConfigError(f"invalid config in {p}: {e}") from e


def apply_cli_overrides(
    settings: Settings,
    *,
    project: str | None = None,
    vault_paths: list[str] | None = None,
    cost_ceiling_usd: float | None = None,
    isolation: IsolationMode | None = None,
) -> Settings:
    """Return a copy of ``settings`` with non-None CLI values applied (CLI > file)."""
    updated = settings.model_copy(deep=True)
    if project is not None:
        updated.project.path = project
    if vault_paths is not None:
        updated.vault.paths = list(vault_paths)
    if cost_ceiling_usd is not None:
        updated.cost.ceiling_usd = cost_ceiling_usd
    if isolation is not None:
        updated.isolation.mode = isolation
    return updated
