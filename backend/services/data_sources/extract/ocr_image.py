"""低清图 OCR×视觉交叉验证裁决 — 可复用图像预处理 (extract 层).

由来 (2026-06-19 中考2024答案图复核实证 = 坑23): 低清答案图 11.png(637x673) **直接视觉扫读会错**
(把 Q9/Q12/Q19/Q20 等读错), PaddleOCR 反而对; 唯一可靠裁决 = **裁分区 + 放大4x + 逐块精读 + 与 OCR 交叉**。
本模块固化机械可复用部分(裁剪/放大/OCR 调用 + 两源 reconcile); **视觉精读由调用方做**(vision model Read
放大后的 crop, 或人), 不在代码里 — 视觉是第二独立源, 不能用同一 OCR 自证 (坑16)。

单一计算点 (Rule1): 凡"低清图→可读区域→双源比对"都走这里, 调用方不各自 crop/调 OCR。
lazy import PIL/paddleocr; 不可用则降级(返回原图路径/空 list, 不抛, 见 acquire/web.py 模式)。

CLI: python3 -m backend.services.data_sources.extract.ocr_image <图> [--bands N] [--factor F] [--ocr]
     裁 N 横块放大 F 倍存 /tmp, (可选)对每块跑 PaddleOCR; 给调用方(含 LLM agent)做视觉精读。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


def is_available() -> bool:
    """PIL 是否可用 (裁剪/放大依赖)."""
    return importlib.util.find_spec("PIL") is not None


def _bands(n: int) -> list[tuple[float, float]]:
    """把 [0,1] 纵向均分 n 块, 每块上下各留 10% 重叠 (防边界字被切半)."""
    out = []
    for i in range(n):
        top = max(0.0, i / n - 0.03)
        bot = min(1.0, (i + 1) / n + 0.03)
        out.append((top, bot))
    return out


def crop_and_upscale(image_path: str | Path, *, bands: int = 3,
                     regions: list[tuple[float, float]] | None = None,
                     factor: int = 4, out_dir: str | Path = "/tmp/ocr_adjudicate") -> list[Path]:
    """裁纵向分区 + LANCZOS 放大 factor 倍 → 存盘, 返回 crop 路径 (供视觉精读/OCR).

    regions=[(top_frac,bot_frac),...] 显式分区; 否则按 bands 均分。低清图放大后小字可读。
    PIL 不可用 → 返回 [原图] (降级不崩)。"""
    if not is_available():
        return [Path(image_path)]
    from PIL import Image
    im = Image.open(image_path).convert("RGB")
    w, h = im.size
    regs = regions if regions else _bands(bands)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(image_path).stem
    paths: list[Path] = []
    for idx, (top, bot) in enumerate(regs):
        crop = im.crop((0, int(h * top), w, int(h * bot)))
        cw, ch = crop.size
        crop = crop.resize((cw * factor, ch * factor), Image.LANCZOS)
        p = out / f"{stem}_r{idx}.png"
        crop.save(p)
        paths.append(p)
    return paths


def paddleocr_lines(image_path: str | Path, lang: str = "en") -> list[str]:
    """PaddleOCR 行文本 (第二独立源; 容版本差异 predict/ocr 两 API, 见 ocr_cross_validate)。
    paddleocr 不可用 → []。"""
    if importlib.util.find_spec("paddleocr") is None:
        return []
    from paddleocr import PaddleOCR
    if not hasattr(paddleocr_lines, "_cache"):
        paddleocr_lines._cache = {}
    ocr = paddleocr_lines._cache.setdefault(lang, PaddleOCR(lang=lang))
    try:
        res = ocr.predict(str(image_path))
        out: list[str] = []
        for r in res:
            out.extend(r["rec_texts"] if isinstance(r, dict) else getattr(r, "rec_texts", []))
        return out
    except Exception:
        res = ocr.ocr(str(image_path))
        return [ln[1][0] for ln in res[0]] if res and res[0] else []


def reconcile_readings(reading_a: list[str], reading_b: list[str]) -> dict:
    """两独立源(如 视觉读数 vs OCR读数) 裁决: 一致项可信; 分歧项需第三次精读 (坑16: 双源一致≠对,
    但**分歧**一定有一方错, 是必须复核的信号)。大小写/空白归一后比对。"""
    norm = lambda xs: {str(x).strip().lower() for x in xs if str(x).strip()}
    a, b = norm(reading_a), norm(reading_b)
    return {
        "agree": sorted(a & b),
        "only_a": sorted(a - b),
        "only_b": sorted(b - a),
        "agreement_rate": round(len(a & b) / max(1, len(a | b)), 3),
        "needs_review": sorted((a - b) | (b - a)),
    }


def _cli() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="低清图裁剪放大(+可选OCR) 供 OCR×视觉裁决")
    ap.add_argument("image")
    ap.add_argument("--bands", type=int, default=3)
    ap.add_argument("--factor", type=int, default=4)
    ap.add_argument("--ocr", action="store_true", help="对每块跑 PaddleOCR(第二源)")
    a = ap.parse_args()
    crops = crop_and_upscale(a.image, bands=a.bands, factor=a.factor)
    for p in crops:
        print(f"crop: {p}")
        if a.ocr:
            for line in paddleocr_lines(p):
                print(f"    ocr| {line}")
    print("→ 视觉精读: 用 Read 工具看每个 crop, 与 ocr 行交叉裁决 (分歧项必复核)")


if __name__ == "__main__":
    _cli()
