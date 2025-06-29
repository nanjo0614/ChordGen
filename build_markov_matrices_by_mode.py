#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_markov_matrices_by_mode.py

EMOPIA+（functional/lead_sheet）の pkl を走査し，
Major / Minor × Emotion Quadrant(Q1–Q4) ごとの
1st-order Markov 遷移行列を作成して CSV 出力する。

Usage:
    python build_markov_matrices_by_mode.py
        --input  "C:\\ChordGen\\EMOPIA+\\functional\\lead_sheet"
        --output "C:\\ChordGen\\markov_matrices_mode"
"""

import argparse
import logging
import pickle
from collections import defaultdict, Counter
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s %(message)s"
)
logger = logging.getLogger(__name__)


# --------------------------------------------------
# コード文字列を抽出するユーティリティ
# --------------------------------------------------
def extract_chords(event_list):
    """
    functional representation の event_list から
    'Chord' イベントの value だけを順番に取り出す
    """
    chords = []
    for ev in event_list:
        if isinstance(ev, dict) and ev["name"] == "Chord":
            chords.append(ev["value"])
    return chords


# --------------------------------------------------
# メイン処理
# --------------------------------------------------
def build_matrices(input_dir: Path, output_dir: Path):
    """
    input_dir 直下の pkl を走査して
    {quadrant}_{mode}.csv を生成
    """
    # {quadrant -> {mode -> Counter[(prev,next)]}}
    transition_counts = defaultdict(lambda: defaultdict(Counter))

    # すべてのコード集合を集める
    all_codes = set()

    # --- 1) pkl を走査してカウント -----------------
    for pkl_path in input_dir.glob("*.pkl"):
        try:
            with open(pkl_path, "rb") as f:
                tup = pickle.load(f)
        except Exception as e:
            logger.error("%s: %s", pkl_path.name, e)
            continue

        events = tup[1]  # element 1 が event list
        meta = {ev["name"]: ev["value"]
                for ev in events if isinstance(ev, dict)
                and ev["name"] in {"Emotion", "Key"}}

        emotion = meta.get("Emotion")        # 'Positive' or 'Negative'
        key_root = meta.get("Key")           # C, a, etc. ここでは root だけ使う

        # key が大文字なら Major, 小文字なら Minor という前提
        mode = "major" if key_root.isupper() else "minor"

        # Emotion × arousal で Q1–Q4 判定 (簡略化版)
        # pkl ファイル名に Q1_ ... が含まれている前提でも可
        quadrant = pkl_path.name.split("_")[0]  # 'Q1' 等

        chords = extract_chords(events)
        all_codes.update(chords)

        if len(chords) < 2:
            continue
        for prev, nxt in zip(chords[:-1], chords[1:]):
            transition_counts[quadrant][mode][(prev, nxt)] += 1

    # --- 2) 各 Q×mode ごとに DataFrame を作る -------
    output_dir.mkdir(parents=True, exist_ok=True)
    for quadrant, mode_dict in transition_counts.items():
        for mode, counter in mode_dict.items():
            # 行・列を完全にそろえる
            codes_sorted = sorted(all_codes)
            df = pd.DataFrame(
                0, index=codes_sorted, columns=codes_sorted, dtype=int
            )

            # カウントを埋める
            for (prev, nxt), cnt in counter.items():
                df.at[prev, nxt] = cnt

            # 行を正規化して確率化（行和=1、ゼロ行はそのまま）
            prob_df = df.div(df.sum(axis=1).replace(0, 1), axis=0)

            out_name = f"{quadrant}_{mode}.csv"
            prob_df.to_csv(output_dir / out_name, encoding="utf-8-sig")
            logger.info("saved %s", out_name)


# --------------------------------------------------
# CLI
# --------------------------------------------------
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True,
                    help="pkl 保存フォルダ (lead_sheet)")
    ap.add_argument("-o", "--output", required=True,
                    help="CSV 出力フォルダ")
    return ap.parse_args()


def main():
    args = parse_args()
    in_dir = Path(args.input)
    out_dir = Path(args.output)

    if not in_dir.exists():
        logger.error("input dir not found: %s", in_dir)
        return
    build_matrices(in_dir, out_dir)


if __name__ == "__main__":
    main()
