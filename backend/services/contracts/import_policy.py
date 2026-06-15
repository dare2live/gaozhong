"""Shared reader for import policy contracts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_PATH = ROOT / "backend" / "config" / "import_policies.yaml"


def load_import_policy(policy_name: str, policy_path: Path | None = None) -> dict[str, Any]:
    path = policy_path or DEFAULT_POLICY_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    policies = raw.get("policies") or {}
    if policy_name not in policies:
        known = ", ".join(sorted(policies))
        raise KeyError(f"unknown import policy {policy_name!r}; known={known}")
    return dict(policies[policy_name])
