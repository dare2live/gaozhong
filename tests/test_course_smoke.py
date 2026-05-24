"""M5 smoke — course service 9 模块 + 8 audit + config 3 yaml.

跑法: PYTHONPATH=. python3 tests/test_course_smoke.py
要求: data/db/gaozhong.duckdb 已存在.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import duckdb

from backend.services.audit import course as audit_course
from backend.services.course import (handout, homework, init_courses,
                                      lexicon_filter, loader, materials,
                                      registry, relations, scenarios)

DB = ROOT / "data" / "db" / "gaozhong.duckdb"


def assert_(cond: bool, msg: str) -> None:
    if not cond:
        print(f"  ❌ FAIL: {msg}")
        raise SystemExit(1)
    print(f"  ✅ {msg}")


def main() -> None:
    print("== M3 yaml 加载 ==")
    courses = loader.load_course_templates()
    assert_(len(courses) >= 4, f"≥4 节 (实测 {len(courses)})")
    pool = loader.load_theme_pool()
    assert_(len(pool) == 10, f"主题池 10 类 (实测 {len(pool)})")
    assert_(sum(len(c["themes"]) for c in pool.values()) >= 50, "≥50 主题")
    bl = loader.load_political_blacklist()
    assert_(len(bl) >= 5, f"政治黑名单 ≥5 词 (实测 {len(bl)})")

    print("\n== M2 registry ==")
    @registry.block("vocab")
    def _h(c):  # noqa
        return None
    assert_(registry.get_block("vocab") is not None, "block 注册取回 OK")

    print("\n== R5 lexicon_filter ==")
    con = duckdb.connect(str(DB), read_only=True)
    g1 = lexicon_filter.allowed_words_for(con, "G1")
    g_final = lexicon_filter.allowed_words_for(con, "G_FINAL")
    assert_(len(g1) > 100, f"G1 词集 >100 (实测 {len(g1)})")
    assert_(len(g_final) > len(g1), f"G_FINAL ({len(g_final)}) > G1 ({len(g1)}) 向下兼容")

    print("\n== R6 word_position ==")
    pos = lexicon_filter.word_position(con, "family")
    if pos:
        print(f"  family → year={pos[0]} pos={pos[1]}")
    assert_(pos is not None and pos[1], "family 能反查到 textbook_position")

    print("\n== R1 relations ==")
    for cid_word in ["word:family", "word:authentic"]:
        rels = relations.related_concepts(con, cid_word)
        print(f"  {cid_word} → {len(rels)} 关联")

    print("\n== R3 scenarios ==")
    for c in courses:
        n = scenarios.count_scenarios(c)
        assert_(n >= 3, f"course #{c['course_id']} ≥3 场景 (实测 {n})")

    print("\n== R4 homework alignment ==")
    for c in courses:
        qs = homework.pick_homework(con, c.get("homework_tags") or [])
        qb_ids = [q["qb_id"] for q in qs]
        res = homework.homework_tag_alignment(con, qb_ids, c.get("homework_tags") or [])
        if qs:
            assert_(res["n_outside"] == 0,
                    f"course #{c['course_id']} 作业 {len(qs)} 题 tag ⊆ 本节 (outside={res['n_outside']})")

    print("\n== materials build ==")
    m = materials.build_materials_for_course(con, courses[0])
    assert_(len(m) >= 5, f"course #{courses[0]['course_id']} materials >=5 (实测 {len(m)})")

    print("\n== handout 7 段 ==")
    h = handout.render_handout(con, courses[0])
    assert_(h["n_segments"] == 7, f"handout 7 段 (实测 {h['n_segments']})")
    assert_(len(h["md"]) > 200, f"md 长度 >200 (实测 {len(h['md'])})")

    print("\n== 8 audit 逐个 ==")
    for fn_name in [
        "audit_course_relations", "audit_course_no_textbook_copy",
        "audit_course_scenarios", "audit_homework_alignment",
        "audit_course_lexical_layer", "audit_course_textbook_position",
        "audit_listening_transcript_required", "audit_no_political",
    ]:
        out = getattr(audit_course, fn_name)(con)
        sev = {f["severity"] for f in out}
        print(f"  {fn_name}: {len(out)} findings, severity={sev}")

    con.close()
    print("\n✅ ALL SMOKE PASS")


if __name__ == "__main__":
    main()
