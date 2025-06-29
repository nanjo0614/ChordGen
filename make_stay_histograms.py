#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
make_stay_histograms.py  (fixed – 2025‑06‑28)
--------------------------------------------
EMOPIA+ の functional representation で保存された *lead_sheet/*.pkl を走査し、
『同じコードが何小節(bar)連続したか』を確率分布として JSON へ保存する。

修正点
~~~~~~
* 旧版では「コードが変わった瞬間」だけを列挙してしまい、滞在長=1 として
  カウントしていた。
* 本版では **Bar 境界を検出** し、「各小節の先頭で鳴っている(最初に現れた)
  コード」を 1 小節 1 つとして扱うことで正しいランレングスを取得する。
* 曲データが `Bar` イベントを持たない場合は 4 拍=1 小節とみなしてフォール
  バック処理を行う。

Usage::

    python make_stay_histograms.py --pkl-root "C:\ChordGen\EMOPIA+\functional\lead_sheet" --out "stay_histograms.json"
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator, List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1)  データ読み出し
# ---------------------------------------------------------------------------

def iter_lead_sheets(pkl_root: Path) -> Iterator[List[Dict[str, Any]]]:
    """再帰的に *.pkl を読み込み、events(list[dict]) を yield する"""
    for pkl_path in pkl_root.rglob("*.pkl"):
        try:
            with pkl_path.open("rb") as f:
                tup = pickle.load(f)
                if not (isinstance(tup, tuple) and len(tup) == 2):
                    raise ValueError("unexpected pickle format: expected 2‑tuple")
                events: List[Dict[str, Any]] = tup[1]
                yield events
        except Exception as e:
            logger.warning("%s: %s", pkl_path.name, e)

# ---------------------------------------------------------------------------
# 2)  1 小節 1 つのコードに変換
# ---------------------------------------------------------------------------

def extract_bar_chords(events: List[Dict[str, Any]]) -> List[str]:
    """各小節の『先頭で鳴っているコード』を列挙して返す。

    * Bar イベントがあれば厳密に区切る。
    * Bar が無い場合は Chord イベントを拍単位で数え、4 拍ごとに 1 小節とみなす。
    """
    bar_chords: List[str] = []

    # -------- A. Bar イベントが存在する場合 --------
    has_bar = any(ev.get("name") == "Bar" for ev in events)
    if has_bar:
        cur_chord: str | None = None
        for ev in events:
            if ev.get("name") == "Bar":
                if cur_chord not in (None, "None_None"):
                    bar_chords.append(cur_chord)
                cur_chord = None  # reset for next bar
            elif ev.get("name") == "Chord":
                # bar 内で最初に現れたコードを採用
                if cur_chord is None:
                    cur_chord = ev.get("value")
        # 末尾バッファを flush
        if cur_chord not in (None, "None_None"):
            bar_chords.append(cur_chord)
        return bar_chords

    # -------- B. Bar が無い場合: 4 拍単位で切る --------
    chords = [ev.get("value") for ev in events if ev.get("name") == "Chord"]
    if not chords:
        return []

    # 4 拍 = 1 小節 という前提でグループ化
    for i in range(0, len(chords), 4):
        grp = [c for c in chords[i : i + 4] if c not in (None, "None_None")]
        if grp:
            bar_chords.append(grp[0])  # bar 先頭のコードを採用
    return bar_chords

# ---------------------------------------------------------------------------
# 3)  滞在長ヒストグラムを構築して保存
# ---------------------------------------------------------------------------

def build_histograms(pkl_root: Path, out_json: Path) -> None:
    """全ファイルを処理し {chord: {run_len: prob}} を JSON で保存"""

    # hist[chord][run_len] = count
    hist: Dict[str, Counter[int]] = defaultdict(Counter)

    file_cnt = 0
    for events in iter_lead_sheets(pkl_root):
        bar_chords = extract_bar_chords(events)
        if not bar_chords:
            continue

        file_cnt += 1
        prev = bar_chords[0]
        run_len = 1
        for ch in bar_chords[1:]:
            if ch == prev:
                run_len += 1
            else:
                hist[prev][run_len] += 1
                prev, run_len = ch, 1
        # flush last run
        hist[prev][run_len] += 1

    if file_cnt == 0:
        logger.error("No valid pkl files found under %s", pkl_root)
        return

    # --- 正規化して dict[int->float] へ変換 --------------------
    result: Dict[str, Dict[int, float]] = {}
    for chord, counter in hist.items():
        total = sum(counter.values())
        result[chord] = {
            run_len: cnt / total for run_len, cnt in sorted(counter.items())
        }

    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info("stay_histograms saved to: %s", out_json)

# ---------------------------------------------------------------------------
# 4)  CLI
# ---------------------------------------------------------------------------

def parse_args():
    ap = argparse.ArgumentParser(
        description="Create stay‑length histograms (bar level) from EMOPIA+ lead_sheet pickles",
    )
    ap.add_argument("--pkl-root", required=True, help="Path to lead_sheet *.pkl directory")
    ap.add_argument("--out", default="stay_histograms.json", help="Output JSON filename")
    return ap.parse_args()


def main():
    args = parse_args()
    pkl_root = Path(args.pkl_root).expanduser()
    out_json = Path(args.out)

    if not pkl_root.exists():
        raise SystemExit(f"[Error] directory not found: {pkl_root}")

    build_histograms(pkl_root, out_json)


if __name__ == "__main__":
    main()
