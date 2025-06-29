"""
utils.py  –  Semi-Markov コード進行システム共通ユーティリティ
---------------------------------------------------------------
build_semi.py / generator_semi.py / voicings.py など複数スクリプト間で
共有する汎用ロジックを一元管理する。

主な提供機能
-------------
A. 表記正規化           : normalize_symbol
B. ローマ数字→半音値    : degree_to_semitone
C. コードタイプ辞書      : CHORD_TYPES
D. CSV I/O              : save_matrix / load_matrix
E. 自己遷移スムージング  : smooth_self_transition
F. 滞在長抽出           : extract_stay_lengths
G. 乱数シード固定        : set_seed
H. ロガー生成           : get_logger
"""

from __future__ import annotations
import re, math, random, logging
from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd

# ======== A. 表記正規化 ===================================================

_ROMAN_RE = re.compile(r"([ivIV]+)([#b]?)(?:_)?(.+)?")  # 例: II#_M7 → ("II","#","M7")
_ACC_MAP  = {"#": 1, "♯": 1, "b": -1, "♭": -1, "": 0}

def normalize_symbol(sym: str) -> str:
    """
    ・大文字ローマ数字へ統一
    ・Unicode ♯♭ を #/b に
    ・空白や多重アンダースコアを除去
    """
    if sym is None:
        return "None_None"

    sym = sym.strip().replace("♯", "#").replace("♭", "b")
    m = _ROMAN_RE.fullmatch(sym)
    if not m:
        # 既に root 音名 (C#, D, …) の場合や不明表記はそのまま返す
        return sym.replace(" ", "").upper()

    deg, acc, ctype = m.groups()
    deg = deg.upper()
    acc = acc or ""
    ctype = (ctype or "").upper()
    return f"{deg}{acc}_{ctype}" if ctype else f"{deg}{acc}"

# ======== B. ローマ数字→半音値 ===========================================

_DEGREE_BASE = {  # C メジャースケールを基準にした度数→半音
    "I": 0,  "II": 2,  "III": 4,  "IV": 5,
    "V": 7,  "VI": 9,  "VII": 11
}

def degree_to_semitone(deg: str) -> int:
    """
    'II#' → 3   /  'VIb' → 8
    """
    m = re.fullmatch(r"([IV]+)([#b]?)", deg.upper())
    if not m:
        raise KeyError(f"Illegal roman numeral token: {deg}")
    base, acc = m.groups()
    semitone = _DEGREE_BASE[base] + _ACC_MAP[acc]
    return semitone % 12

# ======== C. コードタイプ定義 ============================================

# ベース 0 (root) からの相対ピッチ列
CHORD_TYPES: Dict[str, List[int]] = {
    "":       [0, 4, 7],           # major triad
    "M":      [0, 4, 7],
    "MAJ":    [0, 4, 7],
    "M7":     [0, 4, 7, 11],
    "MAJ7":   [0, 4, 7, 11],
    "6":      [0, 4, 7, 9],
    "M6":     [0, 4, 7, 9],

    "M9":     [0, 4, 7, 11, 14],
    "+":      [0, 4, 8],           # augmented
    "+7":     [0, 4, 8, 10],

    "MIN":    [0, 3, 7],
    "M-":     [0, 3, 7],
    "MIM":    [0, 3, 7],           # typo safe
    "MIM7":   [0, 3, 7, 10],
    "M9-":    [0, 3, 7, 10, 14],
    "M11":    [0, 3, 7, 10, 14, 17],
    "M13":    [0, 3, 7, 10, 14, 17, 21],
    "M7":     [0, 3, 7, 10],       # minor 7
    "M6":     [0, 3, 7, 9],        # minor 6

    "7":      [0, 4, 7, 10],       # dominant 7
    "9":      [0, 4, 7, 10, 14],

    "SUS2":   [0, 2, 7],
    "SUS4":   [0, 5, 7],

    "DIM":    [0, 3, 6],
    "O":      [0, 3, 6],           # alternate dim symbol
    "DIM7":   [0, 3, 6, 9],
    "O7":     [0, 3, 6, 9],
    "HDIM7":  [0, 3, 6, 10],

    # 拡張コードも適宜追加
}

# ======== D. CSV I/O =====================================================

def save_matrix(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, float_format="%.6f")   # 精度固定
    print(f"[Saved] {path.name}")

def load_matrix(path: Path, *, as_prob: bool = False) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, index_col=0)
    if as_prob:
        # 端的な正規化チェック（誤差 1e-6 以内なら OK、超えれば再正規化）
        sums = df.sum(axis=1).values
        if not np.allclose(sums, 1.0, atol=1e-6):
            df = df.div(sums, axis=0)
    return df

# ======== E. 自己遷移スムージング ========================================

def smooth_self_transition(df: pd.DataFrame, tau: float = 0.4) -> pd.DataFrame:
    """
    各行の自己遷移セル p_ii を p'_ii = (1-τ)*p_ii + τ*(1/n) に混合。
    n は状態数。行合計は自動で再正規化する。
    """
    n = len(df)
    uniform = 1.0 / n
    df_sm = df.copy()
    for idx in df.index:
        p_ii = df.loc[idx, idx]
        df_sm.loc[idx, idx] = (1.0 - tau) * p_ii + tau * uniform
    # 行正規化
    df_sm = df_sm.div(df_sm.sum(axis=1), axis=0)
    return df_sm

# ======== F. 滞在長抽出 (Semi-Markov) ====================================

def extract_stay_lengths(seq: List[str]) -> List[int]:
    """
    ['C','C','Dm','Dm','Dm','G'] → [2,3,1]
    """
    if not seq:
        return []
    lengths = []
    cur, cnt = seq[0], 1
    for s in seq[1:]:
        if s == cur:
            cnt += 1
        else:
            lengths.append(cnt)
            cur, cnt = s, 1
    lengths.append(cnt)
    return lengths

# ======== G. 乱数シード固定 =============================================

def set_seed(seed: int | None):
    if seed is None:
        return
    random.seed(seed)
    np.random.seed(seed)

# ======== H. 統一ロガー ==================================================

def get_logger(name: str = "ChordGen") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # 既に設定済み
    logger.setLevel(logging.INFO)
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(h)
    return logger
