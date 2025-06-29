#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
smooth_markov_matrices.py
-------------------------
  - Laplace 平滑化
  - 自己遷移クリップ (滞在長セーフティ)
  - コード表記の正規化
"""

import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import re

# --------------------------------------------------
# 1. コード表記正規化ユーティリティ
# --------------------------------------------------
_re_accidental  = re.compile(r'([A-G])([b#])')
_re_slash_chord = re.compile(r'(.+?)/.+')          # 転回形など /B

def normalize_symbol(sym: str) -> str:
    """
    EMOPIA+ の表記を voicings.py が扱える形へ統一する
      例) 'IV#_o7'  -> 'IV#_o7' (そのまま)
          'I_bm7'  -> 'Ibm_m7'
          'V/VI'   -> 'V' (スラッシュ以降削除)
    """
    # 転回形／分数コードを削除
    sym = _re_slash_chord.sub(r'\1', sym)

    # 'I_bm7' のような変化記号が '_' 手前に来るパターンを修正
    if '_b' in sym or '_#' in sym:
        # 'IV#_o7' は OK, 'I_bm7' を 'Ib_m7' に
        core, suffix = sym.split('_', 1)
        core = core.replace('b', 'b').replace('#', '#')
        sym  = f"{core}_{suffix}"

    # 変化記号記号はそのまま (#, b)
    return sym

# --------------------------------------------------
# 2. 行列平滑化 & クリップ
# --------------------------------------------------
def smooth_and_clip(df: pd.DataFrame, tau: float) -> pd.DataFrame:
    # Laplace +1
    counts = df.copy().fillna(0).astype(float) + 1.0

    # 自己遷移クリップ
    for idx in counts.index:
        row = counts.loc[idx]
        p_self = row[idx]
        total  = row.sum()
        p = p_self / total
        if p > tau:
            # 過剰分を他に再配分
            excess = p - tau
            keep   = tau * total          # クリップ後の自己遷移回数
            give   = excess * total       # 減らす回数
            counts.loc[idx, idx] = keep
            # 他コードへ均等に配る（自己以外の列）
            others = row.index.difference([idx])
            counts.loc[idx, others] += give / len(others)

    # 正規化 (行和=1 の確率行列)
    probs = counts.div(counts.sum(axis=1), axis=0)
    return probs

# --------------------------------------------------
# 3. メイン処理
# --------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input",  required=True, help="元の遷移行列CSVが入ったディレクトリ")
    ap.add_argument("--output", required=True, help="平滑化後を書き出すディレクトリ")
    ap.add_argument("--tau", type=float, default=0.4, help="自己遷移の最大確率 (0.0–1.0)")
    args = ap.parse_args()

    in_dir  = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(in_dir.glob("*.csv"))
    if not csv_files:
        print("[Error] 入力ディレクトリに csv が見つかりません。")
        return

    for csv_path in csv_files:
        df = pd.read_csv(csv_path, index_col=0)

        # -------- 正規化：行・列ラベルを変換 --------
        mapping = {s: normalize_symbol(s) for s in df.index}
        df.rename(index=mapping, columns=mapping, inplace=True)

        # ラベル集合を再統一
        all_syms = sorted(set(df.index) | set(df.columns))
        df = df.reindex(index=all_syms, columns=all_syms, fill_value=0)

        # -------- 平滑化＋クリップ＋確率化 --------
        prob_df = smooth_and_clip(df, tau=args.tau)

        # -------- 保存 --------
        outfile = out_dir / (csv_path.stem + ".prob.csv")
        prob_df.to_csv(outfile, float_format="%.8f")
        print(f"[Saved] {outfile.name}")

if __name__ == "__main__":
    main()
