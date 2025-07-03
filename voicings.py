"""
voicings.py  (2025-07-02  add_lower_octave=True 対応)
---------------------------------------------------
コードシンボルを MIDI ノート番号リストへ変換。
 * get_voicing(symbol, octave_shift=0, add_lower_octave=False)
   - add_lower_octave=True で「構成音すべて −12 半音」を重ねる。
"""

from __future__ import annotations
from typing import Dict, List, Tuple
import re

# ============================================
# 0. 基本設定
# ============================================
TONIC_PITCH = 60  # C4

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
ROMAN_RE = re.compile(
    r"^(?P<pre_acc>[#b]?)(?P<deg>I{1,3}|IV|V|VI{0,1}|VII)(?P<post_acc>[#b]?)$"
)

def parse_degree(token: str) -> int:
    m = ROMAN_RE.match(token)
    if not m:
        raise KeyError(f"[parse_degree] 不正なローマ数字表記: {token}")
    deg = m.group("deg")
    accidental_cnt = (
        (1 if m.group("pre_acc") == "#" else -1 if m.group("pre_acc") == "b" else 0) +
        (1 if m.group("post_acc") == "#" else -1 if m.group("post_acc") == "b" else 0)
    )
    offset = DEGREE_OFFSETS_MAJOR[deg] + accidental_cnt
    return (TONIC_PITCH + offset) % 128

# ============================================
# 3. コードタイプ
# ============================================
CHORD_ALIAS: Dict[str, str] = {
    "M": "maj",  "maj": "maj",     "m": "min",  "min": "min",
    "o": "dim",  "dim": "dim",     "+": "aug",  "aug": "aug",
    "M7": "maj7","maj7": "maj7",   "m7": "m7",  "min7": "m7",
    "7": "7",    "dim7": "dim7",   "o7":"dim7", "ø":"m7b5",
    "ø7":"m7b5","m7b5":"m7b5",     "+7":"aug7","aug7":"aug7",
    "sus2":"sus2","sus4":"sus4",
}
CHORD_VOICINGS: Dict[str, List[int]] = {
    "maj":[0,4,7],   "min":[0,3,7],   "dim":[0,3,6],   "aug":[0,4,8],
    "sus2":[0,2,7],  "sus4":[0,5,7],
    "maj7":[0,4,7,11],"m7":[0,3,7,10],"7":[0,4,7,10],
    "dim7":[0,3,6,9], "m7b5":[0,3,6,10],"aug7":[0,4,8,10],
}

# ============================================
# 4. シンボル解析
# ============================================
def _normalize_ctype(raw: str) -> str:
    if raw not in CHORD_ALIAS:
        raise KeyError(f"[ctype] 未対応タイプ: {raw}")
    return CHORD_ALIAS[raw]

def parse_symbol(symbol: str) -> Tuple[int, str]:
    try:
        root_token, raw_ctype = symbol.split("_", 1)
    except ValueError:
        raise ValueError(f"[parse_symbol] '_' が無い形式: {symbol}")

    if root_token in BASE_PITCH:
        root_pitch = BASE_PITCH[root_token]
    else:
        root_pitch = parse_degree(root_token)

    ctype = _normalize_ctype(raw_ctype)
    if ctype not in CHORD_VOICINGS:
        raise KeyError(f"[voicing] 未定義: {ctype}")
    return root_pitch, ctype

# ============================================
# 5. 公開 API
# ============================================
def get_voicing(symbol: str,
                octave_shift: int = 0,
                add_lower_octave: bool = False) -> List[int]:
    """
    chord symbol → MIDI ノート配列
      octave_shift: +1 なら全体を 1 オクターブ上へ
      add_lower_octave=True で「構成音すべて −12 半音」を重ねる
    """
    root_pitch, ctype = parse_symbol(symbol)
    base_notes = [root_pitch + iv + 12 * octave_shift
                  for iv in CHORD_VOICINGS[ctype]]
    if add_lower_octave:
        lower = [n - 12 for n in base_notes if n - 12 >= 0]
        base_notes = lower + base_notes
    return base_notes

# ============================================
# 6. CLI テスト
# ============================================
if __name__ == "__main__":
    import sys, pprint
    sym = sys.argv[1] if len(sys.argv) > 1 else "I_M7"
    pprint.pp(get_voicing(sym, add_lower_octave=True))
