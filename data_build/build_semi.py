#!/usr/bin/env python
# -----------------------------------------------
#  build_semi.py
#  ----------------------------------------------
#  ・入力  : 〈quadrant〉_〈mode〉.csv
#            - Q1_major.csv, Q3_minor.csv …など
#            （行＝現在コード，列＝次コード，値＝遷移回数）
#  ・処理  : τ 加法平滑化 → 行正規化（確率化）
#            ＋ self-transition (対角) はそのまま保持
#  ・出力  : 〈quadrant〉_〈mode〉.pkl     （pickle / pandas DataFrame）
#            〈quadrant〉_〈mode〉.prob.csv（人間可読の確率表）
#            mode_stats.json               （各象限で major / minor を引く確率）
#
#  使い方:
#    python build_semi.py \
#        --input  "C:\ChordGen\markov_matrices_mode" \
#        --output "C:\ChordGen\matrices" \
#        --tau 0.4
# -----------------------------------------------
import argparse
import json
import pickle
from pathlib import Path
from collections import Counter

import pandas as pd

# ---------- ユーティリティ -------------------------------------------------
def load_counts(csv_path: Path) -> pd.DataFrame:
    """遷移回数 CSV を DataFrame で読み込む（NaN→0）"""
    return pd.read_csv(csv_path, index_col=0).fillna(0)

def smooth_and_normalise(df: pd.DataFrame, tau: float) -> pd.DataFrame:
    """
    τ 加法平滑化 → 行正規化
      P_ij = (C_ij + τ) / Σ_k (C_ik + τ)
    """
    df = df + tau
    df = df.div(df.sum(axis=1).replace(0, 1), axis=0)
    return df

def collect_mode_stats(csv_paths):
    """象限ごとの major / minor 割合をカウント → 確率 dict を返す"""
    counter = Counter()
    for p in csv_paths:
        q, mode = p.stem.split("_")[:2]           # 'Q3_major' → ['Q3', 'major']
        counter[(q, mode)] += 1

    stats = {}
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        maj, minu = counter[(q, "major")], counter[(q, "minor")]
        tot = maj + minu
        stats[q] = {"major": maj / tot if tot else 0.5,
                    "minor": minu / tot if tot else 0.5}
    return stats

# ---------- 本体 -----------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Build semi-Markov matrices & mode_stats.json")
    ap.add_argument("--input", required=True,  help="Dir containing raw Q*_*.csv count matrices")
    ap.add_argument("--output", required=True, help="Dir to save .pkl / .prob.csv / mode_stats.json")
    ap.add_argument("--tau", type=float, default=0.4, help="Additive smoothing constant (τ)")
    args = ap.parse_args()

    in_dir  = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_paths = sorted([p for p in in_dir.glob("Q*_*.csv") if not p.name.endswith(".prob.csv")])
    if not csv_paths:
        print(f"[WARN] No Q*_*.csv files found in {in_dir}")
        return

    print(f"[INFO] Scan: {in_dir}")
    print(f"[INFO] Quadrant×Mode found: {len(csv_paths)}")

    # ----- major / minor の比率を算出 -----
    stats = collect_mode_stats(csv_paths)
    with open(out_dir / "mode_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print("[Saved] mode_stats.json")

    # ----- 各行列を平滑化 → 保存 -----
    for csv_path in csv_paths:
        stem = csv_path.stem                      # 例 'Q3_major'
        df_counts = load_counts(csv_path)
        df_prob   = smooth_and_normalise(df_counts, args.tau)

        df_prob.to_csv(out_dir / f"{stem}.prob.csv")
        with open(out_dir / f"{stem}.pkl", "wb") as f:
            pickle.dump(df_prob, f)

        print(f"[Saved] {stem}.pkl / .prob.csv")

    print("[INFO] Done.")

# --------------------------------------------------------------------------
if __name__ == "__main__":
    main()
