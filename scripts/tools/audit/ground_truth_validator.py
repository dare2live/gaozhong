#!/usr/bin/env python3
"""生成题结构校验 — 检查题面合理性 / 答案存在 / 解析逻辑 / 格式要素."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"


def validate(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute("""
        SELECT qb_id, question_type, stem, answer, analysis,
               has_audio, transcript, origin
        FROM question_bank
        WHERE origin IN ('listening_exercise', 'writing_exercise')
    """).fetchall()
    issues: list[dict] = []
    for qid, qt, stem, ans, analysis, has_audio, transcript, origin in rows:
        q_issues = _check_one(qid, qt, stem, ans, analysis, has_audio, transcript)
        issues.extend(q_issues)

    n_checked = len(rows)
    n_pass = n_checked - len({i["qb_id"] for i in issues})
    score = 100 * n_pass / max(n_checked, 1)
    return {
        "name": "生成题结构校验",
        "score": round(score, 1),
        "pass": score >= 80,
        "n_checked": n_checked,
        "n_pass": n_pass,
        "n_issues": len(issues),
        "issues": issues[:20],
    }


def _check_one(qid, qt, stem, ans, analysis, has_audio, transcript) -> list[dict]:
    issues = _check_common(qid, stem, ans, analysis)
    if "听力" in qt:
        issues += _check_listening(qid, stem, ans, has_audio, transcript)
    elif qt == "续写":
        issues += _check_narrative(qid, stem, ans)
    elif qt == "应用文":
        issues += _check_applied(qid, ans)
    return issues


def _check_common(qid, stem, ans, analysis) -> list[dict]:
    issues = []
    if not stem or len(stem.strip()) < 10:
        issues.append({"qb_id": qid, "rule": "stem_too_short", "detail": f"len={len(stem or '')}"})
    if not ans or len(ans.strip()) < 1:
        issues.append({"qb_id": qid, "rule": "answer_missing", "detail": "empty"})
    if not analysis or len(analysis.strip()) < 10:
        issues.append({"qb_id": qid, "rule": "analysis_weak", "detail": f"len={len(analysis or '')}"})
    return issues


def _check_listening(qid, stem, ans, has_audio, transcript) -> list[dict]:
    issues = []
    if has_audio and (not transcript or len(transcript.strip()) < 20):
        issues.append({"qb_id": qid, "rule": "transcript_missing", "detail": "has_audio but no transcript"})
    if _has_options(stem) and ans and ans.strip() not in ("A", "B", "C", "D"):
        issues.append({"qb_id": qid, "rule": "answer_not_abcd", "detail": f"ans={ans.strip()}"})
    return issues


def _check_narrative(qid, stem, ans) -> list[dict]:
    issues = []
    if ans and len(ans.strip().split()) < 50:
        issues.append({"qb_id": qid, "rule": "narrative_too_short", "detail": f"words={len(ans.strip().split())}"})
    if stem and "Paragraph" not in stem and "续写" not in stem:
        issues.append({"qb_id": qid, "rule": "no_paragraph_hint", "detail": "missing Paragraph marker"})
    return issues


def _check_applied(qid, ans) -> list[dict]:
    issues = []
    if ans and len(ans.strip().split()) < 40:
        issues.append({"qb_id": qid, "rule": "applied_too_short", "detail": f"words={len(ans.strip().split())}"})
    fmt_markers = ("Dear", "NOTICE", "My ", "Green ", "Last ")
    if ans and not any(k in ans for k in fmt_markers) and not ans.strip()[0].isupper():
        issues.append({"qb_id": qid, "rule": "no_salutation", "detail": "missing format marker"})
    return issues


def _has_options(stem: str | None) -> bool:
    if not stem:
        return False
    return bool(re.search(r"[ABC]\.", stem))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="生成题结构校验")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        result = validate(con)
    finally:
        con.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"生成题结构校验: {result['score']:.1f}/100 ({result['n_pass']}/{result['n_checked']} pass)")
    if result["issues"]:
        print(f"\n问题 ({result['n_issues']}):")
        for i in result["issues"]:
            print(f"  #{i['qb_id']} [{i['rule']}] {i['detail']}")
    else:
        print("全部通过 ✅")


if __name__ == "__main__":
    main()
