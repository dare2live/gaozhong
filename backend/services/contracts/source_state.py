"""Shared reader and matcher for source-state contracts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_STATES_PATH = ROOT / "backend" / "config" / "source_states.yaml"


def load_source_state_contract(path: Path | None = None) -> dict[str, Any]:
    source = path or DEFAULT_SOURCE_STATES_PATH
    return yaml.safe_load(source.read_text(encoding="utf-8")) or {}


def _states(path: Path | None = None) -> dict[str, dict[str, Any]]:
    return dict((load_source_state_contract(path).get("states") or {}))


def _non_importable_states(path: Path | None = None) -> dict[str, dict[str, Any]]:
    return dict((load_source_state_contract(path).get("non_importable_states") or {}))


def known_source_state_tokens(path: Path | None = None) -> set[str]:
    return set(_states(path)) | set(_non_importable_states(path))


def match_source_state(status: str, path: Path | None = None) -> str | None:
    normalized = str(status or "").lower()
    if not normalized:
        return None
    for token in sorted(known_source_state_tokens(path), key=len, reverse=True):
        if normalized == token or normalized.startswith(f"{token}_"):
            return token
    return None


def canonical_state_token(token: str, path: Path | None = None) -> str | None:
    states = _states(path)
    if token in states:
        return str(states[token].get("alias_of") or token)
    if token in _non_importable_states(path):
        return token
    return None


def state_rank(token: str, path: Path | None = None) -> int | None:
    states = _states(path)
    canonical = canonical_state_token(token, path)
    if canonical and canonical in states:
        return int(states[canonical].get("rank") or 0)
    return None


def source_state_satisfies(status: str, required: str, path: Path | None = None) -> bool:
    actual_token = match_source_state(status, path)
    required_token = canonical_state_token(required, path)
    if not actual_token or not required_token:
        return False

    actual_canonical = canonical_state_token(actual_token, path)
    if required_token == "import_ready":
        return actual_canonical == "import_ready"

    actual_rank = state_rank(actual_token, path)
    required_rank = state_rank(required_token, path)
    if actual_rank is None or required_rank is None:
        return False
    return actual_rank >= required_rank
