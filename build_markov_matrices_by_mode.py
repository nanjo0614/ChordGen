#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_markov_matrices_by_mode.py   (2025-07-01 invalid-code filter)
------------------------------------------------------------------
* Quadrant×Mode の自己遷移除外 Markov 行列 (CSV)
* Quadrant×Mode の曲頭ヒスト first_chord_probs.json
"""

from __future__ import annotations
import argparse, json, logging, pickle
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, Tuple, List

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
log = logging.getLogger(__name__)

INVALID = {"None_None", None, ""}        # ← 追加

# ---------------------------------------------------------------------------
def extract_chords(events: List[dict]) -> List[str]:
    """Chord イベントの value を抽出（無効コードは除外）"""
    return [
        ev["value"] for ev in events
        if ev.get("name") == "Chord" and ev.get("value") not in INVALID
    ]

# ---------------------------------------------------------------------------
def build(input_dir: Path, out_dir: Path):
    counts: Dict[str, Dict[str, Counter[Tuple[str, str]]]] = \
        defaultdict(lambda: defaultdict(Counter))
    first : Dict[str, Dict[str, Counter[str]]] = \
        defaultdict(lambda: defaultdict(Counter))
    all_codes = set()

    for pkl in input_dir.glob("*.pkl"):
        try:
            _, events = pickle.load(pkl.open("rb"))
        except Exception as e:
            log.warning("%s: %s", pkl.name, e)
            continue

        quadrant = pkl.name.split("_")[0]           # 'Q1' 等
        mode     = "major" if any(ev.get("value", "").isupper()
                                  for ev in events if ev.get("name") == "Key") \
                     else "minor"

        chords = extract_chords(events)
        if len(chords) < 2:
            continue

        first[quadrant][mode][chords[0]] += 1
        all_codes.update(chords)

        for prev, nxt in zip(chords[:-1], chords[1:]):
            if prev != nxt:                         # ★自己遷移は除外
                counts[quadrant][mode][(prev, nxt)] += 1

    out_dir.mkdir(parents=True, exist_ok=True)
    codes_sorted = sorted(all_codes)

    for q, mode_dict in counts.items():
        for m, ctr in mode_dict.items():
            df = pd.DataFrame(0, index=codes_sorted, columns=codes_sorted, dtype=int)
            for (i, j), n in ctr.items():
                df.at[i, j] = n
            prob = df.div(df.sum(axis=1).replace(0, 1), axis=0)
            csv = out_dir / f"{q}_{m}.csv"
            prob.to_csv(csv, encoding="utf-8-sig")
            log.info("matrix saved: %s", csv.name)

    json_obj = {}
    for q, mode_dict in first.items():
        for m, ctr in mode_dict.items():
            tot = sum(ctr.values())
            json_obj[f"{q}_{m}"] = {c: v / tot for c, v in ctr.items()}
    (out_dir / "first_chord_probs.json").write_text(
        json.dumps(json_obj, ensure_ascii=False, indent=2), "utf-8")
    log.info("first_chord_probs.json saved.")

# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True)
    ap.add_argument("-o", "--output", required=True)
    a = ap.parse_args()
    build(Path(a.input).expanduser(), Path(a.output).expanduser())

if __name__ == "__main__":
    main()
