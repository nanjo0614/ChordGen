#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
make_stay_histograms.py  (2025-07-01 invalid-code filter)
--------------------------------------------------------
同一コードが何小節続くかのヒストを JSON 化。無効コードは除外。
"""

from __future__ import annotations
import argparse, json, logging, pickle
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
log = logging.getLogger(__name__)

INVALID = {"None_None", None, ""}        # ← 追加

# ---------------------------------------------------------------------------
def iter_lead_sheets(root: Path):
    for p in root.rglob("*.pkl"):
        try:
            with p.open("rb") as f:
                _, events = pickle.load(f)
                yield events
        except Exception as e:
            log.warning("%s: %s", p.name, e)

# ---------------------------------------------------------------------------
def extract_bar_chords(events: List[Dict[str, Any]]) -> List[str]:
    bar_chords: List[str] = []
    has_bar = any(ev.get("name") == "Bar" for ev in events)

    if has_bar:  # Bar 境界がある場合
        cur = None
        for ev in events:
            if ev.get("name") == "Bar":
                if cur:
                    bar_chords.append(cur)
                cur = None
            elif ev.get("name") == "Chord" and ev.get("value") not in INVALID:
                if cur is None:
                    cur = ev["value"]
        if cur:
            bar_chords.append(cur)
        return bar_chords

    # Bar が無い場合（拍ベース → 4 拍 = 1 小節）
    chords = [ev["value"] for ev in events
              if ev.get("name") == "Chord" and ev.get("value") not in INVALID]
    for i in range(0, len(chords), 4):
        grp = chords[i:i + 4]
        if grp:
            bar_chords.append(grp[0])
    return bar_chords

# ---------------------------------------------------------------------------
def build(root: Path, out_json: Path):
    hist = defaultdict(Counter)

    for evs in iter_lead_sheets(root):
        bars = extract_bar_chords(evs)
        if not bars:
            continue
        prev, run = bars[0], 1
        for ch in bars[1:]:
            if ch == prev:
                run += 1
            else:
                hist[prev][run] += 1
                prev, run = ch, 1
        hist[prev][run] += 1

    result = {
        ch: {k: v / sum(cnt.values()) for k, v in cnt.items()}
        for ch, cnt in hist.items()
    }
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    log.info("saved → %s", out_json)

# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkl-root", required=True)
    ap.add_argument("--out", default="stay_histograms.json")
    a = ap.parse_args()
    build(Path(a.pkl_root).expanduser(), Path(a.out))

if __name__ == "__main__":
    main()
