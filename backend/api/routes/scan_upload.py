"""POST /api/scan/upload — 4.7 学生扫描卷面上传 stub.

调用:
  curl -X POST 'http://x:8765/api/scan/upload?student_id=001&kind=answer_sheet&filename=sheet.pdf' \
       -H 'Content-Type: application/octet-stream' \
       --data-binary @sheet.pdf

行为:
  1. 写入 data/scans/<upload_id>.<ext>
  2. sha256 + 入 scan_uploads 表
  3. PDF 用 pypdf 抽文字层 (无 OCR 走真扫描图片仍 pending)
  4. 返回 {upload_id, file_size, ocr_status, text_chars}

不引 PaddleOCR (用户暂不要); 仅 PDF 文字层兜底.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCAN_DIR = ROOT / "data" / "scans"
DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"

MAX_UPLOAD_BYTES = 20 * 1024 * 1024   # 20 MB


def _pypdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
        r = PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in r.pages)
    except Exception as e:
        return f"<<pypdf failed: {e}>>"


def handle(qs: dict, body: bytes, headers) -> tuple[int, dict]:
    if not body:
        return 400, {"error": "empty body"}
    if len(body) > MAX_UPLOAD_BYTES:
        return 413, {"error": f"too large > {MAX_UPLOAD_BYTES}"}
    student_id = qs.get("student_id", [None])[0]
    kind = qs.get("kind", ["answer_sheet"])[0]
    filename = qs.get("filename", ["upload.bin"])[0]
    ext = (filename.rsplit(".", 1)[1] if "." in filename else "bin").lower()[:6]
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    upload_id = uuid.uuid4().hex[:12]
    file_path = SCAN_DIR / f"{upload_id}.{ext}"
    file_path.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    text = _pypdf_text(file_path) if ext == "pdf" else ""
    ocr_status = "done" if text and not text.startswith("<<") else "pending"
    text_path = None
    if text:
        text_path = str((SCAN_DIR / f"{upload_id}.txt").relative_to(ROOT))
        (ROOT / text_path).write_text(text, encoding="utf-8")
    # DB insert (RW connection)
    con = duckdb.connect(str(DB_PATH))
    try:
        con.execute("""
            INSERT INTO scan_uploads VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [upload_id, student_id,
              str(file_path.relative_to(ROOT)), sha, kind,
              datetime.now(timezone.utc).isoformat(),
              ocr_status, text_path])
    finally:
        con.close()
    return 200, {
        "upload_id": upload_id, "file_size": len(body),
        "sha256": sha[:16], "ext": ext,
        "ocr_status": ocr_status,
        "text_chars": len(text) if text and not text.startswith("<<") else 0,
        "text_path": text_path,
    }
