#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generator.py  (2025-07-02  thickened chords)
-------------------------------------------
* first-chord＋セミマルコフ生成
* --thicken / -t : 構成音すべてをオクターブ下にも重ねる
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import mido
from mido import MidiFile, MidiTrack, Message, bpm2tempo
from voicings import get_voicing, parse_symbol   # validation 用

MATRIX_DIR  = Path("markov_matrices_mode")
STAY_JSON   = Path("stay_histograms.json")
FIRST_JSON  = MATRIX_DIR / "first_chord_probs.json"
PPQ, TEMPO_BPM = 480, 135
INVALID = {"None_None", None, ""}

# ---------------------------------------------------------------------------
def load_json(p: Path) -> dict:
    return json.loads(p.read_text("utf-8")) if p.exists() else {}

STAY_HIST  = load_json(STAY_JSON)
FIRST_PROB = load_json(FIRST_JSON)

def is_valid(ch: str) -> bool:
    if ch in INVALID:
        return False
    try:
        parse_symbol(ch)
        return True
    except Exception:
        return False

def sample_stay(ch: str, rng: np.random.Generator, max_stay: int) -> int:
    tbl = STAY_HIST.get(ch)
    if not tbl:
        return 1
    k = np.fromiter(tbl.keys(), int)
    p = np.fromiter(tbl.values(), float)
    τ = int(rng.choice(k, p=p))
    return max(1, min(τ, max_stay))

def load_matrix(q: str, mode: str) -> pd.DataFrame:
    f = MATRIX_DIR / f"{q}_{mode}.csv"
    if not f.exists():
        sys.exit(f"[Error] matrix not found: {f}")
    return pd.read_csv(f, index_col=0)

def choose_first(codes: List[str], q: str, mode: str,
                 rng: np.random.Generator,
                 forced: Optional[str]) -> str:
    if forced and is_valid(forced):
        return forced
    tbl = FIRST_PROB.get(f"{q}_{mode}", {})
    p = np.array([tbl.get(c, 0.0) for c in codes])
    if p.sum() == 0:
        p = np.ones(len(codes))
    p /= p.sum()
    while True:
        ch = rng.choice(codes, p=p)
        if is_valid(ch):
            return ch

def apply_temp(v: np.ndarray, T: float):
    return (v ** (1 / T)) / v.sum() if v.sum() else v

# ---------------- core -----------------------------------------------------
def generate(mat: pd.DataFrame, bars: int, rng: np.random.Generator,
             start: str, max_stay: int, T: float) -> List[str]:
    codes = mat.index.to_list()
    cur   = start
    remain = sample_stay(cur, rng, max_stay)
    prog: List[str] = []

    while len(prog) < bars:
        prog.append(cur)
        remain -= 1
        if len(prog) >= bars:
            break
        if remain == 0:
            row = mat.loc[cur].to_numpy(float)
            idx = mat.columns.get_loc(cur)
            row[idx] = 0.0
            row = apply_temp(row, T)
            if row.sum() == 0:
                nxt = rng.choice([c for c in codes if is_valid(c)])
            else:
                row /= row.sum()
                nxt = rng.choice(codes, p=row)
                while not is_valid(nxt):
                    nxt = rng.choice(codes, p=row)
            cur, remain = nxt, sample_stay(nxt, rng, max_stay)
    return prog[:bars]

# ---------------- MIDI -----------------------------------------------------
def chords_to_midi(seq: List[str], out_path: Path,
                   add_lower: bool, velocity=80):
    midi = MidiFile(ticks_per_beat=PPQ)
    tr = MidiTrack(); midi.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=bpm2tempo(TEMPO_BPM)))
    bar_ticks = PPQ * 4

    for ch in seq:
        if not is_valid(ch):
            tr.append(Message("note_off", note=0, velocity=0, time=bar_ticks))
            continue
        notes = get_voicing(ch, add_lower_octave=add_lower)
        for n in notes:
            tr.append(Message("note_on", note=n, velocity=velocity, time=0))
        tr.append(Message("note_off", note=notes[0], velocity=0, time=bar_ticks))
        for n in notes[1:]:
            tr.append(Message("note_off", note=n, velocity=0, time=0))
    midi.save(out_path)
    print(f"[Info] MIDI saved → {out_path.resolve()}")

# ---------------- CLI ------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quadrant", required=True, choices=["Q1", "Q2", "Q3", "Q4"])
    ap.add_argument("--bars", type=int, default=16)
    ap.add_argument("--max-stay", type=int, default=4)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--start-chord")
    ap.add_argument("-t", "--thicken", action="store_true",
                    help="構成音すべてのオクターブ下を重ねる")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--midi", default="out.mid")
    a = ap.parse_args()

    rng  = np.random.default_rng(a.seed)
    mode = "major" if (MATRIX_DIR / f"{a.quadrant}_major.csv").exists() else "minor"
    mat  = load_matrix(a.quadrant, mode)

    start = choose_first(mat.index.to_list(), a.quadrant, mode, rng, a.start_chord)
    prog  = generate(mat, a.bars, rng, start, a.max_stay, a.temperature)

    print(" | ".join(prog))
    chords_to_midi(prog, Path(a.midi), add_lower=a.thicken)

if __name__ == "__main__":
    main()
