import random
import numpy as np
import tkinter as tk
from tkinter import ttk, scrolledtext
import pygame.midi
import time

# BPM固定（100）で1小節の長さ（4/4拍子）
BPM = 100
BEAT_DURATION = 60 / BPM
MEASURE_DURATION = BEAT_DURATION * 4

# モードごとのコードリスト
MODES = {
    1: ['F', 'G', 'C', 'Am', 'Dm'],
    2: ['C', 'F', 'G', 'Em', 'Am'],
    3: ['G', 'C', 'Dm', 'F'],
    4: ['Dm', 'G', 'Am', 'C'],
    5: ['Am', 'Dm', 'Em', 'F', 'C'],
    6: ['Em', 'Am', 'Bdim', 'F'],
    7: ['Bdim', 'Em', 'F', 'G', 'Am']
}

# モードごとのマルコフ遷移行列
MARKOV_MATRICES = {
    1: np.array([
        [0.1, 0.3, 0.3, 0.2, 0.1],
        [0.2, 0.1, 0.4, 0.2, 0.1],
        [0.4, 0.2, 0.1, 0.2, 0.1],
        [0.2, 0.2, 0.2, 0.2, 0.2],
        [0.3, 0.1, 0.3, 0.2, 0.1]
    ]),
    2: np.array([
        [0.2, 0.2, 0.3, 0.2, 0.1],
        [0.2, 0.2, 0.2, 0.2, 0.2],
        [0.3, 0.2, 0.2, 0.2, 0.1],
        [0.1, 0.3, 0.3, 0.2, 0.1],
        [0.2, 0.2, 0.2, 0.2, 0.2]
    ]),
    3: np.array([
        [0.3, 0.3, 0.2, 0.2],
        [0.3, 0.1, 0.4, 0.2],
        [0.2, 0.2, 0.2, 0.4],
        [0.4, 0.2, 0.2, 0.2]
    ]),
    4: np.array([
        [0.2, 0.4, 0.2, 0.2],
        [0.3, 0.1, 0.3, 0.3],
        [0.2, 0.3, 0.2, 0.3],
        [0.3, 0.2, 0.3, 0.2]
    ]),
    5: np.array([
        [0.2, 0.3, 0.2, 0.2, 0.1],
        [0.3, 0.1, 0.3, 0.2, 0.1],
        [0.2, 0.3, 0.1, 0.2, 0.2],
        [0.2, 0.2, 0.2, 0.1, 0.3],
        [0.3, 0.2, 0.2, 0.2, 0.1]
    ]),
    6: np.array([
        [0.3, 0.2, 0.2, 0.3],
        [0.2, 0.2, 0.3, 0.3],
        [0.2, 0.3, 0.2, 0.3],
        [0.3, 0.2, 0.2, 0.3]
    ]),
    7: np.array([
        [0.2, 0.3, 0.2, 0.2, 0.1],
        [0.2, 0.2, 0.2, 0.2, 0.2],
        [0.3, 0.2, 0.2, 0.2, 0.1],
        [0.2, 0.3, 0.2, 0.2, 0.1],
        [0.1, 0.2, 0.3, 0.2, 0.2]
    ])
}

CHORD_ROOTS = {
    'C': 60, 'Dm': 62, 'Em': 64, 'F': 65,
    'G': 67, 'Am': 69, 'Bdim': 71
}

progression = []

def valence_to_mode(valence):
    return max(1, min(7, 7 - round(valence * 6)))

def generate_markov_progression(valence, length=4):
    mode = valence_to_mode(valence)
    chords = MODES[mode]
    matrix = MARKOV_MATRICES[mode]
    idx = random.randint(0, len(chords) - 1)
    prog = []
    for _ in range(length):
        chord = chords[idx]
        root = CHORD_ROOTS[chord]
        midi_notes = [root, root + 4, root + 7]
        prog.append((f"mode{mode}", chord, midi_notes))
        idx = np.random.choice(len(chords), p=matrix[idx])
    return prog

def play_midi_chords(chord_list, duration=MEASURE_DURATION):
    pygame.midi.init()
    player = pygame.midi.Output(0)
    player.set_instrument(0)
    for _, _, notes in chord_list:
        for note in notes:
            player.note_on(note, 100)
        time.sleep(duration)
        for note in notes:
            player.note_off(note, 100)
    player.close()
    pygame.midi.quit()

def run_gui():
    def on_generate():
        global progression
        val = valence_slider.get() / 100.0
        progression = generate_markov_progression(val)
        output_text.delete('1.0', tk.END)
        for mode, chord, notes in progression:
            output_text.insert(tk.END, f'{mode:<7} {chord:<4} {notes}\n')
        val_label.config(text=f"{int(valence_slider.get())}")

    def on_play():
        if progression:
            play_midi_chords(progression)

    def on_slider_change(event):
        val_label.config(text=f"{int(valence_slider.get())}")

    root = tk.Tk()
    root.title("マルコフコード進行生成")

    tk.Label(root, text="Valence").pack()
    valence_slider = ttk.Scale(root, from_=0, to=100, orient='horizontal')
    valence_slider.set(50)
    valence_slider.pack(fill='x', padx=10)

    val_label = tk.Label(root, text="50", font=("Arial", 10))
    val_label.pack()
    valence_slider.bind("<Motion>", on_slider_change)
    valence_slider.bind("<ButtonRelease-1>", on_slider_change)

    ttk.Button(root, text="コード進行を生成", command=on_generate).pack(pady=5)
    ttk.Button(root, text="再生", command=on_play).pack(pady=5)

    output_text = scrolledtext.ScrolledText(root, width=50, height=10, font=('Courier', 10))
    output_text.pack(padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    run_gui()
