# ============================================================
#  chord_voicings.py
#  ------------------------------------------------------------
#  • EMOPIA 由来の Markov 行列 CSV に現れる全コード表記を
#    パースして MIDI ボイシングを返すユーティリティ
#  • roman numeral root (I–VII) + accidental (#/b) + "_" +
#    quality   ──>  例:  "IV#_o7",  "II_/o7", "V_sus4" …
# ============================================================

from __future__ import annotations
import re
from typing import List, Dict

# ----------------------------------------------------------------
# 1) 定数定義
# ----------------------------------------------------------------
_ROMAN_TO_SEMITONE_MAJOR = {
    'I': 0, 'II': 2, 'III': 4, 'IV': 5,
    'V': 7, 'VI': 9, 'VII': 11,
}
# マイナーは "relative" 解釈 (Aeolian) だが，
# ルート度数だけで良いので上記と同じにしておく

# 品質 -> 相対インターバル表
_QUALITY_INTERVALS: Dict[str, List[int]] = {
    'M'    : [0, 4, 7],
    'M7'   : [0, 4, 7, 11],
    'm'    : [0, 3, 7],
    'm7'   : [0, 3, 7, 10],
    '7'    : [0, 4, 7, 10],
    '+'    : [0, 4, 8],            # augmented
    'o'    : [0, 3, 6],            # diminished triad
    'o7'   : [0, 3, 6, 9],         # dim-7
    '/o7'  : [0, 3, 6, 10],        # half-dim (ø7)
    'sus2' : [0, 2, 7],
    'sus4' : [0, 5, 7],
}

# ----------------------------------------------------------------
# 2) ヘルパ: ルートを半音値に変換
# ----------------------------------------------------------------
def _roman_root_to_semitone(root: str) -> int:
    """
    'IV#' -> 6  ( = 5 + 1 )
    'VIb' -> 8  ( = 9 - 1 )
    """
    m = re.fullmatch(r'(I{1,3}|IV|V|VI|VII)([#b]?)', root)
    if not m:
        raise ValueError(f'Invalid roman numeral root: {root}')
    base = _ROMAN_TO_SEMITONE_MAJOR[m.group(1)]
    acc  = m.group(2)
    if acc == '#':
        base += 1
    elif acc == 'b':
        base -= 1
    return base % 12

# ----------------------------------------------------------------
# 3) パブリック API
# ----------------------------------------------------------------
def get_intervals(quality: str) -> List[int]:
    """
    品質を渡すと 0 からの相対インターバルを返す
    例) 'M7' -> [0,4,7,11]
    """
    if quality not in _QUALITY_INTERVALS:
        raise KeyError(f'Unknown quality: {quality}')
    return _QUALITY_INTERVALS[quality]

def get_voicing(chord_symbol: str,
                key: str = 'C',
                base_oct: int = 4) -> List[int]:
    """
    chord_symbol : 'IV#_o7' など
    key          : 'C', 'Am' のようにトニックを英字で
    base_oct     : ルートを置くオクターブ番号
    -----------------------------------------------------------
    戻り値: MIDI ノート番号リスト (root ≤ others)
    """
    # ------------- 1) key の MIDI 値 -------------------------
    key_letter = key[0].upper()
    letter_to_pc = {'C':0,'D':2,'E':4,'F':5,
                    'G':7,'A':9,'B':11}
    if key_letter not in letter_to_pc:
        raise ValueError(f'Unsupported key: {key}')
    key_pc = letter_to_pc[key_letter]

    # ------------- 2) symbol の分解 -------------------------
    try:
        root_part, qual = chord_symbol.split('_', 1)
    except ValueError:
        raise ValueError('Chord symbol must contain "_" : ' + chord_symbol)

    root_pc_from_key = _roman_root_to_semitone(root_part)
    root_pc = (key_pc + root_pc_from_key) % 12

    # ------------- 3) intervals & MIDI ---------------------
    intervals = get_intervals(qual)
    root_midi = root_pc + 12 * base_oct
    return [root_midi + iv for iv in intervals]

# ----------------------------------------------------------------
# 4) デバッグ用 CLI
# ----------------------------------------------------------------
if __name__ == '__main__':
    import argparse, sys
    ap = argparse.ArgumentParser(
        description='Roman-numeral chord voicing utility'
    )
    ap.add_argument('symbol', help='例) "IV#_o7"')
    ap.add_argument('--key', default='C', help='C, G, Am …')
    ns = ap.parse_args()

    try:
        notes = get_voicing(ns.symbol, key=ns.key)
        print(f'{ns.symbol} in {ns.key}: {notes}')
    except Exception as e:
        print('Error:', e, file=sys.stderr)
        sys.exit(1)
