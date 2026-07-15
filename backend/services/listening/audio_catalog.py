"""Listening audio catalog — single compute from audio_config + filesystem.

Does not invent question stems. Serves year/file inventory + path resolution
for promote + API.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "backend/config/audio_config.yaml"


def load_audio_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def audio_root(cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_audio_config()
    return ROOT / cfg["directory_layout"]["root"]


def year_listening_dir(year: int, cfg: dict[str, Any] | None = None) -> Path:
    return audio_root(cfg) / str(year) / "listening"


def resolve_audio_file(year: int, file_id: str, cfg: dict[str, Any] | None = None) -> Path:
    """Resolve data/audio/{year}/listening/{id}.mp3; rejects path traversal."""
    cfg = cfg or load_audio_config()
    safe_id = Path(file_id).name
    if safe_id != file_id or ".." in file_id or "/" in file_id or "\\" in file_id:
        raise ValueError(f"invalid audio id: {file_id!r}")
    if not safe_id.endswith(".mp3"):
        safe_id = f"{safe_id}.mp3"
    base = year_listening_dir(year, cfg).resolve()
    path = (base / safe_id).resolve()
    path.relative_to(base)
    return path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def catalog(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Derived catalog: config years_with_audio ∩ files on disk."""
    cfg = cfg or load_audio_config()
    years = list(cfg.get("years_with_audio") or [])
    promote = cfg.get("promote_map") or {}
    by_year: list[dict[str, Any]] = []
    missing: list[str] = []
    for year in years:
        ydir = year_listening_dir(year, cfg)
        expected = promote.get(year) or promote.get(str(year)) or {}
        files_meta = []
        for spec in expected.get("files") or []:
            fid = spec["id"]
            path = resolve_audio_file(year, fid, cfg)
            if not path.is_file():
                missing.append(f"{year}/{fid}.mp3")
                files_meta.append(
                    {
                        "id": fid,
                        "path": str(path.relative_to(ROOT)),
                        "exists": False,
                    }
                )
                continue
            files_meta.append(
                {
                    "id": fid,
                    "path": str(path.relative_to(ROOT)),
                    "exists": True,
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "url": f"/api/listening/file?year={year}&id={fid}",
                }
            )
        by_year.append(
            {
                "year": year,
                "source": expected.get("source"),
                "packing": expected.get("packing"),
                "dir": str(ydir.relative_to(ROOT)) if ydir.exists() else None,
                "files": files_meta,
                "file_count": sum(1 for f in files_meta if f.get("exists")),
            }
        )
    return {
        "module_status": cfg.get("module_status"),
        "provenance": cfg.get("provenance"),
        "years_with_audio": years,
        "years": by_year,
        "missing_files": missing,
        "complete": not missing,
    }


def promote_all(*, link: bool = True) -> dict[str, Any]:
    """Copy or hardlink candidate mp3s into data/audio per promote_map."""
    cfg = load_audio_config()
    promote = cfg.get("promote_map") or {}
    results: list[dict[str, Any]] = []
    for year_key, spec in sorted(promote.items(), key=lambda x: int(x[0])):
        year = int(year_key)
        out_dir = year_listening_dir(year, cfg)
        out_dir.mkdir(parents=True, exist_ok=True)
        for item in spec.get("files") or []:
            src = ROOT / item["from"]
            dst = resolve_audio_file(year, item["id"], cfg)
            row: dict[str, Any] = {
                "year": year,
                "id": item["id"],
                "src": str(src.relative_to(ROOT)),
                "dst": str(dst.relative_to(ROOT)),
            }
            if not src.is_file():
                row["status"] = "SKIP_MISSING_SRC"
                results.append(row)
                continue
            if dst.exists():
                if sha256_file(src) == sha256_file(dst):
                    row["status"] = "OK_EXISTS"
                    row["sha256"] = sha256_file(dst)
                    results.append(row)
                    continue
                dst.unlink()
            try:
                if link:
                    dst.hardlink_to(src)
                    row["status"] = "OK_HARDLINK"
                else:
                    raise OSError("force copy")
            except OSError:
                dst.write_bytes(src.read_bytes())
                row["status"] = "OK_COPY"
            row["sha256"] = sha256_file(dst)
            row["bytes"] = dst.stat().st_size
            results.append(row)
        # year manifest
        man = {
            "year": year,
            "source": spec.get("source"),
            "packing": spec.get("packing"),
            "provenance": cfg.get("provenance"),
            "files": [
                r
                for r in results
                if r["year"] == year and r.get("status", "").startswith("OK")
            ],
        }
        (out_dir / "MANIFEST.json").write_text(
            __import__("json").dumps(man, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    cat = catalog(cfg)
    return {"promoted": results, "catalog": cat}
