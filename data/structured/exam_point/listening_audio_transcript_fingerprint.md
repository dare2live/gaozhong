# 听力音频 ↔ 文字稿一致性指纹审计

date: 2026-07-15  
method: `faster-whisper` (`tiny.en`) 切片 ASR + 专有名词/独特句锚点（含 ASR 模糊变体）  
script: `scripts/tools/audit/listening_audio_transcript_fingerprint.py`  
machine result: `data/structured/exam_point/listening_audio_transcript_fingerprint.json`  
scope: **指纹一致，不是逐字 force-align**；不因此打开 `years_with_audio` teachable 门。

## 总表

| 年 | 音频候选 | 仓内文字稿 | 指纹结论 | 说明 |
|---|---|---|---|---|
| 2021 | 133ku full mp3 (900s) | cpsenglish | **PASS** | Text1–2 开口与文稿同剧情；`Mallorca` 被 tiny 听成 `my York`，但 `Spanish` / `lab report` / `Dr. Davidson` 命中 |
| 2022 | kekenet 分段 | **无** | **N/A** | 短对话 ASR 可听（Judy/flight、邻居 thank-you note），无金标文稿可对 |
| 2023 | kekenet 分段 | **无** | **N/A** | 短对话 ASR 可听（train / Bob hospital / 账单退 $10），无金标文稿可对 |
| 2024 | kekenet 分段 | **无** | **N/A** | 短对话 ASR 可听（Smiths dinner / Denver / feed the cat），无金标文稿可对 |
| 2025 | newdu full mp3 (~18:53) | newdu stem/analysis + renrendoc | **PASS** | Text1：黄出租车 + Bus No.4（`Baxley` 被听成 `Fast Leech`）；Text10：`Creative Day School` / `Mini Camp` / ages 5–12 |
| 2026 | newdu full mp3 (~22:45) | newdu + sjds + renrendoc | **PASS** | Text1 picnic/Rose/Kevin；Text6 Swansea（ASR=`Swan Sea`）；Text10 Melbourne / Eureka / Book Thief |

## 关键证据（ASR 摘录）

### 2021 @90s（对照 cpsenglish Text1–2）
> I was in my York last week. … practice my Spanish. … hand in my lab report to Dr. Davidson?

### 2025 @40s（对照 stem Text1）
> Is this bus going to Fast Leech's sir? … yellow taxi on the corner? … take bus number four.

### 2025 @900s（对照 stem Text10）
> Welcome to the creative day school. … Mini Camp … ages 5 through 12 …

### 2026 @03:26 / @08:06 / @17:30（对照 sjds 时间戳）
> picnic … Rose … Kevin a birthday present  
> June 22 to Swan Sea … earlier flight  
> arrived in Melbourne … Rika Tower … Book Thief

## 文稿多源交叉（文本层）

- **2025**：newdu stem / analysis / renrendoc 均含 `Baxley`、`Madison`、`Mini Camp`、`Alice`；与音频指纹一致。
- **2026**：newdu / sjds / renrendoc 均含 picnic–Rose–Kevin、Swansea、Melbourne、Eureka；与音频指纹一致。newdu 文件名残留 `听力原文2025.06.11` 的 caveat **不推翻**正文与 2026 音频对齐这一实测。

## 仍不升级 teachable 的原因

1. 本次是锚点指纹，不是全卷逐字对齐 + 题号级 QC。  
2. 2022–24 仍缺仓内文字稿，无法做同标准核对。  
3. 第三方候选源（非 MoE 官方发行）身份层仍是 candidate。

## 复跑

```bash
python3 -m venv /tmp/gaozhong_asr_venv
/tmp/gaozhong_asr_venv/bin/pip install faster-whisper
# brew install ffmpeg   # if needed
/tmp/gaozhong_asr_venv/bin/python \
  scripts/tools/audit/listening_audio_transcript_fingerprint.py tiny.en
```
