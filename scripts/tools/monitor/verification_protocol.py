#!/usr/bin/env python3
"""真人验证协议 — Gate 6 流程化. 生成验证清单 + 记录结果.

用法:
    python3 scripts/tools/monitor/verification_protocol.py --generate  # 生成验证清单
    python3 scripts/tools/monitor/verification_protocol.py --report    # 查看验证状态
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
PROTOCOL_PATH = ROOT / "data" / "reports" / "verification_protocol.json"

CHECKLIST = [
    {"id": "V1", "step": "摸底测验", "desc": "学生完成 G1/G2/G3 摸底测验, 系统推荐课节",
     "url": "/app#/students", "duration_min": 10},
    {"id": "V2", "step": "查看推荐课节", "desc": "点击推荐课节, 查看讲义内容",
     "url": "/app#/teaching", "duration_min": 5},
    {"id": "V3", "step": "上课 (讲义)", "desc": "阅读一节完整讲义 (7 段), 检查内容可读性",
     "url": "/app#/teaching → 点课节", "duration_min": 15},
    {"id": "V4", "step": "课后测验", "desc": "点击'课后测验'按钮, 完成 10 题, 系统批改",
     "url": "讲义 modal 底部", "duration_min": 10},
    {"id": "V5", "step": "听力练习", "desc": "进入 C tab, 播放听力, 展开原文, 做题",
     "url": "/app#/qbank", "duration_min": 10},
    {"id": "V6", "step": "查看弱点", "desc": "进入 E tab, 查看弱点分析 + 推送课节",
     "url": "/app#/students → 点学生", "duration_min": 5},
    {"id": "V7", "step": "知识图谱", "desc": "点击概念链接, 弹出关联图 + 真题",
     "url": "/app#/graph 或讲义内 concept link", "duration_min": 5},
    {"id": "V8", "step": "打印讲义", "desc": "点击打印按钮, 检查 PDF 输出",
     "url": "讲义 modal → 打印按钮", "duration_min": 3},
]


def generate_protocol() -> dict:
    """生成验证清单 JSON."""
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        stats = {
            "questions": con.execute("SELECT COUNT(*) FROM question_bank").fetchone()[0],
            "courses": con.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
            "students": con.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        }
    finally:
        con.close()
    protocol = {
        "generated_at": datetime.now().isoformat(),
        "system_stats": stats,
        "total_duration_min": sum(c["duration_min"] for c in CHECKLIST),
        "checklist": CHECKLIST,
        "results": {c["id"]: {"status": "pending", "feedback": "", "timestamp": ""} for c in CHECKLIST},
    }
    PROTOCOL_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROTOCOL_PATH.write_text(json.dumps(protocol, ensure_ascii=False, indent=2))
    return protocol


def report() -> dict:
    """读取验证状态."""
    if not PROTOCOL_PATH.exists():
        return {"error": "未生成验证清单, 先跑 --generate"}
    return json.loads(PROTOCOL_PATH.read_text())


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.generate:
        p = generate_protocol()
        print(f"验证清单已生成: {PROTOCOL_PATH}")
        print(f"共 {len(CHECKLIST)} 步, 预计 {p['total_duration_min']} 分钟")
        for c in CHECKLIST:
            print(f"  {c['id']}. {c['step']} ({c['duration_min']}min) — {c['desc']}")
    elif args.report:
        p = report()
        if "error" in p:
            print(p["error"]); return
        done = sum(1 for r in p["results"].values() if r["status"] == "done")
        print(f"验证进度: {done}/{len(CHECKLIST)}")
        for c in CHECKLIST:
            r = p["results"].get(c["id"], {})
            status = "✅" if r.get("status") == "done" else "🔲"
            print(f"  {status} {c['id']}. {c['step']}: {r.get('feedback', '待验证')}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
