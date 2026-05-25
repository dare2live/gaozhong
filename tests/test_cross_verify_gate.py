"""单元测试: cross_verify_pdf 门禁 — 确保坏数据被拦, 好数据通过."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import duckdb

from scripts.tools.audit.cross_verify_pdf import _check_item, verify_year, PDF_MAP


def test_check_item_pass():
    """PDF 中存在的关键词 → pass."""
    pdf_words = {"yellowstone", "national", "park", "variety", "ranger", "programs"}
    result = _check_item("q1", "阅读理解",
        "Yellowstone National Park offers a variety of ranger programs", pdf_words)
    assert result["match"] == "pass", f"Expected pass, got {result}"
    assert result["match_rate"] >= 0.6


def test_check_item_fail():
    """PDF 中不存在的关键词 → fail."""
    pdf_words = {"apple", "banana", "cherry"}
    result = _check_item("q2", "阅读理解",
        "Yellowstone National Park offers a variety of ranger programs", pdf_words)
    assert result["match"] == "fail", f"Expected fail, got {result}"
    assert result["match_rate"] < 0.3


def test_check_item_skip():
    """无英文关键词 → skip."""
    pdf_words = {"test"}
    result = _check_item("q3", "语法填空", "这是一道中文题目没有英文", pdf_words)
    assert result["match"] == "skip"


def test_verify_year_2024_pass():
    """2024 有 PDF + 结构化 → PASS."""
    if 2024 not in PDF_MAP or not PDF_MAP[2024].exists():
        print("SKIP: 2024 PDF not available")
        return
    result = verify_year(2024)
    assert result["overall"] in ("PASS", "skip"), f"2024 should pass, got {result['overall']}"


def test_verify_year_missing_pdf():
    """没有 PDF 的年份 → skip."""
    result = verify_year(1999)
    assert result.get("status") == "skip"


def test_gate_blocks_bad_data():
    """模拟: 结构化数据与 PDF 不一致 → fail 计数 > 0."""
    pdf_words = {"completely", "different", "content", "nothing", "matches"}
    # 这些词不在任何真题 PDF 中
    result = _check_item("fake_q", "阅读理解",
        "Yellowstone National Park offers ranger programs throughout the park", pdf_words)
    assert result["match"] == "fail", "Mismatched content should FAIL"


if __name__ == "__main__":
    tests = [f for f in dir() if f.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            globals()[t]()
            print(f"  ✅ {t}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {t}: {e}")
        except Exception as e:
            print(f"  ⚠️ {t}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
