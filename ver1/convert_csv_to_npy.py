import argparse, numpy as np, pandas as pd
from pathlib import Path

def row_normalize(df: pd.DataFrame, eps=1e-8):
    """行を確率分布に正規化。全ゼロ行は一様分布にする"""
    arr = df.values.astype(np.float32)
    row_sums = arr.sum(axis=1, keepdims=True)
    zero_rows = (row_sums < eps).flatten()
    
    # ゼロ行 → 一様分布
    arr[zero_rows] = 1.0 / arr.shape[1]
    row_sums[zero_rows] = 1.0
    
    arr /= row_sums
    return arr, df.index.tolist()

def convert_all(csv_dir: Path, npy_dir: Path):
    npy_dir.mkdir(exist_ok=True, parents=True)
    mapping_path = npy_dir / "chord_index_map.txt"

    for csv_file in csv_dir.glob("*.csv"):
        df = pd.read_csv(csv_file, index_col=0)
        arr, chords = row_normalize(df)

        # 保存
        np.save(npy_dir / f"{csv_file.stem}.npy", arr)
        print(f"[Save] {csv_file.stem}.npy  shape={arr.shape}")

    # インデックスはどのファイルも同じ前提 → 1 回だけ保存
    with mapping_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(chords))
    print(f"[Save] chord_index_map.txt  ({len(chords)} chords)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv_dir",  required=True, help="CSV フォルダ")
    ap.add_argument("--npy_dir",  required=True, help="出力 .npy フォルダ")
    args = ap.parse_args()

    convert_all(Path(args.csv_dir), Path(args.npy_dir))
import argparse, numpy as np, pandas as pd
from pathlib import Path

def row_normalize(df: pd.DataFrame, eps=1e-8):
    """行を確率分布に正規化。全ゼロ行は一様分布にする"""
    arr = df.values.astype(np.float32)
    row_sums = arr.sum(axis=1, keepdims=True)
    zero_rows = (row_sums < eps).flatten()
    
    # ゼロ行 → 一様分布
    arr[zero_rows] = 1.0 / arr.shape[1]
    row_sums[zero_rows] = 1.0
    
    arr /= row_sums
    return arr, df.index.tolist()

def convert_all(csv_dir: Path, npy_dir: Path):
    npy_dir.mkdir(exist_ok=True, parents=True)
    mapping_path = npy_dir / "chord_index_map.txt"

    for csv_file in csv_dir.glob("*.csv"):
        df = pd.read_csv(csv_file, index_col=0)
        arr, chords = row_normalize(df)

        # 保存
        np.save(npy_dir / f"{csv_file.stem}.npy", arr)
        print(f"[Save] {csv_file.stem}.npy  shape={arr.shape}")

    # インデックスはどのファイルも同じ前提 → 1 回だけ保存
    with mapping_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(chords))
    print(f"[Save] chord_index_map.txt  ({len(chords)} chords)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv_dir",  required=True, help="CSV フォルダ")
    ap.add_argument("--npy_dir",  required=True, help="出力 .npy フォルダ")
    args = ap.parse_args()

    convert_all(Path(args.csv_dir), Path(args.npy_dir))
