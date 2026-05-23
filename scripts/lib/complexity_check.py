"""Cyclomatic complexity for Python files (stdlib only — 不引 radon).

Usage:
  python3 scripts/lib/complexity_check.py <file.py> [<file.py>...]
  echo '/path/to/file.py' | python3 -m scripts.lib.complexity_check --stdin

Output (text):
  <file.py>:<lineno> <func_name> CC=<n>
  WARN ... if CC > THRESHOLD (default 10)
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

THRESHOLD = 10


# Decision-point AST nodes (each adds 1 to cyclomatic complexity).
DECISION_NODES = (
    ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp,
    ast.With, ast.AsyncWith,  # 仅 1 个 with item 不 +1, 多个时另算 (粗略)
    ast.ExceptHandler,
    ast.Assert,
    ast.comprehension,
    ast.Match,  # 3.10+
)


def cyclomatic(node: ast.AST) -> int:
    """McCabe complexity ≈ 1 + decision points. BoolOp(and/or) 加 (operand-1)."""
    cc = 1
    for sub in ast.walk(node):
        if isinstance(sub, DECISION_NODES):
            cc += 1
        elif isinstance(sub, ast.BoolOp):
            cc += max(0, len(sub.values) - 1)
        elif isinstance(sub, getattr(ast, "match_case", ())):
            cc += 1
    return cc


def analyze_file(path: Path) -> list[dict]:
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as e:
        return [{"path": str(path), "name": "(syntax_error)", "lineno": e.lineno, "cc": 0, "kind": "error",
                 "msg": str(e)}]
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append({"path": str(path), "name": node.name, "lineno": node.lineno,
                        "cc": cyclomatic(node), "kind": "function"})
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append({"path": str(path), "name": f"{node.name}.{sub.name}",
                                "lineno": sub.lineno, "cc": cyclomatic(sub), "kind": "method"})
    out.sort(key=lambda r: -r["cc"])
    return out


def format_text(rows: list[dict], threshold: int = THRESHOLD) -> str:
    lines: list[str] = []
    if not rows:
        return "(no functions)"
    for r in rows:
        marker = "  ⚠️ WARN" if r["cc"] > threshold else ""
        lines.append(f"  {r['path']}:{r['lineno']:>4d}  CC={r['cc']:>3d}  {r['name']}{marker}")
    n_warn = sum(1 for r in rows if r["cc"] > threshold)
    lines.append(f"  -- {len(rows)} funcs/methods, {n_warn} over CC>{threshold}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    threshold = THRESHOLD
    out_json = False
    files: list[Path] = []
    for a in argv[1:]:
        if a == "--json":
            out_json = True
        elif a.startswith("--threshold="):
            threshold = int(a.split("=", 1)[1])
        elif a == "--stdin":
            for line in sys.stdin:
                p = Path(line.strip())
                if p.exists() and p.suffix == ".py":
                    files.append(p)
        else:
            p = Path(a)
            if p.exists() and p.suffix == ".py":
                files.append(p)
    if not files:
        print("no .py files given", file=sys.stderr)
        return 1
    all_rows: list[dict] = []
    for f in files:
        all_rows.extend(analyze_file(f))
    if out_json:
        json.dump(all_rows, sys.stdout, ensure_ascii=False, indent=2)
    else:
        print(format_text(all_rows, threshold))
    # exit 0 always (advisory)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
