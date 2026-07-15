# 辽宁卷听力音频全网查找 (2026-07-15)

## 结论（诚实）

| 年 | 卷面关系 | 本地候选音频 | 状态 |
|---|---|---|---|
| 2021 | I&II **共用听力**（多源称） | `2021_xgkii_listening_133ku_candidate.mp3` 整卷 ~15:00 | **candidate** — 未与 EOL 题干指纹交叉；勿升 teachable |
| 2022 | I&II **共用** | 可可英语 6 段 `2022_xgki_ii_kekenet_*.mp3` | **candidate** — 已镜像+sha256 |
| 2023 | I&II **共用** | 可可英语 6 段 `2023_xgki_ii_kekenet_*.mp3` | **candidate** — 已镜像+sha256 |
| 2024 | I / II **分卷**（II 单独） | 可可英语 6 段 `2024_xgkii_kekenet_*.mp3` | **candidate** — 已镜像+sha256 |
| 2025 | I / II 分卷 | 学科网/结网英语/百度盘付费包；**无开放直链** | **未入库** |
| 2026 | 全国二卷有教习网/学科网包 | 付费/网盘；**无开放直链** | **未入库** |

- NEEA / 省考试院：**无**个人可下的官方 MP3 门户。
- GitHub：**无**可用的新课标 II 听力 mp3 仓（仅有四六级/其它）。
- 本仓 `data/audio/{year}/` 仍 **0 文件** → `audio_config.years_with_audio=[]`，`module_status=extraction_gap_not_teachable` **不变**。
- 候选一律落 `data/external/exam_sources/listening_candidates/`，**禁止**未交叉核验就当真相源教。

## 已镜像清单

- Manifests: `*_kekenet_manifest.json`, `2021_xgkii_133ku_manifest.json`
- 2021 另：盘古文库直链 mp3（sha256 见 manifest）
- 既有隔离：`2021_new_gaokao_i_listening_sunedu.*`（I 卷标签，quarantine）

## 公开可跟链源（登记）

| 源 | URL | 说明 |
|---|---|---|
| 可可英语 2024 II 短对话 | https://m.kekenet.com/gaokao/202408/693798.shtml | +693800–804 长对话/独白 |
| 可可英语 2023 I&II | https://m.kekenet.com/gaokao/202408/693782.shtml | +693783–787 |
| 可可英语 2022 I&II | https://m.kekenet.com/gaokao/202209/659942.shtml | +659943–947 |
| 盘古 2021 II | https://www.133ku.com/doc/3663.html | 整卷 mp3 直链 |
| B站合集（播放非文件） | BV1X6421Z7bT 等 | 不可作 sha256 真相源 |
| 学科网/教习网/结网 | zxxk / 51jiaoxi / jwbl | 付费或百度盘，本次未抓 |

## 下一步（未做）

1. 用 2021 EOL 题干 / 答案键对 133ku 音频做听辨或 ASR 指纹（防 I/II 错挂）。
2. 2022–24 段音频与卷面 Text1–10 对齐后，再 copy 入 `data/audio/{year}/listening/` 并更新 `years_with_audio`。
3. 2025/2026：需人工网盘授权或付费源入库后再锁 sha256。
