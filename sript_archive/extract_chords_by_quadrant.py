import os
import pickle
import re
from collections import defaultdict

# ルートディレクトリ
LEAD_SHEET_DIR = "./EMOPIA+/functional/lead_sheet"

# Qごとのコード進行リスト
quadrant_chords = defaultdict(list)

# ディレクトリ内の .pkl ファイルを走査
for filename in os.listdir(LEAD_SHEET_DIR):
    if filename.endswith(".pkl"):
        match = re.match(r"^(Q[1-4])\W*", filename)
        if match:
            quadrant = match.group(1)
            filepath = os.path.join(LEAD_SHEET_DIR, filename)
            try:
                with open(filepath, "rb") as f:
                    _, data = pickle.load(f)
                    chords = []
                    for item in data:
                        if item["name"] == "Chord" and item["value"] not in ["None_None", None]:
                            chords.append(item["value"])
                    if chords:
                        quadrant_chords[quadrant].append(chords)
            except Exception as e:
                print(f"[!] Error reading {filename}: {e}")

# 出力
for q in sorted(quadrant_chords.keys()):
    print(f"\n{q} のコード進行（{len(quadrant_chords[q])}曲分）:")
    for i, progression in enumerate(quadrant_chords[q], 1):
        joined = " - ".join(progression)
        print(f"  {i}. {joined}")
