"""项目地图 (project map) — 聚合模块/数据/gate/drift/stats 四套真相源的只读 CLI.

入口: python3 -m scripts.tools.map [doctor|modules|gates|drift|stats|data] [--json] [--strict]
纯只读聚合, 不改任何状态; 复用现有真相源不另起炉灶 (project_architecture.yaml / m0_gates.yaml /
moth assert / project_architecture_audit.py / read-only DB)。
"""
