"""中考语篇 genre/theme 分类 → exam_point 节点 + tests_exam_point 边 (Phase E3b).

数据现状(2026-07-07, workflow双独立视角分类 + 主线程核实): 中考真题里只对2025年6种题型的
8篇真实文章做过分类(彼时2024全walled无文本, 见 junior/qbank.py docstring)。2026-07-08
2024题面已转真(4篇阅读理解A-D), 但genre/theme分类范围维持2025的8篇不变——这是独立的
scope边界(该分类需workflow双独立视角判断, 非机械数据流转; 是否扩到2024留独立任务,
不因walled解除自动扩大范围, 防止未经判断质量把关的范围膨胀)。8篇里1篇(养老院唱歌故事)
两个独立视角对theme判断不一致(社会服务与人际沟通 vs 做人与做事, 两种读法都站得住, 是真实的
边界模糊非误判), 诚实排除标needs_review; 其余7篇(覆盖40道题, 2025全45题的绝大多数)genre+
theme(L1三大范畴+L2十主题群, 义务教育课标2022taxonomy)完全一致才入库。

Rule1单一计算点: 复用 backend.services.exam_point.loader.load_exam_points 的懒建节点+
dual_model_agree过滤逻辑(该函数已参数化labels_path/theme_l2_path, 本模块是第2消费者),
不重新实现"落边"逻辑, 只传入初中artifact路径。

样本量诚实(坑12): 40题(7篇文章)相对2025全45题/全库90题是薄样本, 消费方(E4课程设计等)
不应把这7条边当频次驱动分配依据, 只作验证性附注。
"""
from __future__ import annotations

from pathlib import Path

from backend.services.exam_point.loader import load_exam_points

ROOT = Path(__file__).resolve().parents[5]
_LABELS_PATH = ROOT / "data" / "junior_high" / "structured" / "genre_theme_labels.jsonl"


def load(con) -> dict:
    """中考genre/theme边入库 (须在 junior/qbank.py::load() 之后调, question:ZK-% 节点需先存在)."""
    return load_exam_points(con, labels_path=_LABELS_PATH, theme_l2_path=_LABELS_PATH)
