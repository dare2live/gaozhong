"""中考语篇 genre/theme 分类 → exam_point 节点 + tests_exam_point 边 (Phase E3b).

数据现状(2026-07-07起, workflow双独立视角分类 + 主线程核实): 2025年6种题型的8篇真实文章
分类(彼时2024全walled无文本)。8篇里1篇(养老院唱歌故事)两个独立视角对theme判断不一致
(社会服务与人际沟通 vs 做人与做事, 两种读法都站得住, 是真实的边界模糊非误判), 诚实排除
标needs_review; 其余7篇(覆盖40道题)genre+theme(L1三大范畴+L2十主题群, 义务教育课标
2022taxonomy)完全一致才入库。

2026-07-08续(用户拍板"中考自成体系但颗粒度应达高考标准, 摸出中考考查重点"): 2024年
题面转真后补做同款双独立视角分类, 覆盖4篇阅读理解A-D(Q1-16)。结果: B篇(Kelly渔村结识
Marie的记叙文)+D篇(Li介绍七巧板中国文化的记叙文)两视角genre+theme_l2完全一致(记叙文/
社会服务与人际沟通、记叙文/历史、社会与文化)入库; A篇(植物养护说明)genre一致(应用文)
但theme_l2分歧(生活与学习 vs 自然生态, 两种读法都站得住); C篇(舞蹈俱乐部访谈)genre分歧
(新闻报道 vs 记叙文, 对话体裁归类边界模糊)theme_l2一致(文学艺术与体育)——A/C按同一诚实
排除惯例不入库(不因一个维度一致就半采纳另一维度分歧的行, 同"1篇不一致整篇排除"惯例)。
现覆盖48题(2024新增8题Q5-8/13-16 + 2025原40题)。

Rule1单一计算点: 复用 backend.services.exam_point.loader.load_exam_points 的懒建节点+
dual_model_agree过滤逻辑(该函数已参数化labels_path/theme_l2_path, 本模块是第2消费者),
不重新实现"落边"逻辑, 只传入初中artifact路径。

样本量诚实(坑12): 48题(11篇文章)相对全库90题是薄样本, 消费方(E4课程设计/F2考点重点分析
等)不应把这些边当频次驱动分配依据, 只作验证性附注/静态分布, 不画趋势(2年数据不够, 见
zhongkao子系统scope note)。
"""
from __future__ import annotations

from pathlib import Path

from backend.services.exam_point.loader import load_exam_points

ROOT = Path(__file__).resolve().parents[5]
_LABELS_PATH = ROOT / "data" / "junior_high" / "structured" / "genre_theme_labels.jsonl"


def load(con) -> dict:
    """中考genre/theme边入库 (须在 junior/qbank.py::load() 之后调, question:ZK-% 节点需先存在)."""
    return load_exam_points(con, labels_path=_LABELS_PATH, theme_l2_path=_LABELS_PATH)
