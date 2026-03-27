"""
main.py – FastAPI Dispatcher for Carnatic AI
============================================
Updates:
1. 3-mode lyrics/notation parser (Western, Swara, Syllable).
2. Keyboard note mapping with Just Intonation.
3. Rounded frequency and keyboard note in display notation.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import base64
import math

from .auth import router as auth_router, get_current_user
from .music_theory import (
    RAGAM_DB, TALAM_DB, PITCH_FREQ_MAP, DEFAULT_BASE_FREQ, 
    get_freq, ragam_validation, pitch_validation
)
from .audio_engine import CarnaticSynthesizer, Note
from .ragam_generator import get_sarali_varisai, generate_full_ascent_descent, generate_ragam_melody

app = FastAPI(title="Carnatic AI Generator - DSP Optimized")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

class GenerationRequest(BaseModel):
    ragam: str
    pitch_name: str
    tempo: int
    lyrics: Optional[str] = ""
    talam: Optional[str] = "Adi"
    sarali_index: Optional[int] = 1 # 1-4
    use_sarali: Optional[bool] = True
    instrument: Optional[str] = "Violin"

def parse_lyrics_to_swaras(text: str, ragam_name: str) -> List[tuple]:
    """
    Fix 1: 3-mode parser
    Mode 1: Western notes (C D E F G A B C') → convert to ragam swaras
    Mode 2: Swara names (S R G M P D N S') → map to ragam-correct swaras  
    Mode 3: Any syllables (Tamil/solkattu) → assign scale-order notes
    Also: strip | and || bar lines before parsing
    """
    # Strip | and || bar lines
    text = text.replace("||", "").replace("|", "")
    tokens = text.split("-") if "-" in text else text.split()
    
    ragam_info = RAGAM_DB.get(ragam_name)
    if not ragam_info:
        return []

    swara_types = ragam_info["swara_types"]
    
    # Indices for mapping
    WESTERN_MAP = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
    CARNATIC_MAP = {"S": 0, "R": 1, "G": 2, "M": 3, "P": 4, "D": 5, "N": 6}
    
    results = []
    current_octave = 0
    prev_idx = -1

    for token in tokens:
        clean = token.replace("'", "").replace("_", "").upper()
        
        # Mode 2 & 1: Check for known note names (Carnatic priority)
        base_idx = -1
        if clean in CARNATIC_MAP:
            base_idx = CARNATIC_MAP[clean]
        elif clean in WESTERN_MAP:
            base_idx = WESTERN_MAP[clean]
            
        if base_idx != -1:
            # Stateful Octave Tracking (Fix: S R G M P D N S -> S')
            if prev_idx != -1:
                # If we wrap around transition (N -> S or D -> S), increment octave
                if base_idx < prev_idx and (prev_idx - base_idx) >= 4:
                    current_octave += 1
                # If we drop down (S -> N), decrement octave
                elif base_idx > prev_idx and (base_idx - prev_idx) >= 4:
                    current_octave -= 1
            
            # Reset/Override octave if explicit markers are present
            marks = token.count("'") - token.count("_")
            # If explicit marks exist, we could reset current_octave, but 
            # for now we combine them to handle S' vs S
            final_octave = current_octave + marks
            
            # Map index to ragam swara type
            mapped = swara_types[base_idx % len(swara_types)]
            
            # Apply octave markers to mapped swara
            if final_octave > 0:
                mapped = mapped.replace("'", "").replace("_", "") + ("'" * final_octave)
            elif final_octave < 0:
                mapped = mapped.replace("'", "").replace("_", "") + ("_" * abs(final_octave))
                
            results.append((mapped, token))
            prev_idx = base_idx
        else:
            # Mode 3: Syllables -> Scale order
            idx = len(results)
            octave_shift = idx // len(swara_types)
            base_pos = idx % len(swara_types)
            mapped = swara_types[base_pos]
            if octave_shift > 0:
                mapped += "'" * octave_shift
            results.append((mapped, token))
            prev_idx = -1 # Reset state on unknown syllable
            
    return results

def swara_to_keyboard(swara: str, freq: float, sa_freq: float, pitch_name: str) -> str:
    """
    Fix 3: Map swara to keyboard note using Just Intonation and semitone rounding.
    """
    CHROMATIC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    try:
        # sa_idx = CHROMATIC.findIndex matching pitch_name exactly
        sa_idx = CHROMATIC.index(pitch_name.upper())
    except ValueError:
        sa_idx = 0
        
    # Semitone calculation: round(12 * log2(freq / sa_freq))
    semitones = round(12 * math.log2(freq / sa_freq))
    
    keyboard_idx = (sa_idx + semitones) % 12
    return CHROMATIC[keyboard_idx]

@app.get("/ragams")
def get_ragams():
    """Returns list of all available ragam names."""
    return list(RAGAM_DB.keys())

@app.get("/talams")
def get_talams():
    """Returns list of all available talam names."""
    return list(TALAM_DB.keys())

@app.get("/ragam_info/{ragam_name}")
def get_ragam_info(ragam_name: str):
    """Returns detailed info for a specific ragam."""
    if ragam_name not in RAGAM_DB:
        raise HTTPException(status_code=404, detail="Ragam not found")
    return RAGAM_DB[ragam_name]

@app.post("/generate")
def generate_music(req: GenerationRequest, user: dict = Depends(get_current_user)):
    """
    Main entry point for generating authentic Carnatic music.
    Supports Sarali Varisai patterns and 3-mode syllable/notation parsing.
    """
    if req.ragam not in RAGAM_DB:
        raise HTTPException(status_code=404, detail=f"Ragam {req.ragam} not found.")
    
    base_freq = PITCH_FREQ_MAP.get(req.pitch_name.upper(), DEFAULT_BASE_FREQ)
    beat_dur = 60.0 / max(req.tempo, 1)

    # 1. Determine Swara Sequence
    if req.use_sarali:
        swara_sequence = get_sarali_varisai(req.sarali_index, req.ragam)
        syllables = [s.replace("'", "").replace("_", "") for s in swara_sequence]
    elif req.lyrics:
        # Fix 1: Multi-mode parser
        parsed = parse_lyrics_to_swaras(req.lyrics, req.ragam)
        swara_sequence = [p[0] for p in parsed]
        syllables = [p[1] for p in parsed]
    else:
        # Default to full ascent/descent if no lyrics
        swara_sequence = generate_full_ascent_descent(req.ragam)
        syllables = [s.replace("'", "").replace("_", "") for s in swara_sequence]

    # 2. Validation
    if not ragam_validation(swara_sequence, req.ragam):
        raise HTTPException(status_code=400, detail="Melody failed ragam validation.")

    # 3. DSP Synthesis
    notes = []
    display_notation = []
    n_total = len(swara_sequence)

    for i, s in enumerate(swara_sequence):
        freq = get_freq(s, base_freq, req.ragam)
        lyric = syllables[i] if i < len(syllables) else ""

        # Extract clean swara type (strip octave markers) for gamaka decision
        clean_swara = s.replace("'", "").replace("_", "")

        notes.append(Note(
            freq=freq,
            duration=beat_dur,
            swara_type=clean_swara,
            is_last=(i == n_total - 1),
        ))
        display_notation.append({
            "swara": s,
            "keyboard_note": swara_to_keyboard(s, freq, base_freq, req.pitch_name),
            "lyric": lyric,
            "freq_hz": round(freq, 2),
            "duration": round(beat_dur, 2)
        })

    synth = CarnaticSynthesizer(
        instrument=req.instrument, 
        talam=req.talam or "Adi", 
        sa_freq=base_freq,
        use_rhythm=False
    )
    wav_stream = synth.synthesize_melody(notes)

    return {
        "ragam": req.ragam,
        "pitch_name": req.pitch_name,
        "pitch_hz": base_freq,
        "tempo": req.tempo,
        "instrument": req.instrument,
        "notation": display_notation,
        "audio_base64": base64.b64encode(wav_stream.read()).decode("utf-8")
    }

@app.get("/validate_system")
def validate_system():
    """Self-check for pitch and frequency accuracy (Octave 3 low register)."""
    c_ok = pitch_validation("C", 130.81)
    s_freq = get_freq("S", 130.81, "Mayamalavagowla")
    tara_s_freq = get_freq("S'", 130.81, "Mayamalavagowla")

    return {
        "status": "healthy",
        "pitch_calibration": "C3 @ 130.81 Hz" if c_ok else "ERR",
        "math_check": {
            "S":             s_freq,
            "Tara_S_Target": 261.62,
            "Tara_S_Actual": tara_s_freq,
            "Tara_S_Valid":  abs(tara_s_freq - 261.62) < 0.05
        }
    }