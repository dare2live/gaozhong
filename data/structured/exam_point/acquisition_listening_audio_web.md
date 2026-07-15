# 辽宁卷听力音频全网查找 (2026-07-15，升档后更新)

## 结论

| 年 | 卷面关系 | 正式音频 | 状态 |
|---|---|---|---|
| 2021 | I&II 共用 | `data/audio/2021/listening/full.mp3` | **teachable_file** · 第三方指纹 PASS |
| 2022 | I&II 共用 | `data/audio/2022/listening/{short_all,dialog_01..04,passage_01}.mp3` | 同上 |
| 2023 | I&II 共用 | `data/audio/2023/listening/...` | 同上 |
| 2024 | II 单独 | `data/audio/2024/listening/...` | 同上 |
| 2025 | II | `data/audio/2025/listening/full.mp3` | 同上 |
| 2026 | 全国二卷 | `data/audio/2026/listening/full.mp3` | 同上 |

- `audio_config.years_with_audio=[2021..2026]`
- `module_status=third_party_fingerprint_verified`
- provenance **非 NEEA**；候选原件仍在 `listening_candidates/`（gitignored mp3）
- 指纹报告: `listening_audio_transcript_fingerprint.md`
- 播放: `/api/listening/file?year=2021&id=full` · 目录 `/api/listening/catalog`

## 升档命令

```bash
python3 -m scripts.tools.map.promote_listening_audio
python3 -m scripts.tools.map.attach_listening_audio_to_qbank
```
