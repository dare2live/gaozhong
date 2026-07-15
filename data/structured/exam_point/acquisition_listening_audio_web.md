# 辽宁卷听力音频全网查找 (2026-07-15)

## 结论（诚实）

| 年 | 卷面关系 | 本地候选音频 | 状态 |
|---|---|---|---|
| 2021 | I&II **共用听力**（多源称） | `2021_xgkii_listening_133ku_candidate.mp3` 整卷 ~15:00 | **candidate** — ASR 指纹 vs cpsenglish **PASS**；仍勿升 teachable |
| 2022 | I&II **共用** | 可可英语 6 段 `2022_xgki_ii_kekenet_*.mp3` | **candidate** — ASR 指纹 vs cpsenglish **PASS** |
| 2023 | I&II **共用** | 可可英语 6 段 `2023_xgki_ii_kekenet_*.mp3` | **candidate** — ASR 指纹 vs 入库稿 **PASS** |
| 2024 | I / II **分卷**（II 单独） | 可可英语 6 段 `2024_xgkii_kekenet_*.mp3` | **candidate** — ASR 指纹 vs 网易云稿 **PASS** |
| 2025 | I / II 分卷 | **新都网 zip 已下** 整卷 mp3(~18:53)+原文 docx | **candidate** — ASR 指纹 vs newdu 稿 **PASS** |
| 2026 | 全国二卷 | **新都网 rar 已下** 整卷 mp3(~22:45)+原文 docx | **candidate** — ASR 指纹 vs sjds/newdu **PASS**（稿名 2025.06.11 caveat 仍保留） |

文字稿进度见 `acquisition_listening_transcripts_2025_2026.md`。  
音频↔文稿指纹报告：`listening_audio_transcript_fingerprint.md`（2021–26 全 PASS）。

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

1. ~~2021/2025/2026 ASR 指纹~~ → PASS。
2. ~~2022–24 入库文字稿 + ASR 指纹~~ → PASS（见 `listening_audio_transcript_fingerprint.md`）。
3. 若要升 teachable：全卷逐字/题号级 QC + 产品明确授权（第三方候选 ≠ NEEA）。
