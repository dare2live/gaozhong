"""Read external data-source contracts from backend/config/sources.yaml."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "backend" / "config" / "sources.yaml"


@dataclass(frozen=True)
class AttachmentSpec:
    kind: str
    url: str | None
    local_path: Path
    expected_sha256: str | None = None
    min_bytes: int = 1
    transform: str | None = None
    text_path: Path | None = None
    min_text_chars: int = 0

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "AttachmentSpec":
        return cls(
            kind=str(raw.get("kind") or "file"),
            url=str(raw["url"]) if raw.get("url") else None,
            local_path=ROOT / str(raw["local_path"]),
            expected_sha256=raw.get("expected_sha256"),
            min_bytes=int(raw.get("min_bytes") or 1),
            transform=raw.get("transform"),
            text_path=(ROOT / str(raw["text_path"])) if raw.get("text_path") else None,
            min_text_chars=int(raw.get("min_text_chars") or 0),
        )


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    name: str
    family: str
    org: str
    publish_url: str
    status: str
    year: int | None
    paper_type: str | None
    observed_scope: str | None
    attachments: tuple[AttachmentSpec, ...]

    @classmethod
    def from_raw(cls, source_id: str, raw: dict[str, Any]) -> "SourceSpec":
        return cls(
            source_id=source_id,
            name=str(raw["name"]),
            family=str(raw.get("family") or "external"),
            org=str(raw.get("org") or ""),
            publish_url=str(raw.get("publish_url") or ""),
            status=str(raw.get("status") or "unknown"),
            year=int(raw["year"]) if raw.get("year") is not None else None,
            paper_type=raw.get("paper_type"),
            observed_scope=raw.get("observed_scope"),
            attachments=tuple(AttachmentSpec.from_raw(item) for item in raw.get("attachments", [])),
        )


class SourceRegistry:
    def __init__(self, sources: dict[str, SourceSpec]) -> None:
        self._sources = dict(sources)

    def get(self, source_id: str) -> SourceSpec:
        try:
            return self._sources[source_id]
        except KeyError as exc:
            known = ", ".join(sorted(self._sources))
            raise KeyError(f"unknown source_id={source_id!r}; known={known}") from exc

    def list_ids(self) -> list[str]:
        return sorted(self._sources)

    def list_sources(self) -> list[SourceSpec]:
        return [self._sources[key] for key in self.list_ids()]


def load_registry(config_path: Path | None = None) -> SourceRegistry:
    path = config_path or DEFAULT_CONFIG
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    source_rows = raw.get("exam_sources") or {}
    sources = {
        source_id: SourceSpec.from_raw(source_id, row)
        for source_id, row in source_rows.items()
    }
    return SourceRegistry(sources)
