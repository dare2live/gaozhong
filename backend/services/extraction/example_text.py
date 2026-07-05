"""共享文本裁剪工具 (Rule 5 可复用).

坑(2026-07-05 根因型全局审计): grammar_occurrences.example_sentence / question_bank.stem /
exam_questions.raw_question 同一批字段被 lesson_plan.py / syllabus.py / question_bank.py /
graph_popup.py / exam.py 等 ≥5 处独立调用点各写一份定长截断(120/160/200/90...不等), 无词/句边界
意识, 违反铁律1 单一计算点。收口于此, 各消费点复用, 不再各自发明截断逻辑。
"""
from __future__ import annotations

import re

_EXAMPLE_LETTER_RE = re.compile(r"\b[a-e]\b[^a-zA-Z]{0,3}[A-Z]")
_EXAMPLE_DISPLAY_MAX = 200


def clean_example(text: str | None) -> str | None:
    """语法例句: 无 a/b/c 字母编号例句模式 → 不展示(纯指令, 诚实降级);
    有则裁到最近句末标点(不截词中间)。是"完整摘录"非"预览", 故不加省略号。"""
    if not text or not _EXAMPLE_LETTER_RE.search(text):
        return None
    if len(text) <= _EXAMPLE_DISPLAY_MAX:
        return text
    clip = text[:_EXAMPLE_DISPLAY_MAX]
    end = max(clip.rfind("."), clip.rfind("!"), clip.rfind("?"))
    return clip[:end + 1] if end > 0 else clip


def clean_preview(text: str | None, max_len: int) -> str:
    """题干/原文预览: 裁到 max_len 内最近句末标点(不截词中间); 本就是"预览"(暗示后面还有),
    裁短了就统一补省略号, 没裁短(原文本就短)原样返回不加省略号。"""
    text = text or ""
    if len(text) <= max_len:
        return text
    clip = text[:max_len]
    end = max(clip.rfind("."), clip.rfind("!"), clip.rfind("?"))
    return (clip[:end + 1] if end > 0 else clip) + "…"
