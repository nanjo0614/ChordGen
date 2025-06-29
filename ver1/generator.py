#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generator.py
------------
・感情象限(Q1–Q4)だけを指定すると  
  ├ その象限に対応する major / minor 行列を確率で選択  
  ├ マルコフ遷移でコード進行を生成  
  └ voicings.py の get_voicing() でボイシング → MIDI 書き出し

使い方例:
    python generator.py --quadrant Q1 --bars 16 --seed 123
"""

from __future__ import annotations
import argparse, random, sys
from pathlib import Path

import numpy as np
import pandas as pd
import mido                             # pip install mido python-rtmidi
from mido import bpm2tempo, Message, MidiFile, MidiTrack

from voicings import get_voicing        # ← 動的ボイシングを使用


# ----------------------------------------------------------------------
# 1. パラメータ
# ----------------------------------------------------------------------
MATRIX_DIR   = Path("markov_matrices_mode")      # build_markov_matrices_by_mode.py の出力先
PPQ          = 480                               # MIDI ticks per beat
TEMPO_BPM    = 120                               # 曲テンポ


# ----------------------------------------------------------------------
# 2. 行列読み込み & モード選択
# ----------------------------------------------------------------------
def load_transition_matrix(quadrant: str, mode: str) -> pd.DataFrame:
    """
    quadrant: 'Q1'〜'Q4'
    mode    : 'major' or 'minor'
    """
    csv_path = MATRIX_DIR / f"{quadrant}_{mode}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Transition CSV not found: {csv_path}")
    return pd.read_csv(csv_path, index_col=0)


def choose_mode_probabilistically(quadrant: str) -> str:
    """
    major/minor どちらを使うかを、各行列の「行合計(=遷移数)」で重み付けして抽選。
    """
    major_df = load_transition_matrix(quadrant, "major")
    minor_df = load_transition_matrix(quadrant, "minor")

    major_weight = major_df.values.sum()
    minor_weight = minor_df.values.sum()
    total        = major_weight + minor_weight

    if total == 0:
        # 両方ゼロなら適当に major
        return "major"

    mode = random.choices(
        population=["major", "minor"],
        weights=[major_weight, minor_weight],
        k=1
    )[0]
    print(f"[Info] {quadrant}: 選択されたモード = {mode}")
    return mode


# ----------------------------------------------------------------------
# 3. コード進行生成
# ----------------------------------------------------------------------
def generate_chord_progression(matrix: pd.DataFrame, length: int = 16) -> list[str]:
    """
    length 小節分のコードをマルコフ遷移で生成
    """
    # 開始コードは総遷移数で重み付け
    start_probs = matrix.sum(axis=1)
    if start_probs.sum() == 0:
        start_code = random.choice(matrix.index.tolist())
    else:
        start_code = random.choices(matrix.index, weights=start_probs, k=1)[0]

    progression = [start_code]
    current     = start_code

    for _ in range(length - 1):
        probs = matrix.loc[current]
        if probs.sum() == 0:
            # 行が全ゼロ → ランダムジャンプ
            current = random.choice(matrix.index.tolist())
        else:
            current = random.choices(matrix.columns, weights=probs, k=1)[0]
        progression.append(current)

    return progression


# ----------------------------------------------------------------------
# 4. MIDI 生成
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

    beat_ticks = ppq
    bar_ticks  = beat_ticks * 4        # 4/4 小節

    for chord in chord_seq:
        notes = get_voicing(chord)     # voicings.py が自動解釈
        # ノートオン
        for note in notes:
            track.append(Message("note_on", note=note, velocity=velocity, time=0))
        # ノートオフ（bar_ticks 後にまとめて）
        track.append(Message("note_off", note=notes[0], velocity=0, time=bar_ticks))
        for note in notes[1:]:
            track.append(Message("note_off", note=note, velocity=0, time=0))

    mid.save(out_path)
    print(f"[Info] MIDI saved to: {out_path.resolve()}")


# ----------------------------------------------------------------------
# 5. メイン
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quadrant", required=True, choices=["Q1","Q2","Q3","Q4"],
                        help="選択する感情象限 (Q1〜Q4)")
    parser.add_argument("--bars", type=int, default=16, help="生成する小節数")
    parser.add_argument("--seed", type=int, default=None, help="乱数シード(再現用)")
    parser.add_argument("--midi", default="out.mid", help="書き出す MIDI ファイル名")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    # 1) モード抽選 → 行列読み込み
    mode     = choose_mode_probabilistically(args.quadrant)
    matrix   = load_transition_matrix(args.quadrant, mode)

    # 2) コード進行生成
    progression = generate_chord_progression(matrix, length=args.bars)
    print("Generated progression:")
    print(" | ".join(progression))

    # 3) MIDI へ
    chords_to_midi(progression, Path(args.midi))


if __name__ == "__main__":
    main()
