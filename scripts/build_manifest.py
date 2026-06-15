"""Build PDF + structured-data lineage manifest (Step 1 资料基石审计).

按姊妹项目 ~/Documents/M/gaokao/scripts/pull_official_pdfs.py 风格设计:
  - sha256 + size + 来源 URL/repo (尽量回溯)
  - 一行一条 jsonl, 不破坏现有数据
  - 失败显式: 文件读不到就抛, 不静默吃

用法:
    python3 scripts/build_manifest.py
输出:
    data/manifest/textbook_manifest.jsonl
    data/manifest/curriculum_manifest.jsonl
    data/manifest/structured_manifest.jsonl
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = ROOT / "data" / "manifest"

VERSION_LABEL = {
    "renjiao": ("人教版-人民教育出版社", "https://github.com/TapXWorld/ChinaTextbook/tree/master/%E9%AB%98%E4%B8%AD/%E8%8B%B1%E8%AF%AD/%E4%BA%BA%E6%95%99%E7%89%88-%E4%BA%BA%E6%B0%91%E6%95%99%E8%82%B2%E5%87%BA%E7%89%88%E7%A4%BE"),
    "waiyan": ("外研社版-外语教学与研究出版社", "https://github.com/TapXWorld/ChinaTextbook/tree/master/%E9%AB%98%E4%B8%AD/%E8%8B%B1%E8%AF%AD/%E5%A4%96%E7%A0%94%E7%A4%BE%E7%89%88-%E5%A4%96%E8%AF%AD%E6%95%99%E5%AD%A6%E4%B8%8E%E7%A0%94%E7%A9%B6%E5%87%BA%E7%89%88%E7%A4%BE"),
    "beishida": ("北师大版-北京师范大学出版社", "https://github.com/TapXWorld/ChinaTextbook/tree/master/%E9%AB%98%E4%B8%AD/%E8%8B%B1%E8%AF%AD/%E5%8C%97%E5%B8%88%E5%A4%A7%E7%89%88-%E5%8C%97%E4%BA%AC%E5%B8%88%E8%8C%83%E5%A4%A7%E5%AD%A6%E5%87%BA%E7%89%88%E7%A4%BE"),
    "yilin": ("译林版-译林出版社", "https://github.com/TapXWorld/ChinaTextbook/tree/master/%E9%AB%98%E4%B8%AD/%E8%8B%B1%E8%AF%AD"),
    "huwaijiao": ("沪外教版-上海外语教育出版社", "https://github.com/TapXWorld/ChinaTextbook/tree/master/%E9%AB%98%E4%B8%AD/%E8%8B%B1%E8%AF%AD"),
    "hujiao": ("沪教版-上海教育出版社", "https://github.com/TapXWorld/ChinaTextbook/tree/master/%E9%AB%98%E4%B8%AD/%E8%8B%B1%E8%AF%AD"),
    "jijiao": ("冀教版-河北教育出版社", "https://github.com/TapXWorld/ChinaTextbook/tree/master/%E9%AB%98%E4%B8%AD/%E8%8B%B1%E8%AF%AD"),
    "chongqingdaxue": ("重庆大学版-重庆大学出版社", "https://github.com/TapXWorld/ChinaTextbook/tree/master/%E9%AB%98%E4%B8%AD/%E8%8B%B1%E8%AF%AD"),
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tracked_files_under(base: Path) -> list[Path]:
    if not base.exists():
        return []
    rel = str(base.relative_to(ROOT))
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-files", "--", rel],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return []
    return [ROOT / line for line in out.splitlines() if line.strip()]


def _input_files(base: Path, suffix: str | None = None) -> list[Path]:
    tracked = _tracked_files_under(base)
    files = tracked or [p for p in base.rglob("*") if p.is_file()]
    if suffix:
        files = [p for p in files if p.suffix == suffix]
    return sorted(files)


def build_textbook_manifest() -> list[dict]:
    rows = []
    base = ROOT / "data" / "textbooks"
    for ver_dir in sorted(base.iterdir()):
        if not ver_dir.is_dir():
            continue
        label, src_url = VERSION_LABEL.get(ver_dir.name, (ver_dir.name, ""))
        for pdf in _input_files(ver_dir, ".pdf"):
            rows.append({
                "type": "textbook",
                "version_key": ver_dir.name,
                "publisher_label": label,
                "book_file": pdf.name,
                "rel_path": str(pdf.relative_to(ROOT)),
                "size_bytes": pdf.stat().st_size,
                "sha256": _sha256(pdf),
                "source_repo": "TapXWorld/ChinaTextbook",
                "source_dir_url": src_url,
            })
    return rows


def build_curriculum_manifest() -> list[dict]:
    rows = []
    base = ROOT / "data" / "curriculum" / "national"
    for pdf in _input_files(base, ".pdf"):
        rows.append({
            "type": "curriculum_standard",
            "subject": pdf.stem,
            "rel_path": str(pdf.relative_to(ROOT)),
            "size_bytes": pdf.stat().st_size,
            "sha256": _sha256(pdf),
            "source_org": "教育部 (MoE)",
            "source_url": "http://www.moe.gov.cn/srcsite/A26/s8001/202006/t20200603_462199.html",
            "source_attachment_url": "http://www.moe.gov.cn/srcsite/A26/s8001/202006/W020200603315372317586.zip",
        })
    return rows


def build_structured_manifest() -> list[dict]:
    rows = []
    base = ROOT / "data" / "structured"
    repo_to_url = {
        "DictionaryData": "https://github.com/LinXueyuanStdio/DictionaryData",
        "dict": "https://github.com/kajweb/dict",
        "english-wordlists": "https://github.com/mahavivo/english-wordlists",
    }
    for repo_dir in sorted(base.iterdir()):
        if not repo_dir.is_dir():
            continue
        repo_files = _input_files(repo_dir)
        sz = sum(f.stat().st_size for f in repo_files)
        rows.append({
            "type": "structured_repo",
            "repo": repo_dir.name,
            "rel_path": str(repo_dir.relative_to(ROOT)),
            "size_bytes": sz,
            "tracked_file_count": len(repo_files),
            "source_url": repo_to_url.get(repo_dir.name, ""),
        })
    return rows


def write_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows):4d} rows -> {path.relative_to(ROOT)}")


def write_run_metadata(path: Path) -> None:
    payload = {
        "generated_at": _now(),
        "input_scope": (
            "git ls-files under data/textbooks, data/curriculum, data/structured; "
            "fallback to filesystem scan only when no tracked files are available"
        ),
        "row_timestamps": "omitted to keep row-level lineage stable across reruns",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote run metadata -> {path.relative_to(ROOT)}")


def main() -> None:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(build_textbook_manifest(), MANIFEST_DIR / "textbook_manifest.jsonl")
    write_jsonl(build_curriculum_manifest(), MANIFEST_DIR / "curriculum_manifest.jsonl")
    write_jsonl(build_structured_manifest(), MANIFEST_DIR / "structured_manifest.jsonl")
    write_run_metadata(MANIFEST_DIR / "_manifest_run.json")


if __name__ == "__main__":
    main()
