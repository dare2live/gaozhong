"""Shared source cross-check rule loader."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RULES_PATH = ROOT / "backend" / "config" / "source_crosscheck_rules.yaml"


def load_source_crosscheck_rules(path: Path | None = None) -> dict[str, Any]:
    source = path or DEFAULT_RULES_PATH
    return yaml.safe_load(source.read_text(encoding="utf-8")) or {}


def _normalize_groups(raw: dict[str, Any]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for group, tokens in raw.items():
        if tokens is None:
            continue
        if isinstance(tokens, (str, int, float)):
            groups[str(group)] = [str(tokens)]
        else:
            groups[str(group)] = [str(token) for token in tokens]
    return groups


def html_identity_rule_source_ids(path: Path | None = None) -> set[str]:
    rules = load_source_crosscheck_rules(path).get("html_identity") or {}
    return {str(source_id) for source_id in (rules.get("sources") or {})}


def html_identity_required_groups(source_id: str, path: Path | None = None) -> dict[str, list[str]]:
    rules = load_source_crosscheck_rules(path).get("html_identity") or {}
    groups = _normalize_groups(rules.get("default_required_groups") or {})
    source_rules = (rules.get("sources") or {}).get(source_id) or {}
    groups.update(_normalize_groups(source_rules.get("required_groups") or {}))
    return groups


def validate_html_identity_rules(
    *,
    known_source_ids: set[str] | None = None,
    path: Path | None = None,
) -> list[dict[str, str]]:
    rules = load_source_crosscheck_rules(path).get("html_identity") or {}
    findings: list[dict[str, str]] = []

    def add(code: str, target: str, detail: str) -> None:
        findings.append({"code": code, "target": target, "detail": detail})

    def check_groups(target: str, raw_groups: dict[str, Any]) -> None:
        if not isinstance(raw_groups, dict):
            add("html_identity_groups_not_mapping", target, "required_groups must be a mapping")
            return
        for group, tokens in raw_groups.items():
            group_name = str(group).strip()
            if not group_name:
                add("html_identity_group_name_empty", target, "group name cannot be empty")
            normalized = _normalize_groups({str(group): tokens}).get(str(group), [])
            if not normalized:
                add("html_identity_group_has_no_tokens", f"{target}:{group}", "group must define at least one token")
            for token in normalized:
                if not token.strip():
                    add("html_identity_group_has_empty_token", f"{target}:{group}", "tokens cannot be empty")

    check_groups("default_required_groups", rules.get("default_required_groups") or {})

    source_rules = rules.get("sources") or {}
    if not isinstance(source_rules, dict):
        add("html_identity_sources_not_mapping", "html_identity.sources", "sources must be a mapping")
        return findings

    for source_id, raw_source_rules in source_rules.items():
        source_key = str(source_id).strip()
        if not source_key:
            add("html_identity_source_id_empty", "html_identity.sources", "source id cannot be empty")
            continue
        if known_source_ids is not None and source_key not in known_source_ids:
            add("html_identity_rule_unknown_source", source_key, "rule references a source id not present in sources.yaml")
        if not isinstance(raw_source_rules, dict):
            add("html_identity_source_rule_not_mapping", source_key, "source rule must be a mapping")
            continue
        if "required_groups" not in raw_source_rules:
            add("html_identity_source_rule_missing_required_groups", source_key, "source rule must define required_groups")
            continue
        check_groups(source_key, raw_source_rules.get("required_groups") or {})

    return findings
