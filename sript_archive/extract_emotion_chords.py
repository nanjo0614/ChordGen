import os
import pickle
from collections import defaultdict
from itertools import groupby

# フォルダパスを再確認（絶対パス推奨）
lead_sheet_dir = "C:/ChordGen/EMOPIA+/functional/lead_sheet"

emotion_to_progressions = defaultdict(list)
file_count = 0
valid_count = 0

for filename in os.listdir(lead_sheet_dir):
    if filename.endswith(".pkl"):
        file_count += 1
        filepath = os.path.join(lead_sheet_dir, filename)
        try:
            with open(filepath, "rb") as f:
                index_list, event_list = pickle.load(f)

            emotion = None
            for event in event_list:
                if isinstance(event, dict) and event.get("name") == "Emotion":
                    emotion = event.get("value")
                    break

            chords = [e['value'] for e in event_list if isinstance(e, dict) and e.get("name") == "Chord"]
            clean_chords = [k for k, _ in groupby(chords) if k and k != 'None_None']

            if emotion and clean_chords:
                emotion_to_progressions[emotion].append(clean_chords)
                valid_count += 1
            else:
                print(f"[INFO] Skipped (no valid chords or emotion): {filename}")

        except Exception as e:
            print(f"[ERROR] Failed to load {filename}: {e}")

# 出力確認
print(f"\nProcessed {file_count} files, found {valid_count} valid chord progressions.")

for emotion, progressions in emotion_to_progressions.items():
    print(f"\nEmotion: {emotion} ({len(progressions)} progressions)")
    for progression in progressions:
        print("  " + " - ".join(progression))
