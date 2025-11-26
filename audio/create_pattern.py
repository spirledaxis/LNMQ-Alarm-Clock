import csv

import librosa
import numpy as np

# === 1. Load MP3 ===
def create_pattern(filename):
    y, sr = librosa.load(f"ringtones/{filename}", mono=True)

    # === 2. Create spectrogram ===
    # STFT = Short-Time Fourier Transform
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))

    # === 3. Map frequency bins to Hz ===
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

    # === 4. Define frequency bands ===
    bass_range = (20, 250)
    mid_range = (250, 4000)
    treble_range = (4000, 20000)


    def band_energy(S, freqs, fmin, fmax):
        """Sum energy of S within a frequency range."""
        idx = np.where((freqs >= fmin) & (freqs < fmax))[0]
        return S[idx, :].mean(axis=0)  # mean energy per frame


    bass = band_energy(S, freqs, *bass_range)
    mid = band_energy(S, freqs, *mid_range)
    treble = band_energy(S, freqs, *treble_range)

    # === 5. Normalize 0–1 for convenience ===


    def normalize(x): return (x - np.min(x)) / (np.max(x) - np.min(x))


    bass, mid, treble = map(normalize, [bass, mid, treble])

    # === 6. Build timeline array ===
    times = librosa.frames_to_time(np.arange(len(bass)), sr=sr, hop_length=512)
    data = np.vstack([times, bass, mid, treble]).T

    # === 7. (Optional) Show first few rows ===
    for t, b, m, tr in data[:10]:
        print(f"{t:.2f}s | bass={b:.2f}, mid={m:.2f}, treble={tr:.2f}")

    # === 8. (Optional) Save as CSV ===
    with open(f"audio_bands/{filename}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "bass", "mid", "treble"])
        writer.writerows(data)
