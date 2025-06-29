import os
import pickle
import re
from collections import defaultdict, Counter
import numpy as np
import pandas as pd

LEAD_SHEET_DIR = "./EMOPIA+/functional/lead_sheet"
quadrant_chords = defaultdict(list)

# .pklからコード進行抽出
for filename in os.listdir(LEAD_SHEET_DIR):
    if filename.endswith(".pkl"):
        match = re.match(r"^(Q[1-4])+", filename)
        if match:
            quadrant = match.group(1)
            filepath = os.path.join(LEAD_SHEET_DIR, filename)
            with open(filepath, "rb") as f:
                _, data = pickle.load(f)
                chords = [d["value"] for d in data if d["name"] == "Chord" and d["value"] not in ["None_None", None]]
                if chords:
                    quadrant_chords[quadrant].append(chords)

# マルコフ遷移行列を作成する関数
def build_markov_matrix(sequences):
    transitions = Counter()
    states = set()
    for seq in sequences:
        for i in range(len(seq) - 1):
            transitions[(seq[i], seq[i + 1])] += 1
            states.update([seq[i], seq[i + 1]])
    states = sorted(states)
    index = {s: i for i, s in enumerate(states)}
    matrix = np.zeros((len(states), len(states)), dtype=int)
    for (a, b), count in transitions.items():
        matrix[index[a], index[b]] = count
    return pd.DataFrame(matrix, index=states, columns=states)

# Qごとのマルコフ行列作成と保存
for q in quadrant_chords:
    df = build_markov_matrix(quadrant_chords[q])
    print(f"{q} のマルコフ行列:")
    print(df)
    df.to_csv(f"{q}_markov_matrix.csv")
    print(f"{q}_markov_matrix.csv を保存しました\n")
