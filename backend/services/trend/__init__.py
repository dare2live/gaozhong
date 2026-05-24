"""trend package — 命题趋势分析. 从 trend.py 拆 (Rule 4 模块化).

  raw.py   原 词频/题型 count 统计 (raw data)
  model.py 4.3 真模型: 题型年趋势线性回归 + 词频年增长率 + 主题热度演化
"""
from .raw import word_freq_by_year, top_high_freq_words, type_freq_by_year, trend_summary
from .model import question_type_year_trend, vocab_year_growth, top_rising_words
