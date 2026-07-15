# 听力音频 ↔ 文字稿一致性指纹审计

date: 2026-07-15（含 2022–24 补核）  
method: `faster-whisper` (`tiny.en`) 切片/分段 ASR + 专有名词锚点  
script: `scripts/tools/audit/listening_audio_transcript_fingerprint.py`  
machine: `listening_audio_transcript_fingerprint.json`  
full ASR dump (2022–24 分段): `listening_2022_2024_asr_dump.json`  
scope: **指纹一致，不是逐字 force-align**；不打开 `years_with_audio` teachable 门。

## 总表

| 年 | 音频候选 | 仓内文字稿 | 指纹结论 | 听写核对要点 |
|---|---|---|---|---|
| 2021 | 133ku full | cpsenglish | **PASS** | Spanish / lab report / Davidson |
| 2022 | kekenet 6 段 | cpsenglish（新入库） | **PASS** | parking / Judy flight / Tracy Woods / Emma Wilson·UBC |
| 2023 | kekenet 6 段 | scribd+百度文库整理（新入库） | **PASS** | camping·cinema / convenience store / yard sale·Ashley / The Idler |
| 2024 | kekenet 6 段 | 网易云电台稿（新入库） | **PASS** | talent show / Smiths / Brown’s Grill·Anderson / Rochester |
| 2025 | newdu full | newdu stem | **PASS** | yellow taxi·Bus No.4 / Creative Day·Mini Camp |
| 2026 | newdu full | sjds/newdu | **PASS** | picnic·Rose / Swansea / Melbourne·Eureka |

## 2022–24「自己听」怎么做的

此前缺仓内金标文稿，故标 N/A。本次：

1. 用 ASR **整段听写**可可英语 18 个分段 mp3 → `listening_2022_2024_asr_dump.json`
2. 网上取金标/准金标原文入库：
   - 2022：柯帕斯 cpsenglish article/1073
   - 2023：新课标 I/II 共用稿（scribd 解析【原文】+ baidu word）
   - 2024：网易云节目 `program?id=3057211543` 介绍区全文
3. 锚点交叉：短对话 + 长对话/独白各至少 1 窗 → 全部 HIT

ASR 与文稿几乎逐句同剧情（tiny 偶发专名误听：如 Mallorca→my York、Mark→Bob），不影响卷别指纹判定。

## 仍不升级 teachable

第三方候选 ≠ NEEA；指纹 ≠ 全卷逐字/题号 QC；`years_with_audio` 仍 `[]`。

## 复跑

```bash
/tmp/gaozhong_asr_venv/bin/python \
  scripts/tools/audit/listening_audio_transcript_fingerprint.py tiny.en
```
