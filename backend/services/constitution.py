"""设计宪法入库 + 运行时约束检查.

宪法 = 模型驱动内容生成的最高原则. 入 constitution 表, API 暴露, 前端展示.
任何内容生成前必须调 check_compliance() 获取当前有效约束.
"""
from __future__ import annotations

import duckdb

PRINCIPLES = [
    ("PRINCIPLE_1", "principle", "真题是唯一真理源",
     "一切内容合法性来自高考真题, 不来自教材/教参/感觉. S级=近5年真题, A级=课标, B级=教材, C级=生成内容.",
     "exam_pattern_extractor 提取 + trend_engine 分析", "§1.1"),
    ("PRINCIPLE_2", "principle", "模型先行, 内容后行",
     "先分析真题→输出命题模型→据此生成内容→模型审计验证. 禁止跳过模型直接生成.",
     "生成前必须 import constitution.check_compliance()", "§2"),
    ("PRINCIPLE_3", "principle", "细颗粒度建模",
     "每个考点独立建模: 提问句式/选项设计/线索类型. 按年份趋势+考点关联三维分析.",
     "exam_pattern_extractor 9 类考点 × 年份 × 关联", "§3"),
    ("PRINCIPLE_4", "principle", "模型审计闭环",
     "生成前审计(查模型) + 生成后审计(跑checker) + 模型自身审计(回测准确度).",
     "alignment_checker + ground_truth_validator + batch_regression_test", "§4"),
    ("PRINCIPLE_5", "principle", "持续学习",
     "每年6月新真题入库→模型刷新→淘汰旧内容→生成新内容. 模型不是一次性产出.",
     "年度循环: 入库→re-run→审计→淘汰→生成", "§5"),
    ("PRINCIPLE_6", "principle", "输出格式标准化",
     "模型每个输出都是结构化JSON, 生成的内容必须带 _generated_by metadata.",
     "JSON schema 验证", "§6"),
]

IRON_LAWS = [
    # --- 用户明确提出 ---
    ("P1", "iron_law", "年份权重递增",
     "2025(权重5)>2024(4)>2023(3)>2022(2)>2021(1.5)>旧(0.5). 趋势/频次/模板全部加权.",
     "trend_engine + pattern_extractor 必须用 year_weights", "§1.2"),
    ("P2", "iron_law", "命题趋势优先",
     "上升考点加大出题比重, 下降考点主动减少. 趋势比历史存量更重要.",
     "trend_engine slope 驱动生成优先级", "§1.3"),
    ("P3", "iron_law", "近年模板为准",
     "提问句式/干扰项/难度/选题以2023-2025真题为唯一模板.",
     "pattern_extractor 只取近3年数据作为生成约束", "§1.2+§1.3"),
    ("P4", "iron_law", "模型先行",
     "任何内容生成前, 先查 exam_patterns.json + trend_analysis.json.",
     "check_compliance() 前置调用", "§2"),
    ("P5", "iron_law", "审计闭环",
     "每批内容必过 alignment_checker + ground_truth_validator.",
     "stop_gate 集成", "§4"),
    ("P6", "iron_law", "持续更新",
     "每年新真题入库后 re-run 全套模型, 淘汰偏离旧内容.",
     "年度 re-run 脚本", "§5"),
    ("P7", "iron_law", "关联出题",
     "每个考点输出关联考点(同现矩阵), 不孤立出题.",
     "trend_engine cooccurrence 驱动", "§3.3"),
    ("P8", "iron_law", "可量化验证",
     "每条质量断言必须有数据支撑, 不接受'感觉'.",
     "所有 check 返回 score + evidence", "§1+§4"),
    # --- 命题深层规律 (从真题研究推导, 用户未明说但必须遵守) ---
    ("P9", "iron_law", "难度梯度对齐",
     "阅读A篇最易→D篇最难, 完形前易后难, 语法填空有提示→无提示. 难度梯度必须与真题一致, 不只看整体分布.",
     "per-position difficulty check", "§3.1"),
    ("P10", "iron_law", "干扰项诱惑度",
     "干扰项不是'随便错', 而是有设计: 偷换主语/过度推理/以偏概全/张冠李戴/无中生有. 每道题的干扰项设计策略必须标注.",
     "ground_truth_validator 检查干扰项设计标注", "§3.1"),
    ("P11", "iron_law", "答案位置均匀",
     "同一套卷中 ABCD 正确答案分布应近似均匀 (真题特征: 每选项约占 25%±5%). 生成题批量检查答案位置分布.",
     "alignment_checker 新增 answer_distribution 维度", "§3"),
    ("P12", "iron_law", "篇章结构匹配",
     "阅读/完形的文章结构(总分/递进/对比/问题-解决)分布必须与真题一致. 不能全是'总分'结构.",
     "pattern_extractor 提取文章结构分布", "§3.1"),
    ("P13", "iron_law", "语篇衔接信号词",
     "七选五/完形中的衔接词(however/therefore/for example/in addition)频率必须与真题一致. 这是命题的核心考查点.",
     "trend_engine 跟踪信号词频率变化", "§3.1"),
    ("P14", "iron_law", "考点跨题型一致",
     "同一考点在不同题型中的考法要一致: 如'非谓语'在语法填空考词形变化, 在完形考语境选择, 在阅读考长难句理解.",
     "cross_type_consistency check", "§3.3"),
    ("P15", "iron_law", "情感/话题真实分布",
     "续写的情感走向(困难→克服→成长)、阅读的话题(科技30%/社会25%/文化20%/自然15%/校园10%)必须与真题分布对齐.",
     "pattern_extractor 提取话题+情感分布", "§3.1"),
]

VIOLATIONS = [
    ("V1", "violation", "禁止: 跳过模型分析直接写题", "内容拒绝入库", "", ""),
    ("V2", "violation", "禁止: 凭感觉决定考点权重", "必须用 weighted slope + frequency", "", ""),
    ("V3", "violation", "禁止: 生成后不跑审计", "视为未完成, 不可 commit", "", ""),
    ("V4", "violation", "禁止: 忽略审计 fail 强行入库", "stop_gate 阻断", "", ""),
    ("V5", "violation", "禁止: 用旧模型指导新内容", "必须先 re-run 模型", "", ""),
    ("V6", "violation", "禁止: 人工内容免审", "人写/LLM写一视同仁, 全过审计", "", ""),
    ("V7", "violation", "禁止: 估算考点分布", "一切从真题计算, 不可估算", "", ""),
    ("V8", "violation", "禁止: 等权对待所有年份", "按 §1.2 权重表加权", "", ""),
]


def seed(con: duckdb.DuckDBPyConnection) -> dict:
    """灌入宪法条款到 constitution 表."""
    con.execute("DELETE FROM constitution")
    n = 0
    for i, (rid, rtype, title, desc, enf, ref) in enumerate(PRINCIPLES):
        con.execute(
            "INSERT INTO constitution VALUES (?,?,?,?,?,?,?)",
            [rid, rtype, title, desc, enf, ref, i],
        )
        n += 1
    for i, (rid, rtype, title, desc, enf, ref) in enumerate(IRON_LAWS, 100):
        con.execute(
            "INSERT INTO constitution VALUES (?,?,?,?,?,?,?)",
            [rid, rtype, title, desc, enf, ref, i],
        )
        n += 1
    for i, (rid, rtype, title, desc, enf, ref) in enumerate(VIOLATIONS, 200):
        con.execute(
            "INSERT INTO constitution VALUES (?,?,?,?,?,?,?)",
            [rid, rtype, title, desc, enf, ref, i],
        )
        n += 1
    return {"total": n, "principles": len(PRINCIPLES),
            "iron_laws": len(IRON_LAWS), "violations": len(VIOLATIONS)}


def load_all(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """读全部宪法条款."""
    rows = con.execute(
        "SELECT rule_id, rule_type, title, description, enforcement, ref_section "
        "FROM constitution ORDER BY sort_order"
    ).fetchall()
    return [{"rule_id": r[0], "rule_type": r[1], "title": r[2],
             "description": r[3], "enforcement": r[4], "ref_section": r[5]}
            for r in rows]


def check_compliance() -> dict:
    """内容生成前调用 — 返回当前有效约束 (铁律+年份权重)."""
    return {
        "year_weights": {2025: 5, 2024: 4, 2023: 3, 2022: 2, 2021: 1.5},
        "year_weights_old": 0.5,
        "trend_priority": True,
        "recent_template_years": [2023, 2024, 2025],
        "audit_required": True,
        "iron_laws": [f"{r[0]}: {r[2]}" for r in IRON_LAWS],
    }


def enforce_before_generation(con) -> dict:
    """生成前强制检查 — 不通过则 raise. 宪法 P4 程序化执行."""
    import json
    from pathlib import Path
    report_dir = Path(__file__).resolve().parents[1].parent / "data" / "reports"
    patterns_path = report_dir / "exam_patterns.json"
    trends_path = report_dir / "trend_analysis.json"
    errors = []
    if not patterns_path.exists():
        errors.append("exam_patterns.json 不存在 — 先跑 exam_pattern_extractor")
    if not trends_path.exists():
        errors.append("trend_analysis.json 不存在 — 先跑 trend_engine")
    if patterns_path.exists():
        pat = json.loads(patterns_path.read_text())
        if pat.get("data_gap"):
            errors.append(f"数据缺口: {pat['data_gap']} — 先补全真题数据")
    n_rules = con.execute("SELECT COUNT(*) FROM constitution").fetchone()[0]
    if n_rules < 20:
        errors.append(f"constitution 表只有 {n_rules} 条 — 先跑 init_db seed")
    if errors:
        raise ConstitutionViolation(errors)
    compliance = check_compliance()
    if trends_path.exists():
        trends = json.loads(trends_path.read_text())
        compliance["rising_points"] = [
            t["point"] for t in trends.get("trends", []) if t.get("direction") == "rising"
        ]
    return compliance


class ConstitutionViolation(Exception):
    """宪法违反 — 生成前检查未通过."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"宪法违反 ({len(errors)} 项): {'; '.join(errors)}")
