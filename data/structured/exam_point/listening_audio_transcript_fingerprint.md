# 听力音频 ↔ 文字稿一致性指纹审计

date: 2026-07-15（升档后）  
method: `faster-whisper` (`tiny.en`) 切片/分段 ASR + 专有名词锚点  
script: `scripts/tools/audit/listening_audio_transcript_fingerprint.py`  
machine: `listening_audio_transcript_fingerprint.json`  
full ASR dump (2022–24 分段): `listening_2022_2024_asr_dump.json`

## 总表

| 年 | 正式目录 | 指纹 | 可教档 |
|---|---|---|---|
| 2021–26 | `data/audio/{year}/listening/` | **PASS** | `years_with_audio` 已开；`module_status=third_party_fingerprint_verified` |

## 升档说明

业主 2026-07-15 拍板：指纹 PASS 后升入正式目录并可播。

- 配置: `backend/config/audio_config.yaml`
- 升档脚本: `python3 -m scripts.tools.map.promote_listening_audio`
- 题库挂接(2021 Q1–20 + 2026 听力块): `python3 -m scripts.tools.map.attach_listening_audio_to_qbank`
- API: `/api/listening/catalog` · `/api/listening/file?year=&id=` · list/detail(`has_audio`)
- **诚实**: provenance=`third_party_not_neea`（非考试院官方发行口）

## 复跑指纹

```bash
/tmp/gaozhong_asr_venv/bin/python \
  scripts/tools/audit/listening_audio_transcript_fingerprint.py tiny.en
```
