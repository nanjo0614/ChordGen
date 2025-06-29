#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EMOPIA+（functional/lead_sheet 形式）の pkl から
  ─ メジャー / マイナー × 感情象限(Q1–Q4)
のコード遷移カウント／確率行列を生成するスクリプト

欠損コード(None) は **カウント対象外**。
"""
import argparse
import pickle
from pathlib import Path
from collections import defaultdict, Counter

import pandas as pd
from tqdm import tqdm


# ---------- ユーティリティ ---------- #
def load_pkl(path: Path):
    """(indices, tokens) 形式の pkl を読み込む"""
    with path.open("rb") as f:
        return pickle.load(f)


def read_lead_sheets(root: Path):
    """root 配下の *.pkl をすべて yield"""
    for p in root.rglob("*.pkl"):
        yield p, load_pkl(p)


def key_mode(tokens):
    """Key イベントから 'major' or 'minor' を返す"""
    for t in tokens:
        if t["name"] == "Key":
            # 大文字 → major, 小文字 → minor
            return "major" if t["value"][0].isupper() else "minor"
    return "unknown"


def chord_sequence(tokens):
    """Chord トークンのみを順番に抽出 (None を許す)"""
    for t in tokens:
        if t["name"] == "Chord":
            yield t["value"]  # None をそのまま返す


# ---------- 行列作成 ---------- #
def collect(args):
    """lead_sheet → 遷移対を収集して dict[group][(prev,cur)] += 1"""
    groups = defaultdict(Counter)  # e.g. groups['Q1_major'][(I_M, V_7)] = 3
    root = Path(args.input)

    for pkl_path, (indices, tokens) in tqdm(list(read_lead_sheets(root)),
                                            desc="[Collect]"):
        # 感情象限はファイル名プレフィックス(Q1_...)から取得
        quadrant = pkl_path.stem.split("_")[0]  # Q1, Q2, ...

        mode = key_mode(tokens)  # 'major' or 'minor'
        if mode not in ("major", "minor"):
            continue  # キー不明のデータはスキップ

        group_key = f"{quadrant}_{mode}"

        # コード系列を走査し、None を含む対はスキップ
        seq = list(chord_sequence(tokens))
        for prev, cur in zip(seq, seq[1:]):
            if prev is None or cur is None:
                continue
            groups[group_key][(prev, cur)] += 1

    return groups


def counter_to_df(counter: Counter):
    """Counter → (index=row, columns=col) DataFrame"""
    rows = sorted({r for r, _ in counter})
    cols = sorted({c for _, c in counter})
    df = pd.DataFrame(0, index=rows, columns=cols, dtype=int)
    for (r, c), v in counter.items():
        df.at[r, c] = v
    return df


def save_matrices(groups: dict, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    for g, counter in groups.items():
        df_count = counter_to_df(counter)
        if df_count.empty:
            continue  # 実データ 0 件は保存しない

        # --- count matrix (.csv) ---
        path_count = out_dir / f"{g}.csv"
        df_count.to_csv(path_count)
        print(f"[Saved] {path_count.name}")

        # --- probability matrix (.prob.csv) ---
        prob = df_count.div(df_count.sum(axis=1), axis=0).fillna(0)
        path_prob = out_dir / f"{g}.prob.csv"
        prob.to_csv(path_prob, float_format="%.8f")
        print(f"[Saved] {path_prob.name}")


# ---------- CLI ---------- #
def parse_cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=str, required=True,
                    help="functional/lead_sheet ディレクトリ")
    ap.add_argument("--output", type=str, required=True,
                    help="CSV 出力ディレクトリ")
    return ap.parse_args()


def main():
    args = parse_cli()
    groups = collect(args)
    save_matrices(groups, Path(args.output))


if __name__ == "__main__":
    main()
