# 听力文字稿 + 2025/2026 音频深挖 (2026-07-15)

## 文字稿能否拿到？

**能。** 公开页/教辅包有完整录音原文（Text 1–10），本仓已镜像候选：

| 年 | 文字稿本地 | 源 | 质量信号 |
|---|---|---|---|
| 2021 | `listening_transcripts/2021_xgki_ii_cpsenglish_transcript.md` | 柯帕斯 | Text=10, W:/M: 齐全 |
| 2022 | `2022_xgki_ii_cpsenglish_transcript.md` | 柯帕斯 | Text=10；与 kekenet 分段 ASR **PASS** |
| 2023 | `2023_xgki_ii_listening_transcript.md` | scribd 解析【原文】+百度文库 | I&II 共用；与 kekenet ASR **PASS** |
| 2024 | `2024_xgkii_netease_transcript.md` | 网易云电台介绍区 | II 卷；与 kekenet ASR **PASS** |
| 2025 | `2025_xgkii_newdu_listening_stem.txt` + `_analysis.txt` | 新都网 zip 内 docx | Text=10, W:=27+ |
| 2026 | `2026_national_ii_newdu_listening.txt`（另：sjds / renrendoc 对照） | 新都网 rar 内「答案+听力原文」docx | Text=10, W:=23 |

交叉对照：2025 renrendoc / 2026 sjds 开场句与 newdu 稿一致（如 2025 Baxley bus；2026 picnic/Rose）。2022–24 见指纹报告。

## 2025–26 音频（此前标「仅付费」——已打穿）

| 年 | 包 | 开放直链 | 本地 mp3 | 时长 |
|---|---|---|---|---|
| 2025 II | newdu zip | `pic01.newdu.com/.../qgej2025061101.zip` | `2025_xgkii_listening_newdu_candidate.mp3` | ~18:53 |
| 2026 II | newdu rar | `pic01.newdu.com/.../2026gaokao2026061201.rar` | `2026_national_ii_listening_newdu_candidate.mp3` | ~22:45 |

sha256 见 `*_newdu_manifest.json` + `sources.yaml`。

诚实保留：
- 非 NEEA 官方发布口；仍是民间聚合镜像
- 2026 答案稿文件名含「听力原文2025.06.11」字样 → **candidate**；ASR 指纹已证正文与 2026 音频对齐（见 `listening_audio_transcript_fingerprint.md`），文件名 anomaly 仍记档
- `years_with_audio` 仍 `[]`（可教门未开）

## 仍缺

- 升 teachable 前：全卷逐字/题号级 QC（当前 2021–26 均为锚点指纹 PASS）
- 可可英语网页双语稿仍被壳页挡住（已用 cpsenglish / scribd / 网易云 旁路入库）
