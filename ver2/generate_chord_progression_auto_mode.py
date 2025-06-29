import os
import numpy as np
import random

# 設定
MATRIX_DIR = "normalized_matrices"
MARKOV_CSV_DIR = "markov_matrices_mode"
CHORD_LABELS = None  # 初回読み込み時に自動で決定

def load_mode_probabilities(quadrant: str):
    """ 指定された象限における Major / Minor の遷移行列の存在割合からモード選択確率を決定 """
    major_path = os.path.join(MATRIX_DIR, f"{quadrant.lower()}_major.npy")
    minor_path = os.path.join(MATRIX_DIR, f"{quadrant.lower()}_minor.npy")

    has_major = os.path.exists(major_path)
    has_minor = os.path.exists(minor_path)

    if has_major and has_minor:
        # 両方ある場合は CSV の行数から使用比率を推定
        major_csv = os.path.join(MARKOV_CSV_DIR, f"{quadrant}_major.csv")
        minor_csv = os.path.join(MARKOV_CSV_DIR, f"{quadrant}_minor.csv")

        with open(major_csv, encoding="utf-8") as f:
            major_lines = sum(1 for _ in f) - 1  # ヘッダー除く
        with open(minor_csv, encoding="utf-8") as f:
            minor_lines = sum(1 for _ in f) - 1

        total = major_lines + minor_lines
        prob_major = major_lines / total
        return prob_major, 1 - prob_major
    elif has_major:
        return 1.0, 0.0
    elif has_minor:
        return 0.0, 1.0
    else:
        raise FileNotFoundError(f"{quadrant} の Major / Minor 行列が見つかりません。")

def load_matrix(quadrant: str, mode: str):
    global CHORD_LABELS

    filename = f"{quadrant.lower()}_{mode.lower()}.npy"
    filepath = os.path.join(MATRIX_DIR, filename)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"マルコフ遷移行列が見つかりません: {filepath}")

    # 同名CSVからラベルを取得
    label_csv = os.path.join(MARKOV_CSV_DIR, f"{quadrant}_{mode}.csv")
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
    print("🎵 感情象限（Q1〜Q4）を入力してください。モードは確率で自動選択されます。")
    q = input("象限を指定してください（例: Q2）: ").strip().upper()

    try:
        prob_major, prob_minor = load_mode_probabilities(q)
        mode = random.choices(["Major", "Minor"], weights=[prob_major, prob_minor])[0]
        matrix = load_matrix(q, mode)
        progression = generate_progression(matrix, num_chords=16)

        print(f"\n🎼 自動選択モード: {mode}")
        print(" - " + " - ".join(progression))
    except Exception as e:
        print(f"⚠️ エラー: {e}")

if __name__ == "__main__":
    main()
