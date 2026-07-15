#!/usr/bin/env python3
"""Fingerprint-check listening candidate MP3s against stored transcripts via ASR.

Uses distinctive spoken anchors (proper nouns / unique phrases), with fuzzy
ASR variants. Promotion to data/audio / years_with_audio is a separate step
(see scripts.tools.map.promote_listening_audio).

Requires: ffmpeg; faster-whisper (e.g. /tmp/gaozhong_asr_venv).
Usage:
  python listening_audio_transcript_fingerprint.py [tiny.en|base.en]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUDIO = ROOT / "data/external/exam_sources/listening_candidates"
TX = ROOT / "data/external/exam_sources/listening_transcripts"
OUT = ROOT / "data/structured/exam_point/listening_audio_transcript_fingerprint.json"


def cut_wav(src: Path, start_s: float, dur_s: float, dst: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start_s:.3f}",
            "-t",
            f"{dur_s:.3f}",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(dst),
        ],
        check=True,
        capture_output=True,
    )


def asr_text(model, wav: Path) -> str:
    segments, _ = model.transcribe(
        str(wav), language="en", beam_size=1, vad_filter=True
    )
    return " ".join(seg.text.strip() for seg in segments).strip()


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def any_alt(asr: str, alts: list[str]) -> bool:
    n = norm(asr)
    return any(norm(a) in n for a in alts)


CHECKS = [
    {
        "year": 2021,
        "audio": "2021_xgkii_listening_133ku_candidate.mp3",
        "transcript": "2021_xgki_ii_cpsenglish_transcript.md",
        "windows": [
            {
                "id": "text1_2_opening",
                "start": 90,
                "dur": 90,
                # tiny ASR often hears Mallorca as "my York"
                "groups": {
                    "spanish": ["Spanish"],
                    "lab_report": ["lab report"],
                    "davidson": ["Davidson"],
                    "mallorca_or_visit": [
                        "Mallorca",
                        "Majorca",
                        "my York",
                        "best friend worked",
                    ],
                },
                "require_any_of": [
                    ["spanish", "lab_report", "davidson"],
                    ["mallorca_or_visit", "spanish"],
                ],
            },
        ],
    },
    {
        "year": 2022,
        "audio": "2022_xgki_ii_kekenet_short_dialog.mp3",
        "transcript": "2022_xgki_ii_cpsenglish_transcript.md",
        "windows": [
            {
                "id": "short_text1_5",
                "audio": "2022_xgki_ii_kekenet_short_dialog.mp3",
                "start": 0,
                "dur": 140,
                "groups": {
                    "parking": ["parking space", "off-street"],
                    "judy": ["Judy", "flight"],
                    "laura": ["Laura", "thank-you", "thank you"],
                },
                "require_any_of": [["parking", "judy"], ["parking", "laura"]],
            },
            {
                "id": "long_tracy_woods",
                "audio": "2022_xgki_ii_kekenet_long_3.mp3",
                "start": 0,
                "dur": 150,
                "groups": {
                    "tracy": ["Tracy Woods", "Tracy"],
                    "dogs": ["dogs", "special education"],
                },
                "require_any_of": [["tracy", "dogs"]],
            },
            {
                "id": "mono_emma_wilson",
                "audio": "2022_xgki_ii_kekenet_monologue.mp3",
                "start": 0,
                "dur": 120,
                "groups": {
                    "emma": ["Emma Wilson", "Emma"],
                    "ubc": ["UBC", "British Columbia", "Vancouver"],
                },
                "require_any_of": [["emma", "ubc"]],
            },
        ],
    },
    {
        "year": 2023,
        "audio": "2023_xgki_ii_kekenet_short_dialog.mp3",
        "transcript": "2023_xgki_ii_listening_transcript.md",
        "windows": [
            {
                "id": "short_camping_bill",
                "audio": "2023_xgki_ii_kekenet_short_dialog.mp3",
                "start": 0,
                "dur": 105,
                "groups": {
                    "camping": ["camping", "cinema", "weatherman"],
                    "convenience": ["convenience store"],
                    "bill": ["ten dollars", "waiter"],
                },
                "require_any_of": [
                    ["camping", "convenience"],
                    ["camping", "bill"],
                ],
            },
            {
                "id": "long_yard_sale",
                "audio": "2023_xgki_ii_kekenet_long_3.mp3",
                "start": 0,
                "dur": 120,
                "groups": {
                    "clara": ["Clara"],
                    "ashley": ["Ashley", "Los Angeles"],
                    "yard": ["yard sale"],
                },
                "require_any_of": [["clara", "ashley"], ["yard", "ashley"]],
            },
            {
                "id": "mono_idler",
                "audio": "2023_xgki_ii_kekenet_monologue.mp3",
                "start": 0,
                "dur": 90,
                "groups": {
                    "idler": ["Idler", "idler"],
                    "hodgkinson": ["Hodgkinson", "Tom"],
                },
                "require_any_of": [["idler"], ["idler", "hodgkinson"]],
            },
        ],
    },
    {
        "year": 2024,
        "audio": "2024_xgkii_kekenet_short_dialog.mp3",
        "transcript": "2024_xgkii_netease_transcript.md",
        "windows": [
            {
                "id": "short_talent_smiths",
                "audio": "2024_xgkii_kekenet_short_dialog.mp3",
                "start": 0,
                "dur": 85,
                "groups": {
                    "talent": ["talent show"],
                    "smiths": ["Smiths"],
                    "denver": ["Denver"],
                },
                "require_any_of": [["talent", "smiths"], ["talent", "denver"]],
            },
            {
                "id": "long_browns_grill",
                "audio": "2024_xgkii_kekenet_long_2.mp3",
                "start": 0,
                "dur": 90,
                "groups": {
                    "grill": ["Brown's Grill", "Browns Grill", "Brown"],
                    "anderson": ["Anderson"],
                },
                "require_any_of": [["grill", "anderson"]],
            },
            {
                "id": "mono_rochester",
                "audio": "2024_xgkii_kekenet_monologue.mp3",
                "start": 0,
                "dur": 90,
                "groups": {
                    "rochester": ["Rochester"],
                    "leadership": ["leadership"],
                },
                "require_any_of": [["rochester", "leadership"]],
            },
        ],
    },
    {
        "year": 2025,
        "audio": "2025_xgkii_listening_newdu_candidate.mp3",
        "transcript": "2025_xgkii_newdu_listening_stem.txt",
        "windows": [
            {
                "id": "text1_baxley_route",
                "start": 40,
                "dur": 80,
                "groups": {
                    "bus_query": [
                        "Is this bus going",
                        "bus going to",
                        "Fast Leech",
                        "Baxley",
                    ],
                    "yellow_taxi": ["yellow taxi"],
                    "bus_number_four": [
                        "bus number four",
                        "Bus No.4",
                        "bus no 4",
                        "number four",
                    ],
                },
                "require_any_of": [
                    ["yellow_taxi", "bus_number_four"],
                    ["bus_query", "yellow_taxi"],
                ],
            },
            {
                "id": "text10_creative_camp",
                "start": 900,
                "dur": 120,
                "groups": {
                    "creative_day": ["Creative Day", "creative day school"],
                    "mini_camp": ["Mini Camp", "Many Can", "mini can"],
                    "ages_5_12": ["ages 5 through 12", "ages five through twelve"],
                },
                "require_any_of": [
                    ["creative_day", "mini_camp"],
                    ["creative_day", "ages_5_12"],
                ],
            },
        ],
    },
    {
        "year": 2026,
        "audio": "2026_national_ii_listening_newdu_candidate.mp3",
        "transcript": "2026_national_ii_sjds_transcript.md",
        "windows": [
            {
                "id": "text1_picnic_rose",
                "start": 206,
                "dur": 40,
                "groups": {
                    "picnic": ["picnic"],
                    "rose": ["Rose"],
                    "kevin": ["Kevin"],
                },
                "require_any_of": [["picnic", "rose"], ["picnic", "kevin"]],
            },
            {
                "id": "text6_swansea",
                "start": 486,
                "dur": 50,
                "groups": {
                    "swansea": ["Swansea", "Swan Sea", "Swanse"],
                    "june_22": ["June 22", "June 22nd"],
                },
                "require_any_of": [["swansea"], ["swansea", "june_22"]],
            },
            {
                "id": "text10_melbourne",
                "start": 1050,
                "dur": 60,
                "groups": {
                    "melbourne": ["Melbourne"],
                    "eureka": ["Eureka", "Rika Tower"],
                    "book_thief": ["Book Thief", "book Thief"],
                },
                "require_any_of": [
                    ["melbourne", "eureka"],
                    ["melbourne", "book_thief"],
                ],
            },
        ],
    },
]


def window_pass(asr: str, win: dict) -> tuple[bool, dict[str, bool]]:
    hits = {k: any_alt(asr, alts) for k, alts in win["groups"].items()}
    ok = any(all(hits[n] for n in combo) for combo in win["require_any_of"])
    return ok, hits


def main() -> int:
    from faster_whisper import WhisperModel

    model_size = sys.argv[1] if len(sys.argv) > 1 else "tiny.en"
    print(f"loading WhisperModel({model_size!r})...", flush=True)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    results = []
    with tempfile.TemporaryDirectory(prefix="listening_fp_") as tmp:
        tmpdir = Path(tmp)
        for check in CHECKS:
            audio = AUDIO / check["audio"]
            tx = TX / check["transcript"]
            year_row: dict = {
                "year": check["year"],
                "audio": check["audio"],
                "transcript": check["transcript"],
                "audio_exists": audio.is_file(),
                "transcript_exists": tx.is_file(),
                "windows": [],
            }
            if not audio.is_file() or not tx.is_file():
                year_row["verdict"] = "SKIP_MISSING"
                results.append(year_row)
                continue

            all_ok = True
            for win in check["windows"]:
                src = AUDIO / win["audio"] if win.get("audio") else audio
                if not src.is_file():
                    year_row["windows"].append(
                        {
                            "id": win["id"],
                            "pass": False,
                            "error": f"missing audio {src.name}",
                        }
                    )
                    all_ok = False
                    continue
                wav = tmpdir / f"{check['year']}_{win['id']}.wav"
                cut_wav(src, win["start"], win["dur"], wav)
                text = asr_text(model, wav)
                ok, hits = window_pass(text, win)
                year_row["windows"].append(
                    {
                        "id": win["id"],
                        "audio": src.name,
                        "start_s": win["start"],
                        "dur_s": win["dur"],
                        "hits": hits,
                        "pass": ok,
                        "asr": text,
                    }
                )
                if not ok:
                    all_ok = False
            year_row["verdict"] = "PASS" if all_ok else "FAIL"
            results.append(year_row)

    out = {
        "method": "faster-whisper fingerprint anchors vs local transcripts",
        "model": model_size,
        "note": (
            "Fingerprint only (distinctive spoken anchors + fuzzy ASR variants); "
            "not full verbatim force-alignment. Teachable gate / years_with_audio "
            "stays closed until explicit product decision."
        ),
        "asr_full_segment_dump": "data/structured/exam_point/listening_2022_2024_asr_dump.json",
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\nwrote {OUT}", flush=True)
    fails = [r for r in results if r.get("verdict") == "FAIL"]
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
