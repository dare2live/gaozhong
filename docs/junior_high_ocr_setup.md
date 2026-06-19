# 初中子系统 OCR 工具链 + 交叉验证 (2026-06-17)

## 全局持久 OCR 环境 (跨项目复用)
PaddleOCR 官方项目 (https://github.com/PaddlePaddle/PaddleOCR) 装在**全局共享 venv**
(避 Homebrew Python PEP668 externally-managed + 不污染系统 python):
- venv: `~/.venvs/ocr` (paddlepaddle 3.3.1 + paddleocr 3.7.0 + pdfplumber)
- 全局入口 (PATH 含 ~/.local/bin): `ocr-python` → venv python; `paddleocr` → CLI。**其它项目直接 `ocr-python xxx.py` 即用**。
- 模型缓存: `~/.paddlex/official_models/` (PP-OCRv6, 全局共享, 首次自动下载)。
- 重建: `python3 -m venv ~/.venvs/ocr && ~/.venvs/ocr/bin/pip install paddlepaddle paddleocr pdfplumber`

## 沪教文本层 vs OCR 交叉验证结论 (§1.4)
脚本 `scripts/tools/junior/ocr_cross_validate.py` (在 venv 跑: `ocr-python scripts/tools/junior/ocr_cross_validate.py`)。
- **可读页**: 文本层结构化抽词 **171/171 = 100% 被 OCR 确证** → pdfplumber 文本层对沪教**可读页高可信**, 做主源。
- **CID 乱码页 (实证)**: 部分页 (如 7b p129) 释义是 **CID 字体码** `(cid:4078)` (InDesign 自定义编码, pdfplumber 解不开)
  → 文本层失败, **必须 OCR**。这是 agent 说"乱码"的真实部分 (但非全册, 只部分页)。
- **策略**: 文本层主抽(可读页) + **OCR 补 CID/伪影页**, 两源一致高置信入库。

## 沪教 6 册词表结构 (extract_hujiao_vocab.py)
- 都是 Module 制 (7-9 各 4 模块, 9b 3模块); 卷末 Appendices "Words and expressions" 词表。
- **9b = 29页累积总词表** (覆盖全初中七-九, 839词, 最完整 vocab 源)。
- per-grade 附录: 7a 159 / 8a 173 / 8b 155 / 9a 154 可读; **7b 偏低(43)=CID 乱码页**待 OCR 补。
- 跨源对账: 沪教907 ∩ 义务课标三级=638(70%) ∩ 高中cefr=814。

## 待精化 (Phase 2.5)
- OCR 融合: CID 页走 OCR 补全 (7b 等); 文本层+OCR 两源 reconcile。
- 9b 累积总表去重 + per-grade 归属 (用各卷附录定首引年级)。
- 落 junior 独立 DB (gaozhong_junior.duckdb, §6) + 独立 D0 门。
