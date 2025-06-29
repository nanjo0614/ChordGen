#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
拍位置 (0,1,2,3) × メジャー/マイナー × 感情象限 の
コード遷移行列を生成するスクリプト。

欠損コード(None) は **カウント対象外**。
"""
import argparse
import pickle
from pathlib import Path
from collections import defaultdict, Counter

import pandas as pd
from tqdm import tqdm


# ---------- util ---------- #
def load_pkl(path):
    with path.open("rb") as f:
        return pickle.load(f)


def key_mode(tokens):
    for t in tokens:
        if t["name"] == "Key":
            return "major" if t["value"][0].isupper() else "minor"
    return "unknown"


def chord_and_beat(tokens):
    """(beat, chord) のタプル列を返す (Chord 出現時のみ)"""
    cur_beat = None
    for t in tokens:
        if t["name"] == "Beat":
            cur_beat = t["value"] % 4  # 0–3
        elif t["name"] == "Chord":
            yield cur_beat, t["value"]  # chord は None 可


# ---------- core ---------- #
def collect(args):
    groups = defaultdict(Counter)  # groups[(quad,mode,beat)][(prev,cur)] = n
    root = Path(args.input)

    for pkl_path in tqdm(list(root.rglob("*.pkl")), desc="[Collect]"):
        indices, tokens = load_pkl(pkl_path)
        quadrant = pkl_path.stem.split("_")[0]
        mode = key_mode(tokens)
        if mode not in ("major", "minor"):
            continue

        seq = list(chord_and_beat(tokens))
        for (beat_prev, chord_prev), (beat_cur, chord_cur) in zip(seq, seq[1:]):
            # 欠損コードはスキップ
            if chord_prev is None or chord_cur is None:
                continue
            key = (quadrant, mode, beat_prev)
            groups[key][(chord_prev, chord_cur)] += 1

    return groups


def counter_to_df(counter: Counter):
    rows = sorted({r for r, _ in counter})
    cols = sorted({c for _, c in counter})
    df = pd.DataFrame(0, index=rows, columns=cols, dtype=int)
    for (r, c), v in counter.items():
        df.at[r, c] = v
    return df


def save(groups, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    for (quad, mode, beat), counter in groups.items():
        df_count = counter_to_df(counter)
        if df_count.empty:
            continue
        # ファイル名例：Q3_minor_beat2.csv
        base = f"{quad}_{mode}_beat{beat}"
        f_count = out_dir / f"{base}.csv"
        f_prob = out_dir / f"{base}.prob.csv"

        df_count.to_csv(f_count)
        prob = df_count.div(df_count.sum(axis=1), axis=0).fillna(0)
        prob.to_csv(f_prob, float_format="%.8f")

        print(f"[Saved] {f_count.name}")
        print(f"[Saved] {f_prob.name}")


# ---------- CLI ---------- #
def parse_cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=str,
                    help="functional/lead_sheet ディレクトリ")
    ap.add_argument("--output", required=True, type=str,
                    help="CSV 出力ディレクトリ")
    return ap.parse_args()


def main():
    args = parse_cli()
    groups = collect(args)
    save(groups, Path(args.output))


if __name__ == "__main__":
    main()
