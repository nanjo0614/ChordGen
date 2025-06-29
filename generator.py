#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generator.py  (semi-Markov版 2025-06-30)
--------------------------------------
 1) Quadrant を指定 → major/minor を確率選択
 2) 滞在長 τ ~ F_i(τ) を引き τ bars 出力
 3) 次状態 j を P(i→j) で抽選（自己遷移は強制 0）
 4) 2) へ戻る
"""

from __future__ import annotations
import argparse, json, random, sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import mido
from mido import MidiFile, MidiTrack, Message, bpm2tempo
from voicings import get_voicing

# --------------------------------------------------
# 定数
MATRIX_DIR = Path("markov_matrices_mode")
STAY_JSON  = Path("stay_histograms.json")
PPQ        = 480
TEMPO_BPM  = 120
# --------------------------------------------------
# 滞在長テーブル
if STAY_JSON.exists():
    STAY_HIST: Dict[str, Dict[str, float]] = json.loads(STAY_JSON.read_text("utf8"))
else:
    print("[Warn] stay_histograms.json not found → stay=1 固定")
    STAY_HIST = {}

def sample_stay(chord: str, rng: np.random.Generator, max_stay: int) -> int:
    tbl = STAY_HIST.get(chord)
    if not tbl:
        return 1
    lengths = np.fromiter(tbl.keys(), dtype=int)
    probs   = np.fromiter(tbl.values(), dtype=float)
    τ = int(rng.choice(lengths, p=probs))
    return max(1, min(τ, max_stay))

# --------------------------------------------------
def load_matrix(quadrant: str, mode: str) -> pd.DataFrame:
    f = MATRIX_DIR / f"{quadrant}_{mode}.csv"
    if not f.exists():
        raise FileNotFoundError(f"{f} not found")
    return pd.read_csv(f, index_col=0)

def choose_mode(quadrant: str) -> str:
    major = load_matrix(quadrant, "major").values.sum()
    minor = load_matrix(quadrant, "minor").values.sum()
    mode = "major" if major >= minor else "minor"
    print(f"[Info] {quadrant}: mode={mode}")
    return mode

# --------------------------------------------------
def _apply_temperature(p: np.ndarray, T: float) -> np.ndarray:
    if p.sum() == 0:
        return p
    q = p ** (1.0 / T)
    return q / q.sum()

def generate_progression(
    matrix: pd.DataFrame,
    bars: int,
    rng: np.random.Generator,
    max_stay: int = 4,
    temperature: float = 1.0,
) -> List[str]:
    codes = matrix.index.to_list()
    # 重み＝行合計で初期コードを抽選
    start_probs = matrix.sum(axis=1).to_numpy()
    start_probs = start_probs / start_probs.sum() if start_probs.sum() else None
    cur = rng.choice(codes, p=start_probs)
    remain = sample_stay(cur, rng, max_stay)

    prog: List[str] = []
    while len(prog) < bars:
        prog.append(cur)
        remain -= 1
        if len(prog) >= bars:
            break
        if remain == 0:
            # ---- 次コード抽選（自己遷移=0） ----
            row = matrix.loc[cur].to_numpy(dtype=float)
            idx = matrix.columns.get_loc(cur)
            row[idx] = 0.0                    # 自己遷移禁止
            row = _apply_temperature(row, temperature)
            if row.sum() == 0:
                nxt = rng.choice(codes)
            else:
                row /= row.sum()
                nxt = rng.choice(codes, p=row)
            cur = nxt
            remain = sample_stay(cur, rng, max_stay)
    return prog[:bars]

# --------------------------------------------------
def chords_to_midi(seq: List[str], out_path: Path, velocity=80):
    midi = MidiFile(ticks_per_beat=PPQ)
    tr = MidiTrack(); midi.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=bpm2tempo(TEMPO_BPM)))

    bar_ticks = PPQ * 4
    for ch in seq:
        notes = get_voicing(ch)
        for n in notes:
            tr.append(Message("note_on", note=n, velocity=velocity, time=0))
        tr.append(Message("note_off", note=notes[0], velocity=0, time=bar_ticks))
        for n in notes[1:]:
            tr.append(Message("note_off", note=n, velocity=0, time=0))
    midi.save(out_path)
    print(f"[Info] MIDI saved → {out_path.resolve()}")

# --------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quadrant", required=True, choices=["Q1", "Q2", "Q3", "Q4"])
    ap.add_argument("--bars", type=int, default=16)
    ap.add_argument("--max-stay", type=int, default=4)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--midi", default="out.mid")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    mode   = choose_mode(args.quadrant)
    matrix = load_matrix(args.quadrant, mode)

    prog = generate_progression(matrix, args.bars, rng,
                                max_stay=args.max_stay,
                                temperature=args.temperature)

    print(" | ".join(prog))
    chords_to_midi(prog, Path(args.midi))

if __name__ == "__main__":
    main()
