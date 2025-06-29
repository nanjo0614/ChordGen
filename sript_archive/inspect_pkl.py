# inspect_pkl2.py
import pickle, pprint, itertools
from pathlib import Path

p = Path(r"C:\ChordGen\EMOPIA+\functional\lead_sheet\Q1_0vLPYiPN7qY_0.pkl")  # 適宜変更
with p.open("rb") as f:
    data = pickle.load(f)

print(type(data))

if isinstance(data, tuple):
    print(f"tuple length = {len(data)}")
    for idx, elem in enumerate(data[:3]):   # 先頭3つ
        print(f"\n--- element {idx} ---")
        print(f"type = {type(elem)}")
        if isinstance(elem, (list, tuple)):
            print("first 20 items:")
            pprint.pprint(list(itertools.islice(elem, 20)))
        elif isinstance(elem, dict):
            pprint.pprint(elem.keys())
        else:
            print(repr(elem))
else:
    print("Not a tuple; got", type(data))
