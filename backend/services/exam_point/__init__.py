"""考点 canonical 维度 (件2 拱心石) — genre/theme/设问/语法考点 落 nodes+edges.

单一计算点(Rule 1): 考点分布只从 edges 算一次; Edges一等公民(Rule 3): question↔考点走 edges。
"""
from .loader import load_exam_points, exam_point_distribution, bridge_exam_point_themes
from .cooccur import exam_point_cooccurrence
