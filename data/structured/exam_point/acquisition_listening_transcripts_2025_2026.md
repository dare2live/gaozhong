# 听力文字稿 + 2025/2026 音频深挖 (2026-07-15)

## 文字稿能否拿到？

**能。** 公开页/教辅包有完整录音原文（Text 1–10），本仓已镜像候选：

| 年 | 文字稿本地 | 源 | 质量信号 |
|---|---|---|---|
| 2021 | `listening_transcripts/2021_xgki_ii_cpsenglish_transcript.md` | 柯帕斯 | Text=10, W:/M: 齐全 |
| 2022–24 | **暂缺入库文本** | 可可英语页有双语稿，但移动端/桌面抓取被壳页挡住（仅音频已镜像） | 音频在 `listening_candidates/` |
| 2025 | `2025_xgkii_newdu_listening_stem.txt` + `_analysis.txt` | 新都网 zip 内 docx | Text=10, W:=27+ |
| 2026 | `2026_national_ii_newdu_listening.txt`（另：sjds / renrendoc 对照） | 新都网 rar 内「答案+听力原文」docx | Text=10, W:=23 |

交叉对照：2025 renrendoc / 2026 sjds 开场句与 newdu 稿一致（如 2025 Baxley bus；2026 picnic/Rose）。

## 2025–26 音频（此前标「仅付费」——已打穿）

| 年 | 包 | 开放直链 | 本地 mp3 | 时长 |
|---|---|---|---|---|
| 2025 II | newdu zip | `pic01.newdu.com/.../qgej2025061101.zip` | `2025_xgkii_listening_newdu_candidate.mp3` | ~18:53 |
| 2026 II | newdu rar | `pic01.newdu.com/.../2026gaokao2026061201.rar` | `2026_national_ii_listening_newdu_candidate.mp3` | ~22:45 |

sha256 见 `*_newdu_manifest.json` + `sources.yaml`。

诚实保留：
- 非 NEEA 官方发布口；仍是民间聚合镜像
- 2026 答案稿文件名含「听力原文2025.06.11」字样 → **candidate**，升 `data/audio` 前必指纹
- `years_with_audio` 仍 `[]`（可教门未开）

## 仍缺

- 2022–24 **入库文字稿**（可可见面人工另存 / 或后续 ASR 对齐已有分段 mp3）
- 全部年份：题干↔音频指纹后才能改 teachable
