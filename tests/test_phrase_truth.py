"""tests_phrase human_verified loader."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb

from backend.services.exam_point import phrase_truth as pt


class TestPhraseTruth(unittest.TestCase):
    def _con(self):
        con = duckdb.connect(":memory:")
        con.execute(
            "CREATE TABLE nodes (concept_id VARCHAR PRIMARY KEY, node_type VARCHAR, "
            "label VARCHAR, attrs_json VARCHAR)"
        )
        con.execute(
            "CREATE TABLE edges (src_id VARCHAR, dst_id VARCHAR, relation VARCHAR, "
            "weight DOUBLE, evidence_json VARCHAR)"
        )
        return con

    def test_load_reuses_textbook_phrase_and_skips_missing_question(self):
        con = self._con()
        con.execute(
            "INSERT INTO nodes VALUES ('phrase:9cdcb01e','phrase','come up with',"
            "'{\"canonical\":\"come up with\",\"type\":\"verb_phrase\"}')"
        )
        con.execute(
            "INSERT INTO nodes VALUES ('question:q1','question','q1','{}')"
        )
        rows = [
            {
                "question_id": "q1",
                "blank_no": 12,
                "canonical": "come up with",
                "answer_surface": "come up with",
                "phrase_type": "phrasal_verb",
                "note": "reuse",
            },
            {
                "question_id": "missing",
                "blank_no": 1,
                "canonical": "show up",
                "phrase_type": "phrasal_verb",
                "note": "skip",
            },
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
            path = Path(f.name)
        with mock.patch.object(pt, "_CURATED", path):
            out = pt.load_tests_phrase(con)
        self.assertEqual(out["n_edges"], 1)
        self.assertEqual(out["n_skipped"], 1)
        dst = con.execute(
            "SELECT dst_id FROM edges WHERE relation='tests_phrase'"
        ).fetchone()[0]
        self.assertEqual(dst, "phrase:9cdcb01e")
        path.unlink()

    def test_summary_requires_human_verified(self):
        con = self._con()
        con.execute(
            "INSERT INTO edges VALUES ('question:q','phrase:p','tests_phrase',1.0,"
            "'{\"provenance\":\"bulk\"}')"
        )
        s = pt.tests_phrase_summary(con)
        self.assertFalse(s["pass"])


if __name__ == "__main__":
    unittest.main()
