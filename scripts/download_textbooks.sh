#!/usr/bin/env bash
# Download Liaoning/Shenyang relevant high school English textbooks from
# TapXWorld/ChinaTextbook (commit at master, snapshot 2025-10-18).
#
# Strategy:
#   - GitHub raw.githubusercontent.com supports files up to ~100MB.
#   - Files split as .pdf.1 .pdf.2 in 北师大版 are concatenated post-download.
#   - All 8 publisher variants are downloaded so we can compare; Shenyang's main
#     in-use version is 外研版(2019). 人教版 is the most common nationwide.
#
# Run from project root:  bash scripts/download_textbooks.sh

set -euo pipefail

REPO_BASE="https://raw.githubusercontent.com/TapXWorld/ChinaTextbook/master/%E9%AB%98%E4%B8%AD/%E8%8B%B1%E8%AF%AD"
DEST_BASE="data/textbooks"

# 仅辽宁省 14 地市在用的 2 个版本 (用户 2026-05-23 反馈):
#   - 外研版: 沈阳/大连/鞍山/抚顺/本溪/丹东/营口/阜新/辽阳/盘锦 (10 市)
#   - 人教版: 锦州/铁岭/朝阳/葫芦岛 (4 市)
# 其它 6 版本 (北师大/译林/沪教/沪外教/冀教/重庆大学) 已从 VERSIONS 去掉.
# version_dir_raw : version_dir_local
VERSIONS=(
  "%E4%BA%BA%E6%95%99%E7%89%88-%E4%BA%BA%E6%B0%91%E6%95%99%E8%82%B2%E5%87%BA%E7%89%88%E7%A4%BE|renjiao"
  "%E5%A4%96%E7%A0%94%E7%A4%BE%E7%89%88-%E5%A4%96%E8%AF%AD%E6%95%99%E5%AD%A6%E4%B8%8E%E7%A0%94%E7%A9%B6%E5%87%BA%E7%89%88%E7%A4%BE|waiyan"
)

# Book name (URL-encoded) : local file name
BOOKS=(
  "%E6%99%AE%E9%80%9A%E9%AB%98%E4%B8%AD%E6%95%99%E7%A7%91%E4%B9%A6%C2%B7%E8%8B%B1%E8%AF%AD%E5%BF%85%E4%BF%AE%20%E7%AC%AC%E4%B8%80%E5%86%8C.pdf|bixiu_1.pdf"
  "%E6%99%AE%E9%80%9A%E9%AB%98%E4%B8%AD%E6%95%99%E7%A7%91%E4%B9%A6%C2%B7%E8%8B%B1%E8%AF%AD%E5%BF%85%E4%BF%AE%20%E7%AC%AC%E4%BA%8C%E5%86%8C.pdf|bixiu_2.pdf"
  "%E6%99%AE%E9%80%9A%E9%AB%98%E4%B8%AD%E6%95%99%E7%A7%91%E4%B9%A6%C2%B7%E8%8B%B1%E8%AF%AD%E5%BF%85%E4%BF%AE%20%E7%AC%AC%E4%B8%89%E5%86%8C.pdf|bixiu_3.pdf"
  "%E6%99%AE%E9%80%9A%E9%AB%98%E4%B8%AD%E6%95%99%E7%A7%91%E4%B9%A6%C2%B7%E8%8B%B1%E8%AF%AD%E9%80%89%E6%8B%A9%E6%80%A7%E5%BF%85%E4%BF%AE%20%E7%AC%AC%E4%B8%80%E5%86%8C.pdf|xuanze_1.pdf"
  "%E6%99%AE%E9%80%9A%E9%AB%98%E4%B8%AD%E6%95%99%E7%A7%91%E4%B9%A6%C2%B7%E8%8B%B1%E8%AF%AD%E9%80%89%E6%8B%A9%E6%80%A7%E5%BF%85%E4%BF%AE%20%E7%AC%AC%E4%BA%8C%E5%86%8C.pdf|xuanze_2.pdf"
  "%E6%99%AE%E9%80%9A%E9%AB%98%E4%B8%AD%E6%95%99%E7%A7%91%E4%B9%A6%C2%B7%E8%8B%B1%E8%AF%AD%E9%80%89%E6%8B%A9%E6%80%A7%E5%BF%85%E4%BF%AE%20%E7%AC%AC%E4%B8%89%E5%86%8C.pdf|xuanze_3.pdf"
  "%E6%99%AE%E9%80%9A%E9%AB%98%E4%B8%AD%E6%95%99%E7%A7%91%E4%B9%A6%C2%B7%E8%8B%B1%E8%AF%AD%E9%80%89%E6%8B%A9%E6%80%A7%E5%BF%85%E4%BF%AE%20%E7%AC%AC%E5%9B%9B%E5%86%8C.pdf|xuanze_4.pdf"
)

fetch_one() {
  local url="$1"
  local out="$2"
  if [[ -s "$out" ]]; then
    echo "  skip (exists): $(basename "$out")"
    return 0
  fi
  echo "  GET  $(basename "$out")"
  # Try single file first; if 404, try split parts
  if curl -fsSL --retry 2 -o "$out.tmp" "$url"; then
    mv "$out.tmp" "$out"
  else
    rm -f "$out.tmp"
    # Try split form: .pdf.1 .pdf.2
    local p1="$out.tmp1" p2="$out.tmp2"
    if curl -fsSL --retry 2 -o "$p1" "${url}.1" && \
       curl -fsSL --retry 2 -o "$p2" "${url}.2"; then
      cat "$p1" "$p2" > "$out"
      rm -f "$p1" "$p2"
      echo "    merged 2 parts -> $(basename "$out")"
    else
      rm -f "$p1" "$p2"
      echo "    MISSING (single & split both 404)"
      return 1
    fi
  fi
}

for entry in "${VERSIONS[@]}"; do
  ver_url="${entry%%|*}"
  ver_local="${entry##*|}"
  out_dir="$DEST_BASE/$ver_local"
  mkdir -p "$out_dir"
  echo "==> $ver_local"
  for b in "${BOOKS[@]}"; do
    book_url="${b%%|*}"
    book_local="${b##*|}"
    url="$REPO_BASE/$ver_url/$book_url"
    out="$out_dir/$book_local"
    fetch_one "$url" "$out" || true
  done
done

echo
echo "=== Summary ==="
find "$DEST_BASE" -name "*.pdf" -type f | sort | while read -r f; do
  size=$(stat -f %z "$f" 2>/dev/null || stat -c %s "$f")
  printf "  %10d  %s\n" "$size" "$f"
done
