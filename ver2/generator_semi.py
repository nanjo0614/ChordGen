#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generator_semi.py
==========================================
■ 目的
    - 感情象限(Q1–Q4) を入力すると
      ・その象限の major/minor 割合を EMOPIA+ 統計から確率的に選択
      ・滞在長セーフティ・マルコフ (Self-Stay Safe Semi-Markov)
        でバー単位のコード進行を生成
      ・MIDI ファイルを書き出す（任意）
■ 必要ファイル
    build_semi.py で生成済みの
        {Qx}_{mode}.prob.csv         … 遷移確率行列 (自己遷移込み)
    mode_stats.json                  … 各象限の major/minor 出現比率
■ 依存
    pandas, numpy, pretty_midi, voicings.py
"""

import json
import math
import random
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import pretty_midi as pm

from voicings import get_voicing   # 先ほど作成した voicings.py を利用


# ------------------------------------------------------------
# 設定
BASE_DIR   = Path(__file__).resolve().parent           # スクリプトが置かれたフォルダ
MATRIX_DIR = BASE_DIR / "semi_matrices"               # build_semi.py 出力
STATS_JSON = BASE_DIR / "mode_stats.json"             # major/minor 割合
PPQ        = 480
TEMPO_BPM  = 100


# ------------------------------------------------------------
# ユーティリティ
def load_matrix(quadrant: str, mode: str) -> pd.DataFrame:
    csv_path = MATRIX_DIR / f"{quadrant}_{mode}.prob.csv"
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    df = pd.read_csv(csv_path, index_col=0)
    return df


def choose_mode(quadrant: str, rng: random.Random) -> str:
    """
    EMOPIA+ 出現頻度に基づいて major/minor を確率選択
    """
    with open(STATS_JSON, "r", encoding="utf-8") as f:
        stats = json.load(f)
    major_ratio = stats[quadrant]["major_ratio"]  # 0〜1
    return "major" if rng.random() < major_ratio else "minor"


def expected_stay(p_self: float) -> float:
    """
    自己遷移確率 p_self から平均滞在長 E[L]=1/(1−p)
    """
    if p_self >= 0.999:           # ほぼ抜け出せない場合は上限
        return 16.0
    return 1.0 / max(1e-6, 1 - p_self)


def next_chord(cur: str,
               stay_cnt: int,
               df: pd.DataFrame,
               rng: random.Random,
               alpha: float = 1.5) -> str:
    """
    Self-Stay Safe Semi-Markov:
      - 平均滞在長 μ = 1/(1-p_ii)
      - 許容滞在長 L_max = ceil(α · μ)
      - stay_cnt >= L_max なら自己遷移確率を0にして再サンプリング
    """
    probs = df.loc[cur].copy()  # Series
    p_self = probs[cur]
    mu = expected_stay(p_self)
    max_stay = max(2, math.ceil(alpha * mu))
    if stay_cnt >= max_stay:
        probs[cur] = 0.0
    s = probs.sum()
    if s == 0.0:
        # フォールバック: 対角を残して正規化
        probs[cur] = 1.0
        s = 1.0
    probs = probs / s
    nxt = rng.choices(probs.index.tolist(), weights=probs.values, k=1)[0]
    return nxt


# ------------------------------------------------------------
# コード進行 → MIDI
def chords_to_midi(chords: List[str],
                   out_path: Path,
                   tempo_bpm: int = TEMPO_BPM,
                   ppq: int = PPQ):
    pm_obj = pm.PrettyMIDI(resolution=ppq, initial_tempo=tempo_bpm)
    piano = pm.Instrument(program=0, name="Piano")
    cur_time = 0.0
    dur = 4 * 60 / tempo_bpm   # 1 bar (4 beats) 長さ [sec]
    for ch in chords:
        notes = get_voicing(ch)
        for n in notes:
            piano.notes.append(pm.Note(
                velocity=90,
                pitch=n,
                start=cur_time,
                end=cur_time + dur
            ))
        cur_time += dur
    pm_obj.instruments.append(piano)
    pm_obj.write(str(out_path))
    print(f"[Info] MIDI saved to: {out_path}")


# ------------------------------------------------------------
# 進行生成
def generate_progression(quadrant: str,
                         bars: int,
                         seed: int | None = None) -> tuple[str, List[str]]:
    rng = random.Random(seed)
    mode = choose_mode(quadrant, rng)
    df = load_matrix(quadrant, mode)

    # 開始コード: 最大出現回数コードを root に
    start = df.sum(axis=1).idxmax()
    progression = [start]

    stay_cnt = 0
    cur = start
    for beat in range(1, bars):
        nxt = next_chord(cur, stay_cnt, df, rng)
        if nxt == cur:
            stay_cnt += 1
        else:
            stay_cnt = 0
        progression.append(nxt)
        cur = nxt
    return mode, progression


# ------------------------------------------------------------
# CLI
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Semi-Markov chord progression generator (B案)")
    parser.add_argument("--quadrant", required=True,
                        choices=["Q1", "Q2", "Q3", "Q4"])
    parser.add_argument("--bars", type=int, default=16)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--midi", type=str, default=None,
                        help="出力 MIDI ファイルパス (指定しないと生成のみ)")
    args = parser.parse_args()

    mode, prog = generate_progression(args.quadrant, args.bars, args.seed)

    print(f"[Info] {args.quadrant}: 選択されたモード = {mode}")
    print("Generated progression:")
    print(" | ".join(prog))

    if args.midi:
        chords_to_midi(prog, Path(args.midi))
