"""D0 unit_vocab_intro.zh_def 内容质量校验 (坑17: 全数据审计发现此前零覆盖, 2026-07-04 补).

背景: zh_def 只测过规模/覆盖率(见 data_accuracy_check._check_2_vocab), 从未测过内容质量
(专有名词/派生词跨行文本渗入前一词条)。unit_vocab_intro 是**原始提取层**, PUA 音标乱码
按架构本就该在此层出现、由下游 glossary._clean_zh_def 清洗进 word_glosses 时才要求零残留
(已有 truth_baseline/truth_gloss.py._pua_count 断言覆盖清洗后表, 此处不重复对原始层判零PUA
——那不是这层的不变量)。本门锁的是"内容边界正确性": renjiao 提取器(vocab_renjiao.py)
修复"专有名词/派生词跨行被误吸入前词zh_def"后, 污染行(zh_def>100字符, 强关联多词条混入)
从 32 条降到 4 条残留(专有名词无IPA段/空IPA"//"两类边缘case, 诊断性质, 非未知未测);
锁上界防回归(不追零, 追零需处理任意多PDF排版边缘case, 产出比递减, 见 mio 协议 #3.6)。
"""
from __future__ import annotations

import duckdb


def check_vocab_quality(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (38) unit_vocab_intro.zh_def 内容质量 (专有名词/派生词跨行渗入防回归) ===")
    # 2026-07-04 坑: vocab_renjiao.py 修复"专有名词/派生词跨行被误吸入前词zh_def"后,
    # renjiao 污染(zh_def>100字符, 强关联多词条混入一条)从 32→4(残留=专有名词无IPA段/
    # 空IPA"//"两类边缘case, 诊断性质, 非未知未测)。锁上界(不追零), 回升说明提取逻辑退化。
    n_long_renjiao = con.execute(
        "SELECT COUNT(*) FROM unit_vocab_intro WHERE version_key='renjiao' AND LENGTH(zh_def) > 100"
    ).fetchone()[0]
    check("renjiao zh_def 超长(>100字符, 疑多词条混入)残留 ≤10 (已从32条修复到4条, 锁上界防回归)",
          n_long_renjiao <= 10, f"{n_long_renjiao} 条")
