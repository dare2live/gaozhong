"""Acquire external source files with manifest-grade verification."""
from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .registry import AttachmentSpec, SourceSpec


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, target: Path) -> None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "gaozhong-data-source-acquirer/1.0"},
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=60) as response:
        target.write_bytes(response.read())


def _extract_docx_text(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(source)],
        check=True,
        capture_output=True,
    )
    target.write_bytes(result.stdout)


def _verify_attachment(spec: AttachmentSpec, *, reuse_existing: bool) -> dict[str, Any]:
    findings: list[str] = []
    action = "reused"
    if not spec.local_path.exists():
        if not spec.url:
            findings.append("missing_local_file")
            findings.append("no_download_url")
            return {
                "kind": spec.kind,
                "local_path": str(spec.local_path),
                "url": spec.url,
                "status": "fail",
                "action": "missing",
                "findings": findings,
            }
        _download(spec.url, spec.local_path)
        action = "downloaded"
    elif not reuse_existing and spec.url:
        _download(spec.url, spec.local_path)
        action = "downloaded"
    elif not reuse_existing and not spec.url:
        action = "local_only_reused"

    if not spec.local_path.exists():
        findings.append("missing_local_file")
        return {
            "kind": spec.kind,
            "local_path": str(spec.local_path),
            "url": spec.url,
            "status": "fail",
            "action": action,
            "findings": findings,
        }

    size = spec.local_path.stat().st_size
    digest = _sha256(spec.local_path)
    if size < spec.min_bytes:
        findings.append(f"too_small:{size}<{spec.min_bytes}")
    if spec.expected_sha256 and digest != spec.expected_sha256:
        findings.append("sha256_mismatch")

    text_chars = None
    if spec.text_path:
        if spec.transform == "docx_to_txt" and (not spec.text_path.exists() or not reuse_existing):
            _extract_docx_text(spec.local_path, spec.text_path)
        if spec.text_path.exists():
            text_chars = len(spec.text_path.read_text(encoding="utf-8", errors="ignore"))
            if text_chars < spec.min_text_chars:
                findings.append(f"text_too_short:{text_chars}<{spec.min_text_chars}")
        else:
            findings.append("missing_text_extract")

    return {
        "kind": spec.kind,
        "url": spec.url,
        "local_path": str(spec.local_path),
        "text_path": str(spec.text_path) if spec.text_path else None,
        "expected_sha256": spec.expected_sha256,
        "actual_sha256": digest,
        "bytes": size,
        "text_chars": text_chars,
        "status": "fail" if findings else "ok",
        "action": action,
        "findings": findings,
    }


def acquire_source(source: SourceSpec, *, reuse_existing: bool = False) -> dict[str, Any]:
    attachments = [
        _verify_attachment(item, reuse_existing=reuse_existing)
        for item in source.attachments
    ]
    findings = [
        f"{item['kind']}:{finding}"
        for item in attachments
        for finding in item.get("findings", [])
    ]
    return {
        "generated_at": _now_iso(),
        "source_id": source.source_id,
        "name": source.name,
        "family": source.family,
        "org": source.org,
        "publish_url": source.publish_url,
        "year": source.year,
        "paper_type": source.paper_type,
        "configured_status": source.status,
        "observed_scope": source.observed_scope,
        "status": "fail" if findings else "ok",
        "findings": findings,
        "attachments": attachments,
    }


def write_manifest(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": _now_iso(),
        "tool": "scripts/tools/data_sources/acquire_external_source.py",
        "records": records,
        "status": "fail" if any(row["status"] != "ok" for row in records) else "ok",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
