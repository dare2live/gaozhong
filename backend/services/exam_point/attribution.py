"""语篇级联合归因 (词汇学段 × 设问思维) — 2026-07-06 方法论研究落地.

背景: 词汇学段(k12.tested_word_stage_distribution)与设问思维(cognitive_skill.py)原本各自
独立算, 从未对齐到同一批语篇上看。用户提出的问题是"考查词75%基础阶, 但真实得分点是不是靠
高中训练的能力" —— 需要把两条线摆到同一批语篇上才能回答。

**语法学段维度已实测排除, 非遗漏**: 设计之初曾打算做"词汇×语法×设问思维"三线联合, 但实测
发现 tests_grammar 边只出现在 语法填空/短文改错 这两种 question_type 上, 而 cognitive_skill
只标注 阅读理解 的子题(四选一; 七选五结构空另计 curriculum_aligned_task, 不进本联合归因) —— 两者 question_type 完全不相交, 语法维度在当前数据结构下**必然**
是空集(不是"样本少", 是"这两条边永远不会同时出现在同一道题上")。若强行保留这个字段, 会让
读者误以为"这篇文章语法信息未知/待补", 实际是**结构性不可能**, 故诚实地不做这个维度, 而非
摆一个必空的占位字段(参考项目"宁缺毋滥, 返空>假推"原则)。

颗粒度边界(必须诚实, 不可假装更精确): tests_word 边挂在**语篇**层级(question:qid),
cognitive_skill 边挂在**子题**层级(question:qid#qN)。一篇文章的词汇边是对整篇抽取的, 无法
精确到"某道子题具体靠哪个词拿分"。本模块只做**语篇级聚合**(一篇文章N道子题里几道是推断/
几道是细节, 与同一篇文章的词汇学段占比对齐), 不做子题级归因。

era 锁 2015-2020(同 cognitive_skill_by_content 既有约束): 2021+ 子题 node 的 passage_label
只是单字母(A/B/C/D, 年内相对编号非全局唯一 question_id), 无法桥接回 'question:'+id 去 JOIN
tests_word 边(已实测验证: 2021+ 各 passage_label 桥接后 tests_word 边数=0)。

单一计算点(Rule1): 只读聚合已有两条 edge 线, 不新建 edge/表, 不重写其他服务已算好的逻辑
(词汇学段读 at_stage 边同 k12.tested_word_stage_distribution 口径; 设问思维分布读
tests_exam_point dimension=cognitive_skill 同 cognitive_skill_by_content 的 passage_label
桥接手法)。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb

from backend.services.trend import scope

_FOUNDATION_STAGES = {"小学", "初中", "义务教育"}
_SENIOR_STAGES = {"高中必修", "高中选修"}


def _passage_skill_dist(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, int]]:
    """每语篇(2015-2020) 设问思维分布(子题计数), 复用 cognitive_skill_by_content 的
    passage_label 回指桥接手法(cognitive_skill.py::_CROSS_SQL 同款 JOIN, 未重写逻辑)。

    排除 curriculum_aligned_task(七选五结构空): 无 passage_label 回指阅读四选一语篇,
    且联合归因问的是「四选一设问思维×词汇」, 不混语篇衔接任务。
    """
    rows = con.execute(
        "SELECT 'question:'||json_extract_string(nq.attrs_json,'$.passage_label') AS pid, "
        "       ns.label AS skill "
        "FROM edges e "
        "JOIN nodes nq ON nq.concept_id = e.src_id "
        "JOIN nodes ns ON ns.concept_id = e.dst_id "
        "WHERE e.relation='tests_exam_point' AND json_extract_string(e.evidence_json,'$.dimension')='cognitive_skill' "
        "AND json_extract_string(e.evidence_json,'$.provenance') <> 'curriculum_aligned_task' "
        "AND COALESCE(json_extract_string(e.evidence_json,'$.exam_stage'),'gaokao')='gaokao' "
        "AND json_extract_string(nq.attrs_json,'$.passage_label') IS NOT NULL "
        "AND CAST(json_extract_string(e.evidence_json,'$.lineage.source_year') AS INT) "
        f"BETWEEN {scope.LIAONING_NATIONAL_PAPER_SINCE} AND {scope.ERA_BOUNDARY_YEAR - 1}"
    ).fetchall()
    out: dict[str, dict[str, int]] = {}
    for pid, skill in rows:
        d = out.setdefault(pid, {})
        d[skill] = d.get(skill, 0) + 1
    return out


def _passage_word_stage_mix(con: duckdb.DuckDBPyConnection, pids: list[str]) -> dict[str, dict]:
    """每语篇 tests_word 边的学段占比, 口径同 k12.tested_word_stage_distribution (at_stage 边)。"""
    if not pids:
        return {}
    qmarks = ",".join(["?"] * len(pids))
    rows = con.execute(
        f"SELECT e.src_id AS pid, COALESCE(SUBSTR(es.dst_id,7),'未分类') AS stage "
        "FROM edges e LEFT JOIN edges es ON es.src_id = e.dst_id AND es.relation='at_stage' "
        f"WHERE e.relation='tests_word' AND e.src_id IN ({qmarks})",
        pids,
    ).fetchall()
    counts: dict[str, dict[str, int]] = {}
    for pid, stage in rows:
        d = counts.setdefault(pid, {})
        d[stage] = d.get(stage, 0) + 1
    out = {}
    for pid, d in counts.items():
        tot = sum(d.values())
        out[pid] = {
            "n_words": tot,
            "foundation_pct": round(100 * sum(d.get(s, 0) for s in _FOUNDATION_STAGES) / tot, 1),
            "senior_pct": round(100 * sum(d.get(s, 0) for s in _SENIOR_STAGES) / tot, 1),
            "unclassified_pct": round(100 * d.get("未分类", 0) / tot, 1),
        }
    return out


def _by_dominant_skill(passages: list[dict]) -> dict[str, dict]:
    """按每篇语篇的主导设问技能(子题数最多的技能)分组, 看该组语篇的平均词汇学段占比是否有差异
    —— 直接回应"推断题占比高的文章, 是不是词汇也更难"这个问题(实测: 不是, 见下方数值)。
    """
    groups: dict[str, list[float]] = {}
    for p in passages:
        if not p["word_stage_mix"]:
            continue
        dom = max(p["skill_dist"].items(), key=lambda kv: kv[1])[0]
        groups.setdefault(dom, []).append(p["word_stage_mix"]["senior_pct"])
    out = {}
    for skill, vals in groups.items():
        out[skill] = {
            "n_passages": len(vals),
            "avg_word_senior_pct": round(sum(vals) / len(vals), 1),
            "thin": len(vals) < 10,
        }
    return out


def joint_attribution_by_passage(con: duckdb.DuckDBPyConnection) -> dict:
    """语篇级联合归因主入口. 返回每篇语篇的 {skill_dist, word_stage_mix} + 按主导技能分组的
    词汇学段对比(by_dominant_skill) + 样本量诚实标注(坑12: 分布门槛, <MIN_DISTRIBUTION_SAMPLE 标 thin)。
    """
    skill_dist = _passage_skill_dist(con)
    pids = sorted(skill_dist.keys())
    word_mix = _passage_word_stage_mix(con, pids)

    passages = []
    for pid in pids:
        n_subq = sum(skill_dist[pid].values())
        passages.append({
            "passage_id": pid,
            "n_subq": n_subq,
            "skill_dist": skill_dist[pid],
            "word_stage_mix": word_mix.get(pid),
        })
    n_with_word = sum(1 for p in passages if p["word_stage_mix"])
    return {
        "era": scope.ERA_OLD,
        "province_scope": "辽宁卷",
        "granularity": "语篇级(passage) — tests_word 边挂语篇层级, cognitive_skill 边挂子题层级, 无法做到子题级归因",
        "excluded_dimension_note": (
            "语法学段(tests_grammar×cognitive_skill)已实测排除: tests_grammar 只标语法填空/"
            "短文改错, cognitive_skill 只标阅读理解, question_type 完全不相交, 结构性不可能对齐"
        ),
        "n_passages": len(passages),
        "n_passages_with_word_data": n_with_word,
        "reliability_note": (
            f"n={len(passages)}篇" +
            ("" if len(passages) >= scope.MIN_DISTRIBUTION_SAMPLE
             else f"(<{scope.MIN_DISTRIBUTION_SAMPLE}, 仅方向性非精确分布, 坑12)")
        ),
        "by_dominant_skill": _by_dominant_skill(passages),
        "passages": passages,
    }


# ---- 完形填空"得分点词"学段分布 (2026-07-07, 用户追问"得分点是高中词汇还是初中词汇") ----
# 上面 joint_attribution_by_passage 答的是"整篇词汇难度 × 设问思维"; 这里答字面版本:
# "每空唯一正确答案词"本身的难度, 与同批语篇全篇词汇难度基线对比, 是否系统性更难。

_CLOZE_OPT_LINE = re.compile(
    r"\d+\.\s*A\.\s*(.*?)\s*B\.\s*(.*?)\s*C\.\s*(.*?)\s*D\.\s*(.*?)(?=\s*\d+\.\s*A\.|\s*$)",
    re.DOTALL,
)
_ANS_LETTER_RE = re.compile(r"[A-D]")
_ROOT = Path(__file__).resolve().parents[3]
_EOL_CLOZE_OPTS = _ROOT / "data/structured/exam_point/cloze_options_eol_xgkii.jsonl"
_EOL_FRAGMENTED_PREFIX = re.compile(r"^eol/(2021|2022)/xgkii/\d+$")


def parse_cloze_options(raw: str) -> list[tuple[str, str, str, str]]:
    """完形填空 raw_question 选项内联在题面文本里(非 options_json 字段), 逐空解析 A/B/C/D。"""
    m0 = re.search(r"\d+\.\s*A\.", raw or "")
    if not m0:
        return []
    return _CLOZE_OPT_LINE.findall(raw[m0.start():])


def _load_eol_cloze_option_rebuilds() -> list[tuple[str, int, list, list[str]]]:
    """2021/2022 逐空拆行完形: 从 EOL docx 重建的选项 sidecar 合成整篇行。"""
    if not _EOL_CLOZE_OPTS.exists():
        return []
    out: list[tuple[str, int, list, list[str]]] = []
    for ln in _EOL_CLOZE_OPTS.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        row = json.loads(ln)
        opts = [(o["A"], o["B"], o["C"], o["D"]) for o in row["options"]]
        letters = list(row["answers"])
        if len(opts) == len(letters) and len(letters) >= 10:
            out.append((row["question_id"], int(row["year"]), opts, letters))
    return out


def cloze_baseline_qids(qid: str) -> list[str]:
    """整篇基线 qid: 2021/2022 重建行展开为同卷 41–55 逐空 id(tests_word 挂在拆行上)。"""
    if not _EOL_FRAGMENTED_PREFIX.match(qid or ""):
        return [qid]
    prefix = "/".join(qid.split("/")[:3])
    return [f"{prefix}/{n}" for n in range(41, 56)]


def qualifying_cloze_rows(con: duckdb.DuckDBPyConnection) -> list[tuple[str, int, list, list[str]]]:
    """辽宁完形填空里"选项文本完整 + 可与 answer 字母数对齐"的整篇行。

    内联选项行(2015–2020 / 2023+)直接从 exam_questions 解析; 2021/2022 原逐空拆行、
    选项未一致内联, 改由 cloze_options_eol_xgkii.jsonl(EOL docx 重建)合成整篇行纳入
    (n_passages 10→12)。跳过 DB 中仍拆行的 eol/2021|2022 单空, 避免与重建行重复计数。
    """
    out: list[tuple[str, int, list, list[str]]] = []
    seen: set[str] = set()
    rows = con.execute(
        "SELECT question_id, year, raw_question, answer FROM exam_questions "
        "WHERE question_type='完形填空' AND province LIKE '辽宁%'"
    ).fetchall()
    for qid, year, raw, ans in rows:
        if _EOL_FRAGMENTED_PREFIX.match(qid or ""):
            continue
        letters = _ANS_LETTER_RE.findall(ans or "")
        opts = parse_cloze_options(raw)
        if len(opts) == len(letters) and len(letters) >= 10:
            out.append((qid, year, opts, letters))
            seen.add(qid)
    for qid, year, opts, letters in _load_eol_cloze_option_rebuilds():
        if qid not in seen:
            out.append((qid, year, opts, letters))
            seen.add(qid)
    return out


def _word_stage_map(con: duckdb.DuckDBPyConnection) -> dict[str, str]:
    """word: 节点 at_stage 学段表, 同 k12.tested_word_stage_distribution 口径。"""
    rows = con.execute(
        "SELECT src_id, dst_id FROM edges WHERE relation='at_stage' AND src_id LIKE 'word:%'"
    ).fetchall()
    return {src[5:]: dst[6:] for src, dst in rows}


def _classify_answer_word(text: str, lemm, stage_map: dict[str, str]) -> str | None:
    """得分点词(可能多词短语)学段判定: 短语内任一实词命中高中档即判 senior(卡最难成分),
    否则任一命中基础档判 foundation, 都不命中判 None。

    WordNetLemmatizer 只处理屈折形态(单复数/时态), 不处理派生形态(painful/completely 这类),
    与 links_extra.build_tests_word 用的 _lemma_tokens 同一限制, 非本函数新引入的缺口。
    """
    stages = []
    for w in re.split(r"\s+", text.strip()):
        w = w.strip(".,;:").lower()
        if not w:
            continue
        for cand in (w, lemm.lemmatize(w, "v"), lemm.lemmatize(lemm.lemmatize(w, "v"), "n")):
            if cand in stage_map:
                stages.append(stage_map[cand])
                break
    if not stages:
        return None
    if any(s in _SENIOR_STAGES for s in stages):
        return "senior"
    if any(s in _FOUNDATION_STAGES for s in stages):
        return "foundation"
    return "other"


def _whole_passage_stage_pct(con: duckdb.DuckDBPyConnection, qids: list[str]) -> dict | None:
    """同一批语篇的全篇词汇学段占比(tests_word 边), 作为得分点词的对比基线。"""
    if not qids:
        return None
    qmarks = ",".join(["?"] * len(qids))
    rows = con.execute(
        f"SELECT COALESCE(SUBSTR(es.dst_id,7),'未分类') AS stage "
        "FROM edges e LEFT JOIN edges es ON es.src_id = e.dst_id AND es.relation='at_stage' "
        f"WHERE e.relation='tests_word' AND e.src_id IN ({qmarks})",
        [f"question:{q}" for q in qids],
    ).fetchall()
    tot = len(rows)
    if not tot:
        return None
    f = sum(1 for (s,) in rows if s in _FOUNDATION_STAGES)
    sr = sum(1 for (s,) in rows if s in _SENIOR_STAGES)
    return {"n_words": tot, "foundation_pct": round(100 * f / tot, 1), "senior_pct": round(100 * sr / tot, 1)}


def _era_answer_word_summary(con: duckdb.DuckDBPyConnection, lemm, stage_map: dict[str, str],
                              rows_for_era: list) -> dict:
    """单个 era 内: 得分点词学段占比 + 同批语篇全篇基线对比 (坑12 分层不取平均, 不跨 era 合并)。"""
    blanks: list[str | None] = []
    for _qid, _year, opts, letters in rows_for_era:
        for i, opt4 in enumerate(opts):
            text = opt4[ord(letters[i]) - ord("A")].strip()
            blanks.append(_classify_answer_word(text, lemm, stage_map))
    n_senior = sum(1 for b in blanks if b == "senior")
    n_found = sum(1 for b in blanks if b == "foundation")
    n_classified = n_senior + n_found
    qids: list[str] = []
    for qid, *_ in rows_for_era:
        for q in cloze_baseline_qids(qid):
            if q not in qids:
                qids.append(q)
    return {
        "n_passages": len(rows_for_era),
        "n_blanks_total": len(blanks),
        "n_blanks_classified": n_classified,
        "answer_word_senior_pct": round(100 * n_senior / n_classified, 1) if n_classified else None,
        "answer_word_foundation_pct": round(100 * n_found / n_classified, 1) if n_classified else None,
        "whole_passage_baseline": _whole_passage_stage_pct(con, qids),
    }


def cloze_answer_word_stage(con: duckdb.DuckDBPyConnection) -> dict:
    """完形填空"得分点词"(每空唯一正确答案词)学段分布, 对比同批语篇全篇词汇学段基线。

    回答用户"75%词汇是初中及以前, 但得分点是不是靠高中词汇"的字面版本: 得分点=正确答案词本身
    的难度(非整篇混合词汇难度)。范围: 12 篇(2015-2020 旧课标II 6 + 2021/2022 EOL docx
    选项重建 2 + 2023–2026 新高考II 4); 见 qualifying_cloze_rows。

    分层不取平均(坑12): 按 scope.segment(year) 分 era 各自算 by_era, 不跨 era 合并百分比。
    """
    from nltk.stem import WordNetLemmatizer

    lemm = WordNetLemmatizer()
    stage_map = _word_stage_map(con)
    rows = qualifying_cloze_rows(con)

    by_era: dict[str, dict] = {}
    for era in sorted({scope.segment(year) for _, year, _, _ in rows}):
        rows_for_era = [r for r in rows if scope.segment(r[1]) == era]
        by_era[era] = _era_answer_word_summary(con, lemm, stage_map, rows_for_era)

    return {
        "province_scope": "辽宁卷",
        "question_type": "完形填空",
        "n_passages": len(rows),
        "excluded_source_note": (
            "2021/2022 已由 cloze_options_eol_xgkii.jsonl(EOL docx 选项重建)纳入; "
            "exam_questions 仍保留逐空拆行, 不与重建整篇行重复计数"
        ),
        "coverage_note": (
            "WordNetLemmatizer 只处理屈折形态(单复数/时态), 不处理派生形态(painful/completely 类), "
            "与 links_extra.build_tests_word 同一限制; 各 era n_blanks_total-n_blanks_classified 即未分类数"
        ),
        "by_era": by_era,
    }
