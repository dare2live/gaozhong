#!/usr/bin/env python3
"""修复答案 B 偏 — 自动重排选项使 ABCD 均匀分布 (P11 合规).

读 listening_exercises.yaml / reading_exercises.yaml,
对每道 MC 题重排选项, 使正确答案循环分配到 A/B/C/D.
"""
import re
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ["A", "B", "C", "D"]


def fix_yaml(path: Path) -> int:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    fixed = 0
    q_index = [0]

    def fix_item(item):
        stem = item.get("stem", "")
        answer = (item.get("answer") or "").strip()
        if answer not in TARGETS:
            return
        options = re.findall(r"([A-D])\.\s*(.+?)(?=\s+[A-D]\.|$)", stem, re.DOTALL)
        if len(options) < 3:
            return
        correct_text = None
        for label, text in options:
            if label == answer:
                correct_text = text.strip()
                break
        if not correct_text:
            return
        target_pos = TARGETS[q_index[0] % 4]
        q_index[0] += 1
        if target_pos == answer:
            return
        texts = [t.strip() for _, t in options]
        correct_idx = next(i for i, (l, _) in enumerate(options) if l == answer)
        texts.pop(correct_idx)
        target_idx = TARGETS.index(target_pos)
        texts.insert(target_idx, correct_text)
        new_stem_lines = []
        for line in stem.split("\n"):
            if re.match(r"^\s*[A-D]\.", line.strip()):
                continue
            new_stem_lines.append(line)
        base_stem = "\n".join(new_stem_lines).rstrip()
        option_str = "\n".join(f"      {TARGETS[i]}. {texts[i]}" for i in range(len(texts)))
        item["stem"] = base_stem + "\n" + option_str + "\n"
        item["answer"] = target_pos
        nonlocal fixed
        fixed += 1

    for key in data:
        if isinstance(data[key], list):
            for item in data[key]:
                if "questions" in item:
                    for q in item["questions"]:
                        fix_item(q)
                else:
                    fix_item(item)

    path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False, width=200), encoding="utf-8")
    return fixed


def main():
    for name in ["listening_exercises.yaml", "reading_exercises.yaml"]:
        path = ROOT / "backend" / "config" / name
        if not path.exists():
            print(f"  SKIP {name}: not found")
            continue
        n = fix_yaml(path)
        print(f"  {name}: {n} questions rebalanced")

    print("\n验证: 重建 DB 后跑 answer distribution check")


if __name__ == "__main__":
    main()
