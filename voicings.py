"""
voicings.py  (revised)
----------------------
コードシンボル 'C_M', 'F#_m7', 'II#_M7', 'III_+' などを
MIDI ノート番号リストへ変換するユーティリティ。
  * トニック C (= MIDI 60) を基準に
    ローマ数字 (I–VII) + #/b も前後どちらも対応。
"""

from __future__ import annotations
from typing import Dict, List, Tuple
import re

# ============================================
# 0. 基本設定
# ============================================
TONIC_PITCH = 60  # C4 を 60 とする

# ============================================
# 1. 実音名 → MIDI
# ============================================
BASE_PITCH: Dict[str, int] = {
    "C": 60, "C#": 61, "Db": 61,
    "D": 62, "D#": 63, "Eb": 63,
    "E": 64,
    "F": 65, "F#": 66, "Gb": 66,
    "G": 67, "G#": 68, "Ab": 68,
    "A": 69, "A#": 70, "Bb": 70,
    "B": 71,
}

# ============================================
# 2. ローマ数字 → トニックからの半音
# ============================================
DEGREE_OFFSETS_MAJOR: Dict[str, int] = {
    "I": 0, "II": 2, "III": 4, "IV": 5,
    "V": 7, "VI": 9, "VII": 11,
}

# ── 先頭／末尾どちらの # / b も許可する ────────────
ROMAN_RE = re.compile(
    r"^(?P<pre_acc>[#b]?)(?P<deg>I{1,3}|IV|V|VI{0,1}|VII)(?P<post_acc>[#b]?)$"
)

def parse_degree(token: str) -> int:
    """
    'II#'   → D# (2 + 1)
    '#IV'   → F# (5 + 1)
    'bVIb'  → Gb (9 - 2)  ※非現実だが一応対応
    """
    m = ROMAN_RE.match(token)
    if not m:
        raise KeyError(f"[parse_degree] 不正なローマ数字表記: {token}")

    deg = m.group("deg")
    accidental_cnt = (
        (1 if m.group("pre_acc") == "#" else -1 if m.group("pre_acc") == "b" else 0) +
        (1 if m.group("post_acc") == "#" else -1 if m.group("post_acc") == "b" else 0)
    )

    offset = DEGREE_OFFSETS_MAJOR[deg] + accidental_cnt
    return (TONIC_PITCH + offset) % 128  # wrap just in case

# ============================================
# 3. コードタイプ正規化
# ============================================
CHORD_ALIAS: Dict[str, str] = {
    # triads
    "M": "maj",  "maj": "maj",
    "m": "min",  "min": "min",
    "o": "dim",  "dim": "dim",
    "+": "aug",  "aug": "aug",
    # 7th
    "M7": "maj7", "maj7": "maj7",
    "m7": "m7",   "min7": "m7",
    "7": "7",
    "dim7": "dim7", "o7": "dim7",
    "ø": "m7b5", "ø7": "m7b5", "m7b5": "m7b5",
    "+7": "aug7", "aug7": "aug7",
    # sus
    "sus2": "sus2",
    "sus4": "sus4",
}

CHORD_VOICINGS: Dict[str, List[int]] = {
    # triads
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    # sevenths
    "maj7": [0, 4, 7, 11],
    "m7":   [0, 3, 7, 10],
    "7":    [0, 4, 7, 10],
    "dim7": [0, 3, 6, 9],
    "m7b5": [0, 3, 6, 10],
    "aug7": [0, 4, 8, 10],
}

# ============================================
# 4. シンボル解析
# ============================================
def _normalize_ctype(raw: str) -> str:
    raw_clean = raw.lstrip("/")  # 先頭に迷子の `/` があれば除去
    if raw_clean not in CHORD_ALIAS:
        raise KeyError(f"[ctype] 未対応タイプ: {raw_clean}")
    return CHORD_ALIAS[raw_clean]

def parse_symbol(symbol: str) -> Tuple[int, str]:
    """
    返り値: (root_midi_pitch, ctype)
    """
    try:
        root_token, raw_ctype = symbol.split("_", 1)
    except ValueError:
        raise ValueError(f"[parse_symbol] '_' が無い形式: {symbol}")

    # --- ルート音の解釈 (実音 or ローマ数字) -----------------
    if root_token in BASE_PITCH:
        root_pitch = BASE_PITCH[root_token]
    else:
        root_pitch = parse_degree(root_token)  # C 基準で計算

    ctype = _normalize_ctype(raw_ctype)
    if ctype not in CHORD_VOICINGS:
        raise KeyError(f"[voicing] ボイシング未定義: {ctype}")

    return root_pitch, ctype

# ============================================
# 5. 公開 API
# ============================================
def get_voicing(symbol: str, octave_shift: int = 0) -> List[int]:
    """
    chord symbol → MIDI ノート配列
      octave_shift: +1 なら 1 オクターブ上へ
    """
    root_pitch, ctype = parse_symbol(symbol)
    root_pitch += 12 * octave_shift
    return [root_pitch + iv for iv in CHORD_VOICINGS[ctype]]

# --------------------------------------------
# 6. 簡易テスト CLI
# --------------------------------------------
if __name__ == "__main__":
    import sys
    s = sys.argv[1] if len(sys.argv) > 1 else "bII#_o7"
    print(s, "->", get_voicing(s))
