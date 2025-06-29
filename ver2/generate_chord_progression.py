import os
import numpy as np
import random

# 設定
MATRIX_DIR = "normalized_matrices"
CHORD_LABELS = None  # 初回読み込み時に自動で決定

def load_matrix(quadrant: str, mode: str):
    global CHORD_LABELS

    filename = f"{quadrant.lower()}_{mode.lower()}.npy"
    filepath = os.path.join(MATRIX_DIR, filename)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"マルコフ遷移行列が見つかりません: {filepath}")

    # 同名CSVからラベルを取得
    label_csv = os.path.join("markov_matrices_mode", f"{quadrant}_{mode}.csv")
    with open(label_csv, encoding="utf-8") as f:
        header = f.readline()
        CHORD_LABELS = header.strip().split(",")[1:]  # 1列目（行ラベル）を除く

    return np.load(filepath)

def generate_progression(matrix: np.ndarray, num_chords: int = 16):
    assert CHORD_LABELS is not None, "コードラベルがロードされていません"
    
    idx = random.randint(0, len(CHORD_LABELS) - 1)
    progression = [CHORD_LABELS[idx]]

    for _ in range(num_chords - 1):
        probs = matrix[idx]
        idx = np.random.choice(len(CHORD_LABELS), p=probs)
        progression.append(CHORD_LABELS[idx])

    return progression

def main():
    print("🎵 感情象限（Q1〜Q4）とモード（Major / Minor）を入力してください")
    q = input("象限を指定してください（例: Q1）: ").strip().upper()
    m = input("モードを指定してください（Major / Minor）: ").strip().capitalize()

    try:
        matrix = load_matrix(q, m)
        progression = generate_progression(matrix, num_chords=16)
        print("\n🎼 生成されたコード進行:")
        print(" - " + " - ".join(progression))
    except Exception as e:
        print(f"⚠️ エラー: {e}")

if __name__ == "__main__":
    main()
