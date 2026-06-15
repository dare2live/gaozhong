"""Shared primitives for project-architecture audit (finding type + path/contract helpers).

Split out of project_architecture.py to keep each module < 400 lines (Rule 8).
project_architecture.py (public API) and project_architecture_checks.py (section
validators) both import from here; this module imports nothing from either to avoid
circular imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ProjectArchitectureFinding:
    code: str
    severity: str
    target: str
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def _module_path(module_name: str) -> Path:
    return ROOT / Path(*module_name.split("."))


def _module_exists(module_name: str) -> bool:
    base = _module_path(module_name)
    return (base.with_suffix(".py")).exists() or (base / "__init__.py").exists()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _add_path_finding(
    findings: list[ProjectArchitectureFinding],
    *,
    code: str,
    target: str,
    path_text: str,
    expect_dir: bool | None = None,
) -> None:
    path = _resolve_path(path_text)
    if not path.exists():
        findings.append(ProjectArchitectureFinding(code, "BLOCK", target, path_text))
        return
    if expect_dir is True and not path.is_dir():
        findings.append(ProjectArchitectureFinding(f"{code}_not_directory", "BLOCK", target, path_text))
    if expect_dir is False and not path.is_file():
        findings.append(ProjectArchitectureFinding(f"{code}_not_file", "BLOCK", target, path_text))


def _require_mapping(
    findings: list[ProjectArchitectureFinding],
    contract: dict[str, Any],
    section: str,
) -> dict[str, Any]:
    value = contract.get(section)
    if not isinstance(value, dict) or not value:
        findings.append(
            ProjectArchitectureFinding(
                "architecture_section_missing_or_empty",
                "BLOCK",
                section,
                "section must be a non-empty mapping",
            )
        )
        return {}
    return value


def _require_list(
    findings: list[ProjectArchitectureFinding],
    contract: dict[str, Any],
    section: str,
) -> list[Any]:
    value = contract.get(section)
    if not isinstance(value, list) or not value:
        findings.append(
            ProjectArchitectureFinding(
                "architecture_section_missing_or_empty",
                "BLOCK",
                section,
                "section must be a non-empty list",
            )
        )
        return []
    return value


def _audit_owner_module(
    findings: list[ProjectArchitectureFinding],
    section: str,
    item_id: str,
    item: dict[str, Any],
) -> None:
    owner_module = item.get("owner_module")
    if owner_module and not _module_exists(str(owner_module)):
        findings.append(
            ProjectArchitectureFinding(
                "owner_module_missing",
                "BLOCK",
                f"{section}.{item_id}",
                str(owner_module),
            )
        )
