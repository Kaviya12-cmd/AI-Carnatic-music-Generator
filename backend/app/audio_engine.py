"""
audio_engine.py – Studio-Quality Carnatic Violin DSP Engine
=============================================================
Architecture:
  - Additive synthesis  : 14 harmonics with natural amplitude decay curve
  - ADSR envelope       : smoothed via raised-cosine fade to avoid clicks
  - Natural vibrato     : 5.5 Hz FM with phase-accurate integration (no pitch drift)
  - Carnatic Gamaka     : note-specific oscillation (kampita) for Ri, Ga, Da, Ni
  - Portamento          : smooth frequency glide between consecutive notes
  - Convolution reverb  : lightweight FIR reverb for studio ambience
  - Normalization       : peak + RMS balancing for consistent loudness
  - Sample rate         : 44 100 Hz (CD quality)
  - Output              : in-memory WAV PCM-16 (BytesIO), compatible with main.py
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np
from scipy.io.wavfile import write as wav_write
from scipy.signal import fftconvolve

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_RATE: int = 44_100     # Hz
MAX_AMPLITUDE: float = 0.90   # peak ceiling (headroom for reverb)
_TWO_PI: float = 2.0 * math.pi

# ─────────────────────────────────────────────────────────────────────────────
# Carnatic Just-Intonation Pitch Map
# ─────────────────────────────────────────────────────────────────────────────

SWARA_RATIOS: dict[str, float] = {
    "S":  1.0,
    "R1": 16.0 / 15.0,
    "R2": 9.0  / 8.0,
    "G2": 6.0  / 5.0,
    "G3": 5.0  / 4.0,
    "M1": 4.0  / 3.0,
    "M2": 45.0 / 32.0,
    "P":  3.0  / 2.0,
    "D1": 8.0  / 5.0,
    "D2": 5.0  / 3.0,
    "N2": 9.0  / 5.0,
    "N3": 15.0 / 8.0,
}

# Swaras that receive gamaka (kampita oscillation in classical performance)
GAMAKA_SWARAS: frozenset[str] = frozenset({"R1", "R2", "G2", "G3", "D1", "D2", "N2", "N3"})

# ─────────────────────────────────────────────────────────────────────────────
# Instrument Profiles (Spectral & Envelope)
# ─────────────────────────────────────────────────────────────────────────────

INSTRUMENT_PROFILES = {
    "Violin": {
        # Softer spectrum (faster harmonic roll-off)
        "harmonics": np.array([1.00, 0.40, 0.20, 0.10, 0.05, 0.02, 0.01, 0.01]),
        "adsr": {"attack": 75.0, "decay": 150.0, "sustain": 0.65, "release": 250.0},
        "vibrato_depth": 0.008, # Slightly shallower
        "vibrato_rate": 5.2,
    },
    "Flute": {
        "harmonics": np.array([1.00, 0.02, 0.25, 0.01, 0.10, 0.00, 0.05, 0.00]),
        "adsr": {"attack": 120.0, "decay": 200.0, "sustain": 0.80, "release": 300.0},
        "vibrato_depth": 0.006,
        "vibrato_rate": 4.8,
        "breath_noise": 0.02, # Reduced noise
    },
    "Voice": {
        "harmonics": np.array([1.00, 0.60, 0.25, 0.12, 0.06, 0.03, 0.01, 0.01]),
        "adsr": {"attack": 100.0, "decay": 180.0, "sustain": 0.75, "release": 350.0},
        "vibrato_depth": 0.010,
        "vibrato_rate": 5.8,
    },
    "Modern Synth": {
        # Fusion Synth: Stronger 2nd/4th harmonics (saw-like) with high bite
        "harmonics": np.array([1.00, 0.82, 0.65, 0.45, 0.32, 0.22, 0.15, 0.10]),
        "adsr": {"attack": 25.0, "decay": 200.0, "sustain": 0.60, "release": 400.0},
        "vibrato_depth": 0.015, # Wider space-age vibrato
        "vibrato_rate": 4.5,
    }
}

# Normalize all harmonic arrays
for p in INSTRUMENT_PROFILES.values():
    p["harmonics"] /= p["harmonics"].sum()

# ─────────────────────────────────────────────────────────────────────────────
# Data transfer object (keeps main.py interface stable)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Note:
    """A single synthesiser note."""
    freq: float                     # fundamental frequency in Hz (0 = rest)
    duration: float                 # note duration in seconds
    swara_type: Optional[str] = ""  # e.g. "R2", "G3" – used to enable gamaka
    is_last: bool = False           # suppresses release artefact on final note


# ─────────────────────────────────────────────────────────────────────────────
# Module-level DSP helpers
# ─────────────────────────────────────────────────────────────────────────────

def _raised_cosine(n_samples: int) -> np.ndarray:
    """Raised-cosine (Hann) fade curve for artefact-free crossfades."""
    t = np.linspace(0.0, 1.0, n_samples, endpoint=False)
    return 0.5 - 0.5 * np.cos(_TWO_PI * t)


def _adsr_envelope(
    n_samples: int,
    sr: int,
    attack_ms: float  = 45.0,
    decay_ms: float   = 100.0,
    sustain_level: float = 0.72,
    release_ms: float = 170.0,
) -> np.ndarray:
    """
    Smooth ADSR envelope using raised-cosine attack/release segments.
    Using raised-cosine (rather than linear) ramps eliminates transient clicks.
    """
    a_n = int(sr * attack_ms  / 1000.0)
    d_n = int(sr * decay_ms   / 1000.0)
    r_n = int(sr * release_ms / 1000.0)

    # Clamp so segments always fit
    total_fixed = a_n + d_n + r_n
    if total_fixed >= n_samples:
        scale = n_samples / (total_fixed + 1)
        a_n = max(1, int(a_n * scale))
        d_n = max(1, int(d_n * scale))
        r_n = max(1, int(r_n * scale))

    s_n = n_samples - (a_n + d_n + r_n)

    attack  = _raised_cosine(a_n)                                   # 0 → 1
    decay   = sustain_level + (1.0 - sustain_level) * (            # 1 → S
                  np.cos(np.linspace(0, math.pi, d_n)) * 0.5 + 0.5)
    sustain = np.full(max(s_n, 0), sustain_level)
    release = sustain_level * (                                     # S → 0
                  np.cos(np.linspace(0, math.pi, r_n)) * 0.5 + 0.5)

    return np.concatenate([attack, decay, sustain, release])[:n_samples]


def _vibrato_phase(
    n_samples: int,
    freq: float,
    sr: int,
    rate_hz: float  = 5.5,
    depth_ratio: float = 0.010,   # ±1 % of fundamental
    onset_delay_s: float = 0.06,  # vibrato kicks in after ~60 ms
) -> np.ndarray:
    """
    Phase-accurate FM vibrato.
    Integrating the instantaneous frequency (instead of just modulating phase)
    guarantees zero pitch drift over the note duration.
    Returns: phase array (radians) for use in np.sin(phase).
    """
    t = np.arange(n_samples) / sr
    depth_hz = freq * depth_ratio

    # Smooth onset envelope (vibrato starts gradually)
    onset_n = int(onset_delay_s * sr)
    onset_env = np.ones(n_samples)
    if onset_n > 0 and onset_n < n_samples:
        fade = np.linspace(0.0, 1.0, onset_n)
        onset_env[:onset_n] = fade

    # Instantaneous frequency: f(t) = freq + depth * onset(t) * sin(2π·rate·t)
    f_inst = freq + depth_hz * onset_env * np.sin(_TWO_PI * rate_hz * t)

    # Phase = 2π · ∫f(t)dt  (cumulative trapezoid integration)
    dt = 1.0 / sr
    phase = _TWO_PI * np.cumsum(f_inst) * dt
    return phase


def _gamaka_phase(
    n_samples: int,
    freq: float,
    sr: int,
    kampita_rate_hz: float = 6.0,
    kampita_depth_ratio: float = 0.018,  # ±1.8 % – slightly wider for Ri/Ga
) -> np.ndarray:
    """
    Carnatic kampita gamaka: a periodic oscillation around the swara,
    analogous to vibrato but more pronounced and beginning immediately
    (no delay), as in classical violin gamakas.
    """
    t = np.arange(n_samples) / sr
    depth_hz = freq * kampita_depth_ratio
    f_inst = freq + depth_hz * np.sin(_TWO_PI * kampita_rate_hz * t)
    dt = 1.0 / sr
    phase = _TWO_PI * np.cumsum(f_inst) * dt
    return phase


def _portamento_phase(
    n_samples: int,
    freq_start: float,
    freq_end: float,
    sr: int,
    glide_ratio: float = 0.12,   # first 12 % of note is the glide
) -> np.ndarray:
    """
    Smooth portamento (meend) at the beginning of a note.
    Uses a logarithmic frequency glide (musically linear in pitch).
    """
    glide_n = max(2, int(n_samples * glide_ratio))
    steady_n = n_samples - glide_n

    log_start = math.log(max(freq_start, 1.0))
    log_end   = math.log(max(freq_end,   1.0))

    glide_freq  = np.exp(np.linspace(log_start, log_end, glide_n))
    steady_freq = np.full(steady_n, freq_end)

    f_inst = np.concatenate([glide_freq, steady_freq])
    dt = 1.0 / sr
    phase = _TWO_PI * np.cumsum(f_inst) * dt
    return phase


def _synthesize_tone(
    phase: np.ndarray,
    instrument: str = "Violin",
) -> np.ndarray:
    """
    Additive synthesis using instrument-specific harmonic weights.
    """
    profile = INSTRUMENT_PROFILES.get(instrument, INSTRUMENT_PROFILES["Violin"])
    weights = profile["harmonics"]
    
    wave = np.zeros_like(phase)
    for k, w in enumerate(weights):
        wave += w * np.sin((k + 1) * phase)
        
    # Add breath noise for Flute
    if instrument == "Flute":
        n_samples = len(phase)
        noise = (np.random.rand(n_samples) * 2 - 1) * profile.get("breath_noise", 0)
        # Low-pass the noise to make it "breathier"
        noise = np.convolve(noise, np.ones(10)/10, mode='same')
        wave += noise
        
    return wave


def _build_reverb_ir(sr: int, room_ms: float = 400.0, decay: float = 0.55) -> np.ndarray:
    """
    Synthetic FIR reverb impulse response
    (exponentially-decaying white noise – Schroeder model approximation).
    This avoids shipping a large IR file while still providing convincing
    studio ambience.
    """
    rng = np.random.default_rng(seed=42)   # fixed seed = deterministic timbre
    n = int(sr * room_ms / 1000.0)
    ir = rng.standard_normal(n)
    t = np.arange(n) / sr
    env = np.exp(-decay * t * (1000.0 / room_ms))
    ir = ir * env
    ir[0] = 1.0   # direct (dry) component
    ir /= np.max(np.abs(ir))
    return ir.astype(np.float32)


# Pre-build reverb IR once at module load (avoids per-call overhead)
_REVERB_IR: np.ndarray = _build_reverb_ir(SAMPLE_RATE)


# Based on membrane acoustics: left (bass) and right (treble) heads
# Strokes: Tha, Dhi, Thom, Nam, Chapu, Gumki
# Reference: South Indian percussion DSP literature + Karplus-Strong variants
# ─────────────────────────────────────────────────────────────────────────────

def _stroke_nam(sa_freq: float, n: int, t: np.ndarray, sr: int) -> np.ndarray:
    """
    Nam — right-head resonant tone, tuned precisely to Sa.
    Models the overtone series of the black spot (karanai) on the right head.
    Rich in harmonics, long resonance.
    """
    f = sa_freq
    # Overtone series with specific JI-like ratios (Bessel-function inspired)
    amps  = [1.00, 0.55, 0.28, 0.14, 0.07, 0.03]
    freqs = [f,  f*2.0, f*3.0, f*4.76, f*6.0, f*8.0]   # Non-integer overtones for realism
    wave  = sum(a * np.sin(_TWO_PI * fi * t) for a, fi in zip(amps, freqs))
    # Long sustain with slight pitch sag (membrane relaxation)
    pitch_sag = np.exp(-3.0 * t)
    env = np.exp(-5.0 * t) * (1.0 + 0.15 * pitch_sag)
    return (wave * env).astype(np.float32)

def _stroke_tha(sa_freq: float, n: int, t: np.ndarray, sr: int) -> np.ndarray:
    """
    Tha — right-head open treble stroke (sharp, bright, dry).
    Short high-frequency burst with fast click transient.
    """
    rng = np.random.default_rng(seed=7)
    noise = rng.standard_normal(n)
    # Bandpass: keep 800 Hz – 6 kHz (treble membrane content)
    kernel = np.zeros(51)
    for k in range(1, 12):
        kernel += np.sin(_TWO_PI * k * 2000 / sr * np.arange(51))
    kernel /= (np.linalg.norm(kernel) + 1e-9)
    noise_filtered = np.convolve(noise, kernel, mode='same')
    # Add a few resonant partials tuned to upper harmonics of Sa
    res = (0.6 * np.sin(_TWO_PI * sa_freq * 3 * t) +
           0.3 * np.sin(_TWO_PI * sa_freq * 5 * t))
    wave = noise_filtered + res
    env = np.exp(-35.0 * t)
    return (wave * env).astype(np.float32)

def _stroke_dhi(sa_freq: float, n: int, t: np.ndarray, sr: int) -> np.ndarray:
    """
    Dhi — right-head finger-muted tone.
    Combination of Tha and Nam with slightly longer resonance.
    """
    tha = _stroke_tha(sa_freq, n, t, sr)
    nam = _stroke_nam(sa_freq, n, t, sr)
    # Dhi = 60% Nam clarity + 40% Tha brightness
    return (0.60 * nam + 0.40 * tha).astype(np.float32)

def _stroke_thom(sa_freq: float, n: int, t: np.ndarray, sr: int) -> np.ndarray:
    """
    Thom — left bass-head open stroke (deep, booming, resonant).
    Models the pitch-bending characteristic of the bass membrane.
    """
    f_bass = sa_freq * 0.45  # ~1 octave below Sa (left head tuning)
    # Pitch-bend on attack: left head starts slightly higher and sags
    pitch_bend = f_bass * (1.0 + 0.25 * np.exp(-30.0 * t))
    f_inst = pitch_bend
    phase = _TWO_PI * np.cumsum(f_inst) / sr
    wave = np.sin(phase) + 0.35 * np.sin(2 * phase) + 0.15 * np.sin(3 * phase)
    # Add impact transient (noise click)
    rng = np.random.default_rng(seed=11)
    click = rng.standard_normal(n) * np.exp(-80 * t) * 0.4
    wave += click
    env = np.exp(-6.0 * t)
    return (wave * env).astype(np.float32)

def _stroke_chapu(sa_freq: float, n: int, t: np.ndarray, sr: int) -> np.ndarray:
    """
    Chapu (Chappu) — soft left-hand muted bass hit.
    Shorter, drier than Thom — the 'ghost' bass note.
    """
    wave = _stroke_thom(sa_freq, n, t, sr)
    # Apply stronger decay (muted)
    mute_env = np.exp(-20.0 * t)
    return (wave * mute_env).astype(np.float32)

def _stroke_gumki(sa_freq: float, n: int, t: np.ndarray, sr: int) -> np.ndarray:
    """
    Gumki — left-hand oscillating bass tone (pitch modulated).
    Creates the wah/modulation effect by oscillating the membrane tension.
    """
    f_bass = sa_freq * 0.45
    # Gumki wobble: 4 Hz LFO pitch modulation starting wide, narrowing
    wobble_depth = 0.12 * np.exp(-5 * t)
    wobble = 1.0 + wobble_depth * np.sin(_TWO_PI * 4.0 * t)
    f_inst = f_bass * wobble
    phase = _TWO_PI * np.cumsum(f_inst) / sr
    wave = np.sin(phase) + 0.2 * np.sin(2 * phase)
    env = np.exp(-7.0 * t)
    return (wave * env).astype(np.float32)

# ── Stroke dispatcher ─────────────────────────────────────────────────────────

_STROKE_FN = {
    "Nam":   _stroke_nam,
    "Tha":   _stroke_tha,
    "Dhi":   _stroke_dhi,
    "Thom":  _stroke_thom,
    "Chapu": _stroke_chapu,
    "Gumki": _stroke_gumki,
}

def _synthesize_mridangam_stroke(stroke_type: str, sa_freq: float, duration: float, sr: int) -> np.ndarray:
    """Dispatcher: generates one mridangam stroke by name."""
    n = max(1, int(sr * duration))
    t = np.arange(n, dtype=np.float32) / sr
    fn = _STROKE_FN.get(stroke_type)
    if fn is None:
        return np.zeros(n, dtype=np.float32)
    raw = fn(sa_freq, n, t, sr)
    # Safety clip
    return np.clip(raw, -2.0, 2.0)

# ── Tala pattern definitions ──────────────────────────────────────────────────
# Each sub-list is one beat. Strokes are placed at fractional positions within
# the beat (0.0, 0.5 = half-beat subdivisions).

_TALA_PATTERNS = {
    # Adi Tala: 8 counts | Laghu(4) + Drutam + Drutam
    # Authentic 16-syllable avartanam: Ta Ka Di Mi | Ta Ka Ju No | Ta Di Ki Na | Tom
    "Adi": [
        # Position, Stroke
        (0.00, "Tha"),   (0.50, "Chapu"),
        (1.00, "Nam"),   (1.50, "Chapu"),
        (2.00, "Dhi"),   (2.50, "Gumki"),
        (3.00, "Nam"),   (3.50, "Tha"),
        (4.00, "Tha"),   (4.25, "Chapu"), (4.50, "Nam"), (4.75, "Chapu"),
        (5.00, "Thom"),  (5.50, "Gumki"),
        (6.00, "Tha"),   (6.25, "Chapu"), (6.50, "Nam"), (6.75, "Tha"),
        (7.00, "Thom"),  (7.50, "Gumki"),
    ],
    # Rupaka Tala: 6 beats (Drutam + Laghu)
    "Rupaka": [
        (0.00, "Thom"), (0.50, "Gumki"),
        (1.00, "Tha"),  (1.50, "Nam"),
        (2.00, "Dhi"),  (2.50, "Thom"),
        (3.00, "Tha"),  (3.50, "Chapu"),
        (4.00, "Nam"),  (4.50, "Gumki"),
        (5.00, "Thom"), (5.50, "Tha"),
    ],
    # Triputa Tala: 7 beats
    "Triputa": [
        (0.00, "Tha"),  (0.50, "Nam"),
        (1.00, "Dhi"),  (1.50, "Chapu"),
        (2.00, "Thom"), (2.50, "Gumki"),
        (3.00, "Tha"),  (3.50, "Nam"),  (3.75, "Chapu"),
        (4.00, "Thom"),
        (5.00, "Tha"),  (5.50, "Nam"),
        (6.00, "Thom"), (6.50, "Gumki"),
    ],
}

def _build_rhythm_layer(num_beats: int, beat_dur: float, talam: str, sa_freq: float, sr: int) -> np.ndarray:
    """
    Builds a complete Mridangam rhythm layer using authentic stroke patterns.
    The palette is positioned at sub-beat precision for natural feel.
    """
    total_n = int(sr * num_beats * beat_dur)
    full_rhythm = np.zeros(total_n, dtype=np.float32)

    tala_events = _TALA_PATTERNS.get(talam, _TALA_PATTERNS["Adi"])
    tala_cycle  = max(e[0] for e in tala_events) + 1.0  # number of beats per cycle

    for i_beat in range(num_beats):
        beat_start_n = int(i_beat * beat_dur * sr)
        # Map this beat into the repeating tala cycle
        cycle_pos = i_beat % tala_cycle

        for (event_beat, stroke_name) in tala_events:
            # Find events that belong to current beat position
            if int(event_beat) == int(cycle_pos) or (
                abs(event_beat - (i_beat % tala_cycle)) < 0.01
            ):
                # Sub-beat offset within the beat
                sub_offset_s = (event_beat - int(event_beat)) * beat_dur
                start_n = beat_start_n + int(sub_offset_s * sr)

                stroke_dur = min(beat_dur * 0.95, 0.6)  # cap at 600 ms
                stroke = _synthesize_mridangam_stroke(stroke_name, sa_freq, stroke_dur, sr)

                end_n = min(start_n + len(stroke), total_n)
                if end_n > start_n:
                    full_rhythm[start_n:end_n] += stroke[:end_n - start_n] * 0.40

    return full_rhythm


def _apply_reverb(signal: np.ndarray, dry: float = 0.72, wet: float = 0.28) -> np.ndarray:
    """
    Convolution reverb with dry/wet mix.
    FFT-based overlap-add (fftconvolve) is efficient even for long signals.
    """
    wet_signal = fftconvolve(signal, _REVERB_IR, mode="full")[:len(signal)]
    return dry * signal + wet * wet_signal


def _apply_soft_filter(signal: np.ndarray) -> np.ndarray:
    """3-tap moving average — gentle high-cut for a warmer, pleasant tone."""
    return np.convolve(signal, np.array([0.25, 0.50, 0.25]), mode='same')


def _apply_pingpong_delay(signal: np.ndarray, sr: int, delay_ms: int = 350, feedback: float = 0.40, mix: float = 0.25) -> np.ndarray:
    """Stereo Ping-Pong Delay implementation for modern fusion ambiance."""
    delay_samples = int(sr * delay_ms / 1000.0)
    out = signal.copy()
    
    # We only process mono-to-mono for now to keep ByteIO interface stable,
    # but the recursive feedback adds 'modern' rhythmic texture
    feedback_signal = np.zeros_like(signal)
    
    for i in range(delay_samples, len(signal)):
        # Recursive feedback formula: f(t) = s(t-d) + feed * f(t-d)
        feedback_signal[i] = signal[i - delay_samples] + feedback * feedback_signal[i - delay_samples]
        
    return (1.0 - mix) * signal + mix * feedback_signal


def _normalize(signal: np.ndarray, target_peak: float = 0.85) -> np.ndarray:
    """Peak normalise then apply gentle RMS correction for pleasant loudness."""
    peak = np.max(np.abs(signal))
    if peak < 1e-9:
        return signal
    signal = signal * (target_peak / peak)

    # Gentle RMS levelling (Lower target for 'softer' sound)
    rms = np.sqrt(np.mean(signal ** 2))
    target_rms = target_peak * 0.18   # Softer perceptual ceiling
    if rms > 1e-9:
        gain = min(target_rms / rms, 1.0)
        signal = signal * gain

    return np.clip(signal, -1.0, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Main Synthesiser Class
# ─────────────────────────────────────────────────────────────────────────────

class CarnaticSynthesizer:
    """
    Multi-instrument Carnatic synthesiser supporting Violin, Flute, and Voice.
    """

    def __init__(
        self,
        sample_rate: int  = SAMPLE_RATE,
        instrument: str   = "Violin",
        reverb: bool      = False,
        portamento: bool  = True,
        gamaka: bool      = True,
        use_rhythm: bool  = True,  # Added Miruthangam toggle
        talam: str        = "Adi",
        sa_freq: float    = 130.81
    ):
        self.sr          = sample_rate
        self.instrument  = instrument if instrument in INSTRUMENT_PROFILES else "Violin"
        self.use_reverb  = reverb
        self.use_porta   = portamento
        self.use_gamaka  = gamaka
        self.use_rhythm  = use_rhythm
        self.talam       = talam
        self.sa_freq     = sa_freq
        self.profile     = INSTRUMENT_PROFILES[self.instrument]

    # ── Public API ────────────────────────────────────────────────────────────

    def synthesize_melody(self, notes: List[Note]) -> io.BytesIO:
        """
        Render a sequence of Note objects to an in-memory WAV (PCM-16).
        Returns a BytesIO positioned at offset 0, ready to be read or
        sent directly as an HTTP response.
        """
        if not notes:
            return self._silence_wav(duration_s=1.0)

        segments: List[np.ndarray] = []

        for i, note in enumerate(notes):
            prev_freq = notes[i - 1].freq if i > 0 else note.freq

            if note.freq <= 0.0:
                seg = self._rest(note.duration)
            else:
                seg = self._render_note(note, prev_freq)

            segments.append(seg)

        full_wave = np.concatenate(segments)
        
        # ── Add Rhythmic Layer (Miruthangam) ──────────────────────────────
        if self.use_rhythm:
            beat_dur = notes[0].duration if notes else 0.5
            rhythm = _build_rhythm_layer(len(notes), beat_dur, self.talam, self.sa_freq, self.sr)
            # Ensure same length, then mix
            min_len = min(len(full_wave), len(rhythm))
            full_wave[:min_len] = full_wave[:min_len] * 0.9 + rhythm[:min_len]

        # 1. Apply modern Ping-Pong Delay/Echo (Fusion hallmark)
        full_wave = _apply_pingpong_delay(full_wave, self.sr)

        # 2. Subtle high-cut filter for a warmer, pleasant tone
        full_wave = _apply_soft_filter(full_wave)

        # 3. Add touch of reverb for space (Modern wide hall)
        if self.use_reverb:
            full_wave = _apply_reverb(full_wave, dry=0.90, wet=0.10)

        # 4. Final peak + RMS balancing
        full_wave = _normalize(full_wave)

        # Convert to 16-bit PCM
        pcm16 = (full_wave * 32_767).astype(np.int16)
        buf = io.BytesIO()
        wav_write(buf, self.sr, pcm16)
        buf.seek(0)
        return buf

    # ── Internal per-note rendering ───────────────────────────────────────────

    def _render_note(self, note: Note, prev_freq: float) -> np.ndarray:
        n_samples = max(1, int(self.sr * note.duration))
        freq       = note.freq
        swara      = (note.swara_type or "").replace("'", "").replace("_", "")

        # ── 1. Phase trajectory ───────────────────────────────────────────
        has_gamaka = self.use_gamaka and swara in GAMAKA_SWARAS

        vibrato_depth = self.profile["vibrato_depth"]
        vibrato_rate  = self.profile["vibrato_rate"]

        if has_gamaka:
            # Gamaka overrides vibrato
            phase = _gamaka_phase(n_samples, freq, self.sr)
        else:
            # Standard vibrato
            phase = _vibrato_phase(n_samples, freq, self.sr, rate_hz=vibrato_rate, depth_ratio=vibrato_depth)

        # ── 2. Portamento (meend): blend glide at start of each note ─────
        if self.use_porta and prev_freq > 0.0 and prev_freq != freq:
            glide_phase = _portamento_phase(n_samples, prev_freq, freq, self.sr)
            blend_n = max(2, int(n_samples * 0.12))
            alpha = np.linspace(0.0, 1.0, blend_n)
            phase[:blend_n] = (1.0 - alpha) * glide_phase[:blend_n] + alpha * phase[:blend_n]

        # ── 3. Additive synthesis ─────────────────────────────────────────
        wave = _synthesize_tone(phase, instrument=self.instrument)

        # ── 4. ADSR envelope ──────────────────────────────────────────────
        adsr = self.profile["adsr"]
        env = _adsr_envelope(
            n_samples, 
            self.sr, 
            attack_ms=adsr["attack"], 
            decay_ms=adsr["decay"], 
            sustain_level=adsr["sustain"], 
            release_ms=adsr["release"]
        )
        wave *= env

        return wave

    def _rest(self, duration_s: float) -> np.ndarray:
        """Silent segment."""
        return np.zeros(max(1, int(self.sr * duration_s)))

    def _silence_wav(self, duration_s: float = 1.0) -> io.BytesIO:
        """Empty WAV for edge cases."""
        pcm = np.zeros(int(self.sr * duration_s), dtype=np.int16)
        buf = io.BytesIO()
        wav_write(buf, self.sr, pcm)
        buf.seek(0)
        return buf
