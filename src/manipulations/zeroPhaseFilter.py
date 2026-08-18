"""Normalize manipulation: applies z-score or min-max normalization to a region."""
from __future__ import annotations

import numpy as np
from scipy.signal import get_window
from src.manipulations.base import DataManipulation




def db_to_lin(db: np.ndarray) -> np.ndarray:
    return 10.0 ** (db / 20.0)

def make_mag_response(freqs_hz: np.ndarray, mags_db: np.ndarray, fs: int, n_fft: int) -> np.ndarray:
    """
    Interpolate a 0..fs/2 magnitude curve (dB) onto rFFT bins and return linear magnitude H[k].
    """
    freqs_hz = np.asarray(freqs_hz, dtype=float)
    mags_db = np.asarray(mags_db, dtype=float)

    if np.min(freqs_hz) < 0 or np.max(freqs_hz) > fs / 2 + 1e-9:
        raise ValueError(f"Curve must be within 0..{fs/2} Hz")

    f_grid = np.fft.rfftfreq(n_fft, d=1.0 / fs)
    mags_db_i = np.interp(f_grid, freqs_hz, mags_db, left=mags_db[0], right=mags_db[-1])
    Hmag = db_to_lin(mags_db_i)
    return Hmag

def ola_apply_mag_response(x: np.ndarray, Hmag: np.ndarray, params: ApplyParams) -> np.ndarray:
    """
    Apply Hmag (rFFT-bin linear magnitudes) to x using overlap-add STFT processing.
    """
    n_fft, hop = params.n_fft, params.hop
    if hop <= 0 or hop > n_fft:
        raise ValueError("hop must be in (0, n_fft].")
    if len(Hmag) != (n_fft // 2 + 1):
        raise ValueError("Hmag length must be n_fft//2 + 1.")

    x = np.asarray(x, dtype=float)
    w = get_window(params.window, n_fft, fftbins=True).astype(float)

    # pad for frame coverage
    pad = n_fft
    x_pad = np.pad(x, (pad, pad), mode="constant")
    y_pad = np.zeros_like(x_pad)
    w2_acc = np.zeros_like(x_pad)

    for start in range(0, len(x_pad) - n_fft + 1, hop):
        frame = x_pad[start : start + n_fft]
        frame_w = frame * w

        X = np.fft.rfft(frame_w)
        Y = X * Hmag  # magnitude shaping (zero-phase)
        y_frame = np.fft.irfft(Y, n=n_fft)

        y_pad[start : start + n_fft] += y_frame * w
        w2_acc[start : start + n_fft] += w * w

    eps = 1e-12
    y_pad = np.where(w2_acc > eps, y_pad / (w2_acc + eps), y_pad)

    return y_pad[pad : pad + len(x)]


def parse_text_list(text: str) -> np.ndarray:
    """
    Parse a string like "[1, 2, 3]" or "1, 2, 3" into a numpy array of floats.
    """
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    if not text:
        return np.array([], dtype=float)
    try:
        return np.array([float(x) for x in text.split(",")], dtype=float)
    except ValueError as e:
        raise ValueError(f"Invalid number in list: {e}")

class zeroPhaseFilter(DataManipulation):
    name = "Zero-Phase Filter"
    description = "Applies a zero phase frequency domain filter."
    options = {
        "Freqs": {
            "type": "text",
            "label": "Frequency Centers",
            "default": "[]",
            "placeholder": "[]",
        },
        "Mags": {
            "type": "text",
            "label": "Magnitudes Anchors",
            "default": "[]",
            "placeholder": "[]",
        }, 
        "FS": {
            "type": "int",
            "label": "FS",
            "default": 1000,
            "placeholder": 1000,
        },      
        "nfft": {
            "type": "int",
            "label": "nfft",
            "default": 2048,
            "placeholder": 2048,
        },
        "hop": {
            "type": "int",
            "label": "hop",
            "default": 512,
            "placeholder": 512,
        }                    
    }

    def apply(self, data, timestamps, channel_idx, region, option_values):



        freqs_hz = option_values.get("Freqs", "[]")
        mags_db = option_values.get("Mags", "[]")
        fs = option_values.get("FS", 1000)
        nfft = option_values.get("nfft", 1000)
        hop_ = option_values.get("hop", 1000)


        class ApplyParams:
            n_fft: int = nfft
            hop: int = hop_
            window: str = "hann"

        params = ApplyParams()

        freqs_hz = parse_text_list(freqs_hz)
        mags_db = parse_text_list(mags_db)

        Hmag = make_mag_response(freqs_hz, mags_db, fs, params.n_fft)


        result = data.copy()
        start, end = region
        mask = (timestamps >= start) & (timestamps <= end)
        segment = result[mask]
        segment = ola_apply_mag_response(segment, Hmag, params)
        if len(segment) == 0:
            return result

        result[mask] = segment

        return result
