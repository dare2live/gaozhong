"""考点 canonical 维度 (件2 拱心石) — genre/theme/设问/语法考点 落 nodes+edges.

单一计算点(Rule 1): 考点分布只从 edges 算一次; Edges一等公民(Rule 3): question↔考点走 edges。
"""
from .loader import (load_exam_points, exam_point_distribution, exam_point_shift,
                     bridge_exam_point_themes)
from .cooccur import exam_point_cooccurrence, materialize_cooccurrence
from .cognitive_skill import (load_cognitive_skill, cognitive_skill_distribution,
                              cognitive_skill_by_content)
from .cognitive_seven_choose_five import structure_subtype_distribution
from .attribution import joint_attribution_by_passage, cloze_answer_word_stage
from .senior_knowledge import (grammar_structural_coverage, phrase_pattern_exam_relevance,
                               cloze_collocation_structural_subset)
from .k12_bridge import junior_senior_grammar_bridge

from .genre_truth import analysis_genre_crosscheck, upgrade_cross_verified
