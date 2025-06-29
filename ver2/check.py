import pandas as pd
from pathlib import Path

def check_chord_presence(chord: str):
    root = Path("markov_matrices_mode")
    for csv in root.glob("*.csv"):
        df = pd.read_csv(csv, index_col=0)
        if chord in df.index or chord in df.columns:
            print(f"✅ {chord} found in {csv.name}")

check_chord_presence("VII_sus2")
