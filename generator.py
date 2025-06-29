#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generator.py  改造版
--------------
感情象限(Q1–Q4)だけを指定すると
  ├ その象限に対応する major / minor 行列を確率で選択
  ├ stay_histograms.json で「同じコードが何小節続くか」を実データからサンプリング
  ├ 温度付きマルコフ遷移でコード進行を生成
  └ voicings.py の get_voicing() でボイシング → MIDI 書き出し

使い方例:
    python generator.py --quadrant Q1 --bars 16 --max-stay 4 \
                        --temperature 0.7 --seed 42
"""

from __future__ import annotations
import argparse, random, sys, json
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import mido                      # pip install mido python-rtmidi
from mido import bpm2tempo, Message, MidiFile, MidiTrack

from voicings import get_voicing  # 動的ボイシング


# ----------------------------------------------------------------------
# 1. パラメータ
# ----------------------------------------------------------------------
MATRIX_DIR   = Path("markov_matrices_mode")
STAY_JSON    = Path("stay_histograms.json")   # ← make_stay_histograms.py で生成
PPQ          = 480
TEMPO_BPM    = 120

# ----------------------------------------------------------------------
# 2. 滞在長ヒストグラムの読込み
# ----------------------------------------------------------------------
if STAY_JSON.exists():
    STAY_HIST: Dict[str, Dict[str, float]] = json.loads(STAY_JSON.read_text("utf8"))
else:
    STAY_HIST = {}
    print("[Warn] stay_histograms.json が見つかりません。滞在長=1固定で進行を生成します。")


def sample_stay(chord: str, max_stay: int) -> int:
    """
    chord に対して滞在長をサンプリング。ヒストグラムがなければ 1。
    """
    table = STAY_HIST.get(chord)
    if not table:
        return 1

    lengths = np.fromiter(table.keys(), dtype=int)
    probs   = np.fromiter(table.values(), dtype=float)
    # numpy でサンプリング
    stay = int(np.random.choice(lengths, p=probs))
    return max(1, min(stay, max_stay))


# ----------------------------------------------------------------------
# 3. 行列読み込み & モード選択
# ----------------------------------------------------------------------
def load_transition_matrix(quadrant: str, mode: str) -> pd.DataFrame:
    csv_path = MATRIX_DIR / f"{quadrant}_{mode}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Transition CSV not found: {csv_path}")
    return pd.read_csv(csv_path, index_col=0)


def choose_mode_probabilistically(quadrant: str) -> str:
    major_df = load_transition_matrix(quadrant, "major")
    minor_df = load_transition_matrix(quadrant, "minor")

    major_w = major_df.values.sum()
    minor_w = minor_df.values.sum()
    total    = major_w + minor_w

    if total == 0:
        return "major"

    mode = random.choices(["major", "minor"],
                          weights=[major_w, minor_w], k=1)[0]
    print(f"[Info] {quadrant}: 選択されたモード = {mode}")
    return mode


# ----------------------------------------------------------------------
# 4. コード進行生成
# ----------------------------------------------------------------------
def _apply_temperature(probs: np.ndarray, temperature: float) -> np.ndarray:
    """
    temperature <1 でシャープ、>1 でフラット
    """
    if temperature <= 0:
        raise ValueError("temperature must be positive")

    # 0 しか無い場合はそのまま返す
    if probs.sum() == 0:
        return probs

    # Boltzmann スケーリング
    scaled = probs ** (1.0 / temperature)
    return scaled / scaled.sum()


def generate_progression(
    matrix: pd.DataFrame,
    bars: int,
    max_stay: int = 4,
    temperature: float = 1.0,
) -> list[str]:
    """
    滞在長ヒストグラム & 温度付き遷移で生成
    """
    # 開始コードを総遷移数で重み付け
    start_weights = matrix.sum(axis=1).values
    if start_weights.sum() == 0:
        cur = random.choice(matrix.index.tolist())
    else:
        cur = random.choices(matrix.index, weights=start_weights, k=1)[0]

    prog: list[str] = []
    while len(prog) < bars:
        # ---- 1) 滞在長決定 ----
        stay = sample_stay(cur, max_stay=max_stay)
        stay = min(stay, bars - len(prog))     # 残り越えない
        prog.extend([cur] * stay)

        if len(prog) >= bars:
            break

        # ---- 2) 次コード抽選 ----
        probs = matrix.loc[cur].to_numpy(dtype=float)
        probs = _apply_temperature(probs, temperature)

        if probs.sum() == 0 or np.allclose(probs, 0):
            next_c = random.choice(matrix.columns)
        else:
            next_c = np.random.choice(matrix.columns, p=probs)
        cur = next_c

    return prog[:bars]


# ----------------------------------------------------------------------
# 5. MIDI 生成
# ----------------------------------------------------------------------
def chords_to_midi(
    chord_seq: list[str],
    out_path: Path,
    tempo_bpm: int = TEMPO_BPM,
    ppq: int = PPQ,
    velocity: int = 80,
):
    mid   = MidiFile(ticks_per_beat=ppq)
    track = MidiTrack(); mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=bpm2tempo(tempo_bpm)))

    bar_ticks = ppq * 4   # 4/4

    for chord in chord_seq:
        notes = get_voicing(chord)
        # note_on
        for n in notes:
            track.append(Message("note_on", note=n, velocity=velocity, time=0))
        # note_off
        track.append(Message("note_off", note=notes[0], velocity=0, time=bar_ticks))
        for n in notes[1:]:
            track.append(Message("note_off", note=n, velocity=0, time=0))

    mid.save(out_path)
    print(f"[Info] MIDI saved to: {out_path.resolve()}")


# ----------------------------------------------------------------------
# 6. メイン
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quadrant", required=True, choices=["Q1","Q2","Q3","Q4"],
                    help="感情象限 Q1〜Q4")
    ap.add_argument("--bars", type=int, default=16, help="生成小節数")
    ap.add_argument("--max-stay", type=int, default=4,
                    help="同一コード連続の 最大小節 (安全装置)")
    ap.add_argument("--temperature", type=float, default=1.0,
                    help="遷移確率の温度 (<1 で自己遷移抑制)")
    ap.add_argument("--seed", type=int, default=None, help="乱数シード")
    ap.add_argument("--midi", default="out.mid", help="出力 MIDI ファイル名")
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    mode   = choose_mode_probabilistically(args.quadrant)
    matrix = load_transition_matrix(args.quadrant, mode)

    prog = generate_progression(matrix,
                                bars=args.bars,
                                max_stay=args.max_stay,
                                temperature=args.temperature)

    print("Generated progression:")
    print(" | ".join(prog))

    chords_to_midi(prog, Path(args.midi))


if __name__ == "__main__":
    main()
