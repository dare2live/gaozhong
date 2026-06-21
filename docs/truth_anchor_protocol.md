# 真值锚协议 — 数据准确性的"标准制定方法 + 标准 + 验证 + 持续完善"

> 根治: 三门(D0/moth/stop_gate)一直验"自洽"(计数==快照)不验"真值"(内容匹配第一手源),
> 形成**自洽棘轮**——污染入库后门永远绿(eol 2021/2022 误标辽宁, 6 次审计才靠 mirror 比对抓到)。
> 本协议把"真值校验"从一次性审计变成**模块化工具化系统**: `backend/services/truth_baseline/`(校验器)
> + `backend/config/truth_anchors.yaml`(锚注册表)+ `python3 -m scripts.tools.truth_check`(CLI)+ 接三门。

## 0. 仲裁标准 (以哪次为准 — 写死, 不再争)

**冲突时, 离第一手真相源最近的那次赢。** 任何"绿门 / 提交快照 / 我之前写的 lesson"都是二手货, 会撒谎。

真值层级 (tier): **S 官方源(教育部/课标 PDF/官方卷)> A 已验证镜像(verified_mirror)/原版教材 PDF > B 民间聚合 > 禁: LLM 单源 / 教辅 / 派生快照 / 库内自标。**
本次裁定: mirror(已验证辽宁新高考II卷)胜, eol 是污染源。

## 1. 方案 — 怎么制定一个真值标准 (立新锚答 5 问)

1. **第一手源在哪?** (官方卷 PDF / verified_mirror / 教材 PDF) — 填 `truth_anchors.yaml` 的 `provenance` + 源路径。
2. **markers 怎么钉?** 从第一手源抽**该域独有的内容指纹**(真题=标志性篇章专名如 `Take a view/rhino`; 课标=官方配额 1500/500/1000; 教材=每单元正文; 释义=禁止 markers 如 PUA/人名), 一次钉死即为常量真值。
3. **粒度?** 锚单元键 (真题=`年:省:卷型`; 课标=`vocab_quota`; 教材=`variant_units`)。
4. **无锚怎么标?** 没有第一手源的维度 → `lifecycle: no_anchor` → 校验报 **UNKNOWN, 不冒充已验证**(用户立法)。
5. **仲裁级别?** 默认第一手胜 (见 §0)。

## 2. 标准 — 门验真伪不验自洽

- 锚是**数据**(`truth_anchors.yaml`), 校验器是**通用引擎读锚**(judgment 数据化 §3.5)。
- 门断言"**库内容 ∩ 真值锚 markers**", **不是**"计数==快照"。例: 2021 辽宁库内容必须含 `Take a view/rhino`, 缺即 BLOCK(不管计数对不对)。
- **入库即对锚交叉, 单源不入**: 新真题入库点必跑 `truth_check --domain exam`, 不匹配真值锚不许入(§1.4 ≥2 源在**入库点**执行, 非事后审计)。

## 3. 验证标准 — 证明门真有效非装饰 (lifecycle 前置门)

- 每个 active 锚的校验器必过 `--self-test`: **注入污染必抓到 + 干净不误报**, 才许 `lifecycle: active`(否则是装饰门, 坑21)。
- `python3 -m scripts.tools.truth_check --self-test` 是 active 化的前置门。
- `--lint` 校验 `truth_anchors.yaml` 自身合法 (active 锚必有 markers)。

## 4. 持续完善 — 机制不是口号

- **加新域/新标准 = 加一个 checker + `CHECKERS` 追加 + yaml 加锚, 核心(base/CLI/门)一行不动**(模块化扩展; codegraph query CHECKERS 一把出全域)。
- 第一手源变了(教材换版/课标换版)→ markers 重新钉 + 锚降 `no_anchor` 待重验(防陈旧, 坑2)。
- `map doctor` 聚合 `truth_check --json`(真值偏差 + UNKNOWN 待补锚数)→ 推动补锚。

## 5. 工具接口

| 命令 | 作用 |
|---|---|
| `python3 -m scripts.tools.truth_check` | verify 全域: 库内容 ∩ 真值锚 |
| `... --strict` | 有 BLOCK → exit 1 (供门/CI) |
| `... --self-test` | 对抗自测 (active 前置门) |
| `... --lint` | 校验 yaml 合法 |
| `... --json` | 机读 (map doctor 聚合) |

## 6. 现状 (2026-06-20 建立)

- **exam 域已 active**: 2021/2023/2024 锚 (verified_mirror); 2022/2025 = no_anchor (mirror 无数据, 标 UNKNOWN)。
- **首验即抓红线①**: `verify` 报 `2021 辽宁内容≠真值锚(缺 Take a view/rhino)= eol 省份污染`; 旧 D0 同时仍绿 = **验真值≠验自洽 分水岭成立**。
- 替代 `scripts/tools/audit/truth_baseline_*`(731 行一次性软匹配报告脚本, 红队点名的反例)。
- **待续** (按此协议扩, 非一次性): 接 D0 门(需先修红线① eol 污染否则 D0 正确变红)→ 加 textbook 域(section 丢段红线②)→ 加 glossary 域(释义污染红线③)→ 课标配额域。
