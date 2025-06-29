#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_markov_matrices_by_mode.py  (2025-06-30 semi-Markov ready)
---------------------------------------------------------------
EMOPIA+ functional/lead_sheet を走査して
  Quadrant(Q1–Q4) × Mode(major/minor)
の **自己遷移を除いた** 1 次 Markov 行列 (CSV) を出力する。

python build_markov_matrices_by_mode.py -i ./EMOPIA+/functional/lead_sheet -o markov_matrices_mode
"""

from __future__ import annotations
import argparse, logging, pickle
from collections import defaultdict, Counter
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

# --------------------------------------------------
# ユーティリティ
# --------------------------------------------------
def extract_chords(events):
    """Chord イベントの value を順番に取り出す"""
    return [ev["value"] for ev in events if ev.get("name") == "Chord"]

# --------------------------------------------------
def build_matrices(input_dir: Path, output_dir: Path):
    # {Q → {mode → Counter[(prev,next)]}}
    counts = defaultdict(lambda: defaultdict(Counter))
    all_codes = set()

    for pkl_path in input_dir.glob("*.pkl"):
        try:
            with open(pkl_path, "rb") as f:
                _, events = pickle.load(f)
        except Exception as e:
            logger.warning("%s: %s", pkl_path.name, e)
            continue

        key_token = next((ev["value"] for ev in events
                          if ev.get("name") == "Key"), "C")
        mode = "major" if key_token.isupper() else "minor"
        quadrant = pkl_path.name.split("_")[0]  # 'Q1' など

        chords = extract_chords(events)
        if len(chords) < 2:
            continue
        all_codes.update(chords)

        # -------- 自己遷移を無視してカウント ----------
        for prev, nxt in zip(chords[:-1], chords[1:]):
            if prev != nxt:
                counts[quadrant][mode][(prev, nxt)] += 1

    output_dir.mkdir(parents=True, exist_ok=True)
    codes_sorted = sorted(all_codes)

    for quadrant, mdict in counts.items():
        for mode, ctr in mdict.items():
            df = pd.DataFrame(
                0, index=codes_sorted, columns=codes_sorted, dtype=int
            )
            for (prev, nxt), c in ctr.items():
                df.at[prev, nxt] = c

            prob = df.div(df.sum(axis=1).replace(0, 1), axis=0)
            out = output_dir / f"{quadrant}_{mode}.csv"
            prob.to_csv(out, encoding="utf-8-sig")
            logger.info("saved %s", out.name)

# --------------------------------------------------
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True,
                    help="lead_sheet *.pkl フォルダ")
    ap.add_argument("-o", "--output", required=True,
                    help="CSV 出力フォルダ")
    return ap.parse_args()

def main():
    a = parse_args()
    build_matrices(Path(a.input), Path(a.output))

if __name__ == "__main__":
    main()
