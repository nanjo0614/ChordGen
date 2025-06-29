import pandas as pd
import numpy as np
import random

# マルコフ行列のCSVファイルを読み込む関数
def load_markov_matrix(q_label):
    filename = f"{q_label}_markov_matrix.csv"
    df = pd.read_csv(filename, index_col=0)
    return df

# マルコフ連鎖でコード進行を生成する関数
def generate_chord_progression(markov_matrix, length=16):
    chords = list(markov_matrix.columns)
    current = random.choice(chords)  # ランダムに開始コードを選択
    progression = [current]

    for _ in range(length - 1):
        probs = markov_matrix.loc[current].values
        if probs.sum() == 0:
            current = random.choice(chords)
        else:
            current = np.random.choice(chords, p=probs / probs.sum())
        progression.append(current)

    return progression

# メイン処理
def main():
    print("感情象限を指定してください（Q1, Q2, Q3, Q4）:")
    q_input = input(">> ").strip().upper()
    if q_input not in {"Q1", "Q2", "Q3", "Q4"}:
        print("不正な入力です。Q1〜Q4のいずれかを入力してください。")
        return

    markov_matrix = load_markov_matrix(q_input)
    progression = generate_chord_progression(markov_matrix, length=16)
    print(f"\n{q_input} のマルコフ連鎖に基づくコード進行:")
    print(" - ".join(progression))

if __name__ == "__main__":
    main()
