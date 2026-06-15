"""Load the project architecture control-plane contract."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "backend" / "config" / "project_architecture.yaml"

REQUIRED_MAPPING_SECTIONS = (
    "instruction_sources",
    "truth_sources",
    "sibling_projects",
    "module_contracts",
    "data_zones",
    "config_contracts",
    "documentation_authority",
    "gate_contracts",
    "legacy_policy_lints",
)
REQUIRED_LIST_SECTIONS = ("architecture_rules",)


def load_project_architecture(config_path: Path | None = None) -> dict[str, Any]:
    """Return the raw architecture contract.

    Shape validation belongs to the read-only audit so callers can get a full
    finding list instead of failing fast on the first missing section.
    """
    path = config_path or DEFAULT_CONFIG
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"project architecture config must be a mapping: {path}")
    return raw
