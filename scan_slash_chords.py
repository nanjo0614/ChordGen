#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scan_slash_chords.py
--------------------
EMOPIA+ の lead-sheet pkl を走査し，
Chord イベントに '/' を含むコード記号があるかどうかを列挙するユーティリティ。

使い方:
    python scan_slash_chords.py --root "C:/ChordGen/EMOPIA+/functional/lead_sheet"
"""

import argparse
import pickle
from pathlib import Path


def iter_events(pkl_path: Path):
    """pkl ファイルを読み込み，イベント辞書のリストを yield する"""
    try:
        with pkl_path.open("rb") as f:
            data = pickle.load(f)
            # EMOPIA+ の形式: (durations:list[int], events:list[dict])
            if isinstance(data, tuple) and len(data) == 2 and isinstance(data[1], list):
                for ev in data[1]:
                    yield ev
    except Exception as e:
        print(f"[!] 解析失敗: {pkl_path} ({e})")


def scan(root: Path):
    total_files = 0
    hit_files = 0
    hit_count = 0

    for pkl in root.rglob("*.pkl"):
        total_files += 1
        hit_in_file = False
        for ev in iter_events(pkl):
            if ev.get("name") == "Chord":
                chord_name = str(ev.get("value"))
                if "/" in chord_name:
                    if not hit_in_file:
                        print(f"\n=== {pkl.relative_to(root)} ===")
                        hit_in_file = True
                        hit_files += 1
                    print("  →", chord_name)
                    hit_count += 1
        # メモリ節約のために次のファイルへ

    print("\n----- summary -----")
    print(f"scanned : {total_files} files")
    print(f"hit file : {hit_files} files (≥1 slash chord)")
    print(f"hit evts : {hit_count} chord events containing '/'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search slash chords in EMOPIA+ pickle files")
    parser.add_argument(
        "--root",
        type=str,
        required=True,
        help="Root directory of EMOPIA+/functional/lead_sheet",
    )
    args = parser.parse_args()

    target_root = Path(args.root).expanduser()
    if not target_root.exists():
        raise SystemExit(f"[Error] path not found: {target_root}")

    scan(target_root)
