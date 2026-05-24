"""学生扫描录入 (M5 schema 预留, 用 stdlib 简单 OCR baseline).

POST 用法 (浏览器表单或 curl):
  curl -X POST 'http://x:8765/api/scan/upload?student_id=001&kind=answer_sheet' \
       --data-binary @sheet.pdf
返回:
  {"upload_id": "...", "saved_to": "data/scans/...", "pypdf_text_chars": 123}

简版: 只接受 PDF, 用 pypdf 抽文字层; 图片 OCR 留 PaddleOCR 后续接入.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.api.db import db_ro, rows_to_dicts

ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCAN_DIR = ROOT / "data" / "scans"


def api_scan_list(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        return rows_to_dicts(con.execute("""
            SELECT upload_id, student_id, file_rel_path, upload_kind, uploaded_at, ocr_status
            FROM scan_uploads ORDER BY uploaded_at DESC LIMIT 50
        """))
    finally:
        con.close()


def api_scan_meta(qs: dict) -> dict:
    """Stub for 'I want to record metadata about a planned upload' — no actual file storage in GET."""
    return {
        "note": "GET stub. Real POST upload TBD when wired into frontend.",
        "schema": {
            "upload_id": "uuid", "student_id": "students.student_id",
            "kind": "answer_sheet | homework | essay",
            "file_rel_path": "data/scans/<sha>.pdf",
        },
        "scan_dir": str(SCAN_DIR.relative_to(ROOT)),
        "scan_dir_exists": SCAN_DIR.exists(),
    }


def _record_upload(student_id: str | None, kind: str,
                    file_path: Path, ocr_text: str | None) -> str:
    """Insert into scan_uploads (read-only DB → would need RW; placeholder for POST handler)."""
    import duckdb
    con = duckdb.connect(str(ROOT / "data/db/gaozhong.duckdb"))
    upload_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    sha = hashlib.sha256(file_path.read_bytes()).hexdigest() if file_path.exists() else ""
    rel = str(file_path.relative_to(ROOT)) if file_path.exists() else None
    text_path = None
    if ocr_text:
        text_path = str((SCAN_DIR / f"{upload_id}.txt").relative_to(ROOT))
        (ROOT / text_path).write_text(ocr_text, encoding="utf-8")
    con.execute("""
        INSERT INTO scan_uploads VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [upload_id, student_id, rel, sha, kind, now,
          "done" if ocr_text else "pending", text_path])
    con.close()
    return upload_id


ROUTES = {
    "/api/scan/list": api_scan_list,
    "/api/scan/meta": api_scan_meta,
}
