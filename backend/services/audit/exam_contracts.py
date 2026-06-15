"""Read-only exam paper contract audit."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = ROOT / "data" / "db" / "gaozhong.duckdb"
DEFAULT_CONTRACTS = ROOT / "backend" / "config" / "exam_paper_contracts.yaml"


@dataclass(frozen=True)
class YearContractResult:
    year: int
    expected_min_rows: int
    db_rows_matching_paper: int
    db_rows_any_paper: int
    current_status: str
    status: str
    findings: list[str]
    known_gaps: list[str]
    current_known_sources: list[str]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _norm(value: str) -> str:
    return "".join(str(value or "").split()).lower()


def _load_contracts(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return raw.get("contracts") or {}


def _paper_rows(con: duckdb.DuckDBPyConnection, year: int, paper_aliases: list[str]) -> int:
    rows = con.execute(
        "SELECT paper_type, COUNT(*) FROM exam_questions WHERE year = ? GROUP BY 1",
        [year],
    ).fetchall()
    alias_set = {_norm(item) for item in paper_aliases}
    return sum(count for paper_type, count in rows if _norm(paper_type) in alias_set)


def _any_rows(con: duckdb.DuckDBPyConnection, year: int) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM exam_questions WHERE year = ?",
        [year],
    ).fetchone()[0]


def _year_result(
    con: duckdb.DuckDBPyConnection,
    *,
    year: int,
    year_contract: dict[str, Any],
    paper_aliases: list[str],
) -> YearContractResult:
    expected = int(year_contract.get("expected_min_rows") or 0)
    matching = _paper_rows(con, year, paper_aliases)
    any_rows = _any_rows(con, year)
    current_status = str(year_contract.get("current_status") or "unknown")
    findings: list[str] = []

    if matching < expected:
        findings.append(f"db_contract_gap:{expected - matching}")
    if any_rows and not matching:
        findings.append("year_rows_exist_but_no_contract_paper_match")
    if any_rows < expected:
        findings.append(f"db_any_paper_gap:{expected - any_rows}")
    if any(token in current_status for token in ("not_", "partial", "suspicious", "candidate")):
        findings.append(f"contract_status_not_closed:{current_status}")

    status = "fail" if findings else "pass"
    return YearContractResult(
        year=year,
        expected_min_rows=expected,
        db_rows_matching_paper=matching,
        db_rows_any_paper=any_rows,
        current_status=current_status,
        status=status,
        findings=findings,
        known_gaps=list(year_contract.get("known_gaps") or []),
        current_known_sources=list(year_contract.get("current_known_sources") or []),
    )


def audit_contract(
    contract_name: str,
    *,
    db_path: Path = DEFAULT_DB,
    contracts_path: Path = DEFAULT_CONTRACTS,
) -> dict[str, Any]:
    contracts = _load_contracts(contracts_path)
    if contract_name not in contracts:
        known = ", ".join(sorted(contracts))
        raise KeyError(f"unknown contract {contract_name!r}; known={known}")

    contract = contracts[contract_name]
    aliases = list(contract.get("paper_type_aliases") or [contract.get("paper_type")])
    years = contract.get("years") or {}
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        results = [
            _year_result(con, year=int(year), year_contract=dict(year_contract), paper_aliases=aliases)
            for year, year_contract in sorted(years.items())
        ]
    finally:
        con.close()

    failed = [item for item in results if item.status != "pass"]
    return {
        "generated_at": _now_iso(),
        "tool": "backend.services.audit.exam_contracts",
        "contract_name": contract_name,
        "paper_type": contract.get("paper_type"),
        "paper_type_aliases": aliases,
        "truth_gate": contract.get("truth_gate"),
        "status": "fail" if failed else "pass",
        "summary": {
            "years": len(results),
            "failed_years": len(failed),
            "total_db_rows_matching_paper": sum(item.db_rows_matching_paper for item in results),
            "total_db_rows_any_paper": sum(item.db_rows_any_paper for item in results),
        },
        "years": [item.__dict__ for item in results],
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
