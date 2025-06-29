#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generator.py  (first-chord + semi-Markov 2025-06-30)
---------------------------------------------------
Quadrant 指定 → 曲頭コードを専用分布で抽選 → セミマルコフ生成 → MIDI 保存
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import mido
from mido import MidiFile, MidiTrack, Message, bpm2tempo
from voicings import get_voicing

MATRIX_DIR  = Path("markov_matrices_mode")
STAY_JSON   = Path("stay_histograms.json")
FIRST_JSON  = MATRIX_DIR / "first_chord_probs.json"  # ←build スクリプトと同じ場所
PPQ         = 480
TEMPO_BPM   = 120

# ------------- サポート関数 ------------------------------------
def load_json(path: Path) -> dict:
    return json.loads(path.read_text("utf-8")) if path.exists() else {}

STAY_HIST  = load_json(STAY_JSON)
FIRST_PROB = load_json(FIRST_JSON)

def sample_stay(chord: str, rng: np.random.Generator, max_stay: int) -> int:
    tbl = STAY_HIST.get(chord)
    if not tbl:
        return 1
    k  = np.fromiter(tbl.keys(), dtype=int)
    p  = np.fromiter(tbl.values(), dtype=float)
    τ  = int(rng.choice(k, p=p))
    return max(1, min(τ, max_stay))

def load_matrix(q: str, mode: str) -> pd.DataFrame:
    f = MATRIX_DIR / f"{q}_{mode}.csv"
    if not f.exists():
        sys.exit(f"[Error] matrix not found: {f}")
    return pd.read_csv(f, index_col=0)

def choose_mode(q: str) -> str:
    # 曲数の多い方を選ぶ
    major_csv = MATRIX_DIR / f"{q}_major.csv"
    minor_csv = MATRIX_DIR / f"{q}_minor.csv"
    return "major" if major_csv.exists() else "minor"

# ---------------------------------------------------------------
def choose_first(
    codes: List[str],
    quadrant: str,
    mode: str,
    rng: np.random.Generator,
    forced: Optional[str] = None,
) -> str:
    if forced:
        return forced
    key = f"{quadrant}_{mode}"
    tbl = FIRST_PROB.get(key)
    if tbl:
        p = np.array([tbl.get(c, 0.0) for c in codes])
        if p.sum() > 0:
            p /= p.sum()
            return rng.choice(codes, p=p)
    # fallback: 行和重み
    p = np.ones(len(codes))
    p /= p.sum()
    return rng.choice(codes, p=p)

# ---------------------------------------------------------------
def _apply_temp(p: np.ndarray, T: float) -> np.ndarray:
    if p.sum() == 0:
        return p
    q = p ** (1.0 / T)
    return q / q.sum()

def generate(
    matrix: pd.DataFrame,
    bars: int,
    rng: np.random.Generator,
    start_code: str,
    max_stay: int,
    T: float,
) -> List[str]:
    codes = matrix.index.to_list()
    cur   = start_code
    remain = sample_stay(cur, rng, max_stay)
    prog: List[str] = []

    while len(prog) < bars:
        prog.append(cur)
        remain -= 1
        if len(prog) >= bars:
            break
        if remain == 0:
            row = matrix.loc[cur].to_numpy(float)
            idx = matrix.columns.get_loc(cur)
            row[idx] = 0.0                           # 自己遷移禁止
            row = _apply_temp(row, T)
            if row.sum() == 0:
                nxt = rng.choice(codes)
            else:
                row /= row.sum()
                nxt = rng.choice(codes, p=row)
            cur    = nxt
            remain = sample_stay(cur, rng, max_stay)
    return prog[:bars]

# ---------------------------------------------------------------
def chords_to_midi(seq: List[str], out_path: Path, velocity=80):
    midi = MidiFile(ticks_per_beat=PPQ)
    track = MidiTrack(); midi.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=bpm2tempo(TEMPO_BPM)))

    bar_ticks = PPQ * 4
    for ch in seq:
        notes = get_voicing(ch)
        for n in notes:
            track.append(Message("note_on", note=n, velocity=velocity, time=0))
        track.append(Message("note_off", note=notes[0], velocity=0, time=bar_ticks))
        for n in notes[1:]:
            track.append(Message("note_off", note=n, velocity=0, time=0))
    midi.save(out_path)
    print(f"[Info] MIDI saved → {out_path.resolve()}")

# ---------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quadrant", required=True, choices=["Q1", "Q2", "Q3", "Q4"])
    ap.add_argument("--bars", type=int, default=16)
    ap.add_argument("--max-stay", type=int, default=4)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--start-chord", help="固定で曲頭コードを指定")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--midi", default="out.mid")
    args = ap.parse_args()

    rng   = np.random.default_rng(args.seed)
    mode  = choose_mode(args.quadrant)
    mat   = load_matrix(args.quadrant, mode)

    start = choose_first(mat.index.to_list(),
                         args.quadrant, mode, rng,
                         forced=args.start_chord)
    prog = generate(mat, args.bars, rng, start,
                    max_stay=args.max_stay, T=args.temperature)

    print(" | ".join(prog))
    chords_to_midi(prog, Path(args.midi))

if __name__ == "__main__":
    main()
