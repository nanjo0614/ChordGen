import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

INPUT_DIR = "markov_matrices_mode"  # 相対 or 絶対パスに変更可
OUTPUT_DIR = "normalized_matrices"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def normalize_and_save(file_path):
    df = pd.read_csv(file_path, index_col=0)
    matrix = df.to_numpy(dtype=np.float64)

    # Laplace 平滑化（+1）
    matrix += 1

    # 正規化（行ごとに合計が1）
    row_sums = matrix.sum(axis=1, keepdims=True)
    normalized = matrix / row_sums

    # 保存ファイル名
    filename = os.path.basename(file_path)
    npy_name = os.path.splitext(filename)[0] + ".npy"
    np.save(os.path.join(OUTPUT_DIR, npy_name), normalized)

    print(f"✅ Saved: {npy_name}")

    return filename, df.columns, normalized

# --- メイン処理 ---
matrices = []
for file in os.listdir(INPUT_DIR):
    if file.endswith(".csv"):
        path = os.path.join(INPUT_DIR, file)
        name, labels, matrix = normalize_and_save(path)
        matrices.append((name, labels, matrix))

# --- 可視化（最初の1枚だけ） ---
if matrices:
    name, labels, matrix = matrices[0]
    plt.figure(figsize=(12, 10))
    sns.heatmap(matrix, xticklabels=labels, yticklabels=labels, cmap="viridis", annot=False)
    plt.title(f"Markov Matrix Heatmap: {name}")
    plt.tight_layout()
    plt.show()
