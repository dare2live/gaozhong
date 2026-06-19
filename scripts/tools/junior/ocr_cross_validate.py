"""沪教 7a 词表附录: 文本层(pdfplumber) vs OCR(PaddleOCR) 交叉验证 (§1.4)."""
import re
import pdfplumber

PDF = "/Users/dp/Documents/M/gaozhong/data/junior_high/textbooks/hujiao/7a.pdf"
PAGES = range(123, 132)   # 附录 p124-132


def text_layer_words() -> set[str]:
    """第一源: 文本层抽词 (word /ipa/ pos. 释义)."""
    words = set()
    with pdfplumber.open(PDF) as pdf:
        for i in PAGES:
            t = (pdf.pages[i].extract_text() or "").replace("上海教育出版社", "")
            for m in re.finditer(r"([a-zA-Z][a-zA-Z\-' ]+?)\s*/[^/]+/\s*([a-z]+)\.", t):
                w = m.group(1).strip().lower()
                if 2 <= len(w) <= 25:
                    words.add(w.split()[-1] if " " in w else w)
    return words


def ocr_texts(img: str) -> list[str]:
    from paddleocr import PaddleOCR
    if not hasattr(ocr_texts, "_ocr"):
        ocr_texts._ocr = PaddleOCR(lang="en")
    o = ocr_texts._ocr
    try:
        res = o.predict(img)
        out = []
        for r in res:
            out.extend(r["rec_texts"] if isinstance(r, dict) else getattr(r, "rec_texts", []))
        return out
    except Exception:
        res = o.ocr(img)
        return [ln[1][0] for ln in res[0]] if res and res[0] else []


def ocr_words() -> set[str]:
    """第二源: OCR 图像抽英文 token."""
    words = set()
    for i in PAGES:
        for t in ocr_texts(f"/tmp/hujiao_ocr/p{i+1}.png"):
            for m in re.finditer(r"\b([a-zA-Z][a-zA-Z\-']{1,24})\b", t):
                words.add(m.group(1).lower())
    return words


tl, oc = text_layer_words(), ocr_words()
inter = tl & oc
print(f"文本层词: {len(tl)} | OCR词: {len(oc)} | 一致(交集): {len(inter)} ({len(inter)/max(1,len(tl)):.0%} of 文本层)")
print(f"仅文本层 (OCR漏/文本层噪声): {len(tl-oc)} 例 {sorted(tl-oc)[:15]}")
print(f"仅OCR (文本层丢字母/伪影): {len(oc-tl)} 例 {sorted(oc-tl)[:20]}")
# 定向: 文本层 'erman' 伪影 → OCR 应有 'german'
for art, fix in [("erman", "german"), ("hina", "china")]:
    print(f"  伪影核: '{art}'∈文本层={art in tl} → '{fix}'∈OCR={fix in oc} (OCR 修正确证)")
