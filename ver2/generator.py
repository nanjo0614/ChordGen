#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
generator.py
------------
1. 四象限(Q1–Q4)を指定してコード進行を生成
2. 滞在長セーフティ・マルコフ & 拍位置×コード遷移を利用
3. 生成したコード進行をMIDI化
   - 依存: pandas, numpy, pretty_midi, argparse, pathlib
"""

import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd
import pretty_midi as pm

# ==========================================================
# 設定
# ----------------------------------------------------------
MODE_DIR = Path("markov_matrices_mode_smooth")
BEAT_DIR = Path("markov_matrices_beat_smooth")
PPQ       = 480          # ticks/quarter
TEMPO_BPM = 120
INSTRUMENT = 0           # Acoustic Grand Piano

# ==========================================================
# ユーティリティ
# ----------------------------------------------------------
def load_csv(path: Path) -> pd.DataFrame:
    """
    指定パスに .csv が無ければ .prob.csv を試す。
    """
    if path.exists():
        return pd.read_csv(path, index_col=0)
    prob_path = path.with_suffix(".prob.csv")
    if prob_path.exists():
        return pd.read_csv(prob_path, index_col=0)
    raise FileNotFoundError(f"matrix not found: {path} / {prob_path}")

def get_matrix(quadrant: str, mode: str, beat: int | None = None) -> pd.DataFrame:
    """
    quadrant (Q1–Q4), mode ('major'|'minor'), beat(0‒3|None)
      -> 対応する遷移行列(DataFrame)を返す
    """
    if beat is None:
        return load_csv(MODE_DIR / f"{quadrant}_{mode}.csv")
    else:
        return load_csv(BEAT_DIR / f"{quadrant}_{mode}_beat{beat}.csv")

# ----------------------------------------------------------
def safe_choice(probs: pd.Series, stay: int, max_stay: int = 4) -> str:
    """
    滞在長セーフティ・マルコフ (LoopSafe)：
    * 同じコードが続き過ぎる場合，自己遷移を減衰させる
    """
    if stay >= max_stay:
        probs = probs.copy()
        probs.loc[probs.idxmax()] = 0.0  # 最頻自己遷移を潰す
    total = probs.sum()
    if not np.isfinite(total) or total == 0:
        # 全部0 → 一様分布
        probs[:] = 1.0
        total = probs.sum()
    return random.choices(probs.index, weights=probs / total, k=1)[0]

def next_chord(cur: str, beat: int, quadrant: str, mode: str, stay: int) -> str:
    """
    現在コード cur・拍位置 beat から次コードを決定
    """
    mat = get_matrix(quadrant, mode, beat)
    if cur not in mat.index:
        # 未収録コード：列の総和で代用
        probs = mat.sum(axis=0)
    else:
        probs = mat.loc[cur]
    return safe_choice(probs, stay)

# ----------------------------------------------------------
def generate_progression(quadrant: str, bars: int, seed: int | None = None):
    """
    四象限→ mode を確率決定 → progression 生成
    """
    if seed is not None:
        random.seed(seed); np.random.seed(seed)

    # モード選択：major/minor 出現頻度をモード行列の行数で推定
    n_major = len(load_csv(MODE_DIR / f"{quadrant}_major.csv"))
    n_minor = len(load_csv(MODE_DIR / f"{quadrant}_minor.csv"))
    mode = random.choices(["major", "minor"], weights=[n_major, n_minor])[0]
    print(f"[Info] {quadrant}: 選択されたモード = {mode}")

    # 1小節=4拍・コード1拍固定
    beats_total = bars * 4
    # スタートコード：matrix 全行からランダム
    start_mat = get_matrix(quadrant, mode)
    cur = random.choice(start_mat.index.to_list())
    progression = [cur]

    stay = 0
    for i in range(1, beats_total):
        beat = i % 4
        nxt = next_chord(cur, beat, quadrant, mode, stay)
        progression.append(nxt)
        stay = stay + 1 if nxt == cur else 1
        cur = nxt

    return mode, progression

# ==========================================================
# voicing
# ----------------------------------------------------------
VOICING_PATH = Path("voicings.py")
import importlib.util, sys
spec = importlib.util.spec_from_file_location("voicings", VOICING_PATH)
voicings = importlib.util.module_from_spec(spec)
sys.modules["voicings"] = voicings
spec.loader.exec_module(voicings)
get_voicing = voicings.get_voicing

# ----------------------------------------------------------
def chords_to_midi(prog: list[str], out_path: Path,
                   tempo_bpm: int = TEMPO_BPM, ppq: int = PPQ):
    midi = pm.PrettyMIDI(resolution=ppq, initial_tempo=tempo_bpm)
    inst = pm.Instrument(program=INSTRUMENT)
    tick = 0
    dur = ppq  # 1拍
    velocity = 90
    for ch in prog:
        for note_num in get_voicing(ch):
            note = pm.Note(velocity, note_num, tick / ppq, (tick+dur) / ppq)
            inst.notes.append(note)
        tick += dur
    midi.instruments.append(inst)
    midi.write(str(out_path))
    print(f"[Info] MIDI saved to: {out_path}")

# ==========================================================
# CLI
# ----------------------------------------------------------
def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quadrant", required=True, choices=["Q1", "Q2", "Q3", "Q4"])
    ap.add_argument("--bars", type=int, default=16)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--midi", type=str, default="out.mid")
    args = ap.parse_args()

    mode, prog = generate_progression(args.quadrant, args.bars, args.seed)
    print("Generated progression:")
    print(" | ".join(prog))
    chords_to_midi(prog, Path(args.midi))

if __name__ == "__main__":
    cli()
