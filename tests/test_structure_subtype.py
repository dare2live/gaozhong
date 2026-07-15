"""单元测试: 理解文章结构类型 L2 — 永不 unknown + 四级优先级."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.exam_point.structure_subtype import (
    blank_src_ids,
    classify_structure_subtype,
    curated_subtypes,
    discourse_slot,
    extract_blank_analysis,
    parse_option_letters,
)
from backend.services.exam_point.cognitive_seven_choose_five import (
    structure_subtype_distribution,
)


# ── parse / expand ──────────────────────────────────────────────

def test_parse_option_letters_single():
    assert parse_option_letters("C") == ["C"]


def test_parse_option_letters_list():
    assert parse_option_letters("['A', 'D', 'F', 'B', 'G']") == ["A", "D", "F", "B", "G"]


def test_parse_option_letters_numbered():
    assert parse_option_letters("36.A 37.C 38.F 39.B 40.G") == ["A", "C", "F", "B", "G"]


def test_blank_src_ids_bundled():
    out = blank_src_ids("pdf/2025/xgkii/reading2", "['D','A','F','C','G']")
    assert len(out) == 5
    assert out[0] == ("pdf/2025/xgkii/reading2#q36", 36, "D")
    assert out[4][1] == 40


def test_blank_src_ids_single_trail():
    out = blank_src_ids("eol/2021/xgkii/38", "F")
    assert out == [("eol/2021/xgkii/38", 38, "F")]


def test_blank_src_ids_mismatch_raises():
    try:
        blank_src_ids("x/1", "A,B")
        raise AssertionError("should raise")
    except ValueError:
        pass


def test_extract_blank_analysis_detail_blocks():
    an = "【36题详解】本空为主题句。【37题详解】承上启下过渡。"
    got = extract_blank_analysis(an)
    assert "主题句" in got[36]
    assert "承上启下" in got[37]


# ── analysis_explicit ───────────────────────────────────────────

def test_classify_analysis_主题句():
    st, rule, meth = classify_structure_subtype("本空为主题句, 统领全段")
    assert st == "主题句" and meth == "analysis_explicit"


def test_classify_analysis_承上启下():
    st, _, meth = classify_structure_subtype("此空起承上启下作用")
    assert st == "承上启下" and meth == "analysis_explicit"


def test_classify_analysis_段旨收束():
    st, _, meth = classify_structure_subtype("位于段尾, 对本段的总结")
    assert st == "段旨收束" and meth == "analysis_explicit"


def test_classify_analysis_逻辑推进():
    st, _, meth = classify_structure_subtype("进一步解释前句内容")
    assert st == "逻辑推进" and meth == "analysis_explicit"


def test_classify_analysis_句际衔接():
    st, _, meth = classify_structure_subtype("根据前句上下文联系选答案")
    assert st == "句际衔接" and meth == "analysis_explicit"


# ── curated > empty analysis ────────────────────────────────────

def test_classify_curated_when_no_analysis():
    curated = curated_subtypes()
    assert curated, "curated jsonl must exist"
    src_id, row = next(iter(curated.items()))
    st, note, meth = classify_structure_subtype("", src_id=src_id)
    assert meth == "curated_passage"
    assert st == row["subtype"]
    assert st != "unknown"


def test_classify_analysis_beats_curated():
    """有明确解析时不走 curated (优先级1>2)."""
    curated = curated_subtypes()
    src_id = next(iter(curated))
    st, _, meth = classify_structure_subtype("本空为主题句", src_id=src_id)
    assert meth == "analysis_explicit"
    assert st == "主题句"


# ── discourse_slot ──────────────────────────────────────────────

def test_discourse_heading_blank():
    passage = "Intro text\n● ___36___ \nMore body here about gardens."
    got = discourse_slot(passage, 36)
    assert got and got[0] == "主题句"


def test_discourse_fallback_local():
    passage = "AAAA " * 40 + "36" + " BBBB " * 40
    got = discourse_slot(passage, 36)
    assert got is not None
    assert got[0] in {"主题句", "承上启下", "段旨收束", "逻辑推进", "句际衔接"}


# ── fallback: never unknown ─────────────────────────────────────

def test_classify_fallback_never_unknown():
    st, rule, meth = classify_structure_subtype(
        "", src_id="nonexistent/id", passage="", blank_no=None,
    )
    assert meth == "fallback_cohesion"
    assert st == "句际衔接"
    assert st != "unknown"
    assert "fallback" in rule


def test_classify_all_methods_exclude_unknown():
    cases = [
        ("主题句在此", None, None, None),
        ("", "ghost", "", None),
        ("", None, "word 36 word", 36),
    ]
    for snip, sid, pas, bn in cases:
        st, _, meth = classify_structure_subtype(snip, src_id=sid, passage=pas, blank_no=bn)
        assert st != "unknown", (snip, sid, meth)
        assert meth in {
            "analysis_explicit", "curated_passage", "discourse_slot", "fallback_cohesion",
        }


# ── curated file integrity ──────────────────────────────────────

def test_curated_jsonl_valid_subtypes():
    allowed = {"主题句", "承上启下", "段旨收束", "逻辑推进", "句际衔接"}
    path = ROOT / "data/structured/exam_point/cognitive_structure_subtype_labels.jsonl"
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) >= 20
    for r in rows:
        assert r["subtype"] in allowed, r
        assert r["src_id"]
        assert "unknown" not in r["subtype"]


def test_curated_covers_known_gap_years():
    """2021/22/25/26 + 中考五选四 曾为 unknown 的空位须在 curated."""
    ids = set(curated_subtypes())
    need_any = [
        "eol/2021", "eol/2022", "2025", "2026", "ZK-LN-2024", "ZK-LN-2025",
    ]
    for prefix in need_any:
        assert any(prefix in i for i in ids), f"missing curated for {prefix}"


# ── DB distribution (integration, read-only) ────────────────────

def test_db_gaokao_structure_unknown_zero():
    import duckdb
    db = ROOT / "data/db/gaozhong.duckdb"
    if not db.exists():
        print("SKIP: no duckdb")
        return
    con = duckdb.connect(str(db), read_only=True)
    try:
        sub = structure_subtype_distribution(con, "gaokao")
        assert sub["n_total"] == 60, sub
        assert sub["unknown_n"] == 0, sub
        labels = {x["label"] for x in sub["by_subtype"]}
        assert "unknown" not in labels
        assert labels <= {"主题句", "承上启下", "段旨收束", "逻辑推进", "句际衔接"}
    finally:
        con.close()


def test_db_zhongkao_structure_unknown_zero():
    import duckdb
    db = ROOT / "data/db/gaozhong.duckdb"
    if not db.exists():
        print("SKIP: no duckdb")
        return
    con = duckdb.connect(str(db), read_only=True)
    try:
        sub = structure_subtype_distribution(con, "zhongkao")
        assert sub["n_total"] >= 8, sub
        assert sub["unknown_n"] == 0, sub
    finally:
        con.close()


def test_db_no_unknown_subtype_literal():
    import duckdb
    db = ROOT / "data/db/gaozhong.duckdb"
    if not db.exists():
        return
    con = duckdb.connect(str(db), read_only=True)
    try:
        n = con.execute(
            "SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' "
            "AND json_extract_string(evidence_json,'$.dimension')='cognitive_skill' "
            "AND json_extract_string(evidence_json,'$.provenance')='curriculum_aligned_task' "
            "AND json_extract_string(evidence_json,'$.subtype')='unknown'"
        ).fetchone()[0]
        assert n == 0, f"found {n} unknown subtype edges"
    finally:
        con.close()


def test_adversarial_unknown_detected():
    """注入 unknown subtype 后 distribution.unknown_n 必须 >0 (防门假绿)."""
    import duckdb
    import shutil
    import tempfile

    db = ROOT / "data/db/gaozhong.duckdb"
    if not db.exists():
        return
    tmp = Path(tempfile.mkdtemp()) / "adv.duckdb"
    shutil.copy(db, tmp)
    con = duckdb.connect(str(tmp))
    try:
        row = con.execute(
            "SELECT edge_id, evidence_json FROM edges WHERE relation='tests_exam_point' "
            "AND json_extract_string(evidence_json,'$.provenance')='curriculum_aligned_task' "
            "AND COALESCE(json_extract_string(evidence_json,'$.exam_stage'),'gaokao')='gaokao' "
            "LIMIT 1"
        ).fetchone()
        assert row
        eid, ev = row
        evj = json.loads(ev)
        evj["subtype"] = "unknown"
        con.execute(
            "UPDATE edges SET evidence_json=? WHERE edge_id=?",
            [json.dumps(evj, ensure_ascii=False), eid],
        )
        sub = structure_subtype_distribution(con, "gaokao")
        assert sub["unknown_n"] >= 1, sub
    finally:
        con.close()
        tmp.unlink(missing_ok=True)
        tmp.parent.rmdir()


if __name__ == "__main__":
    tests = [f for f in dir() if f.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            globals()[t]()
            print(f"  ✅ {t}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {t}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ⚠️ {t}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed + failed} tests passed")
    sys.exit(1 if failed else 0)
