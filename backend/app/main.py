from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
import io

from .auth import router as auth_router, get_current_user
from .music_theory import RAGAM_DB, TALAM_DB, get_freq
from .audio_engine import ViolinSynthesizer, Note

app = FastAPI(title="Carnatic AI Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

class GenerationRequest(BaseModel):
    lyrics: str
    ragam: str
    talam: str
    gamaka_style: str  # Kampitam, Jaru, Nokku, None
    instrument: Optional[str] = "Violin" # Violin, Voice
    pitch: Optional[float] = 261.63 # Default C4

@app.get("/ragams")
def get_ragams():
    return list(RAGAM_DB.keys())

@app.get("/talams")
def get_talams():
    return list(TALAM_DB.keys())

@app.post("/generate")
def generate_song(req: GenerationRequest, user: dict = Depends(get_current_user)):
    if req.ragam not in RAGAM_DB:
        raise HTTPException(status_code=404, detail="Ragam not found")
    
    ragam_data = RAGAM_DB[req.ragam]
    # Simple syllabification: split by spaces and hyphens
    syllables = req.lyrics.replace("-", " ").split()
    
    # 1. Generate Melody Sequence
    # Strategy: Linear walk through Arohanam then Avarohanam, repeating if necessary
    scale = ragam_data["arohanam"] + ragam_data["avarohanam"][1:-1] # Avoid repeating S' and S
    
    melody_swaras = []
    for i, _ in enumerate(syllables):
        swara = scale[i % len(scale)]
        melody_swaras.append(swara)

    # 2. Apply Talam for Rhythm (Durations)
    if req.talam not in TALAM_DB:
        talam_pattern = [1] * 8 # Default
    else:
        talam_pattern = TALAM_DB[req.talam]
        
    # Map swaras to talam beats. 
    # If patterns run out, repeat.
    notes = []
    notation_display = []
    
    base_beat_duration = 0.5 # seconds
    
    for i, (syl, swara) in enumerate(zip(syllables, melody_swaras)):
        beat_idx = i % len(talam_pattern)
        is_strong = talam_pattern[beat_idx] == 1
        
        # Simple rhythm: Strong beats = 1 sec, Weak = 0.5 sec? 
        # Or standard duration, usually Talam defines structure, not individual note duration.
        # Let's map 1 syllable = 1 beat for simplicity.
        duration = base_beat_duration
        
        freq = get_freq(swara, base_freq=req.pitch)
        
        # Apply random gamaka if style is selected, else specific
        # We apply user selection to random notes to simulate "style"
        # Voice is cleaner without heavy gamaka usually in beginner lessons, but let's allow it.
        applied_gamaka = None
        if req.gamaka_style != "None":
            if random.random() > 0.6: # 40% chance of gamaka on any note
                applied_gamaka = req.gamaka_style
        
        notes.append(Note(freq, duration, applied_gamaka))
        notation_display.append({
            "lyric": syl,
            "swara": swara,
            "duration": duration,
            "gamaka": applied_gamaka
        })
        
    # Generate Audio
    if req.instrument == "Voice":
        from .audio_engine import FormantSynthesizer
        synth = FormantSynthesizer()
        wav_io = synth.generate_melody(notes, lyrics=syllables)
    else:
        synth = ViolinSynthesizer()
        wav_io = synth.generate_melody(notes)
    
    import base64
    audio_b64 = base64.b64encode(wav_io.read()).decode('utf-8')
    
    return {
        "notation": notation_display,
        "audio_base64": audio_b64
    }

from fastapi import UploadFile, File, Form

@app.post("/train_voice")
async def train_voice(
    pitch: float = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    # Simulate processing time
    import time
    time.sleep(2) # Fake "training" time
    
    return {
        "status": "success",
        "message": f"Voice profile calibrated for Scale {pitch} Hz.",
        "profile_id": "profile_678"
    }

@app.post("/generate_with_audio")
async def generate_with_audio(
    lyrics: str = Form(...),
    ragam: str = Form(...),
    talam: str = Form(...),
    gamaka_style: str = Form(...),
    instrument: str = Form("Violin"),
    pitch: float = Form(261.63),
    file: UploadFile = File(None),
    user: dict = Depends(get_current_user)
):
    req = GenerationRequest(lyrics=lyrics, ragam=ragam, talam=talam, gamaka_style=gamaka_style, instrument=instrument, pitch=pitch)
    
    # ... (Copy logic from previous generate_song)
    if req.ragam not in RAGAM_DB:
        raise HTTPException(status_code=404, detail="Ragam not found")
    
    ragam_data = RAGAM_DB[req.ragam]
    syllables = req.lyrics.replace("-", " ").split()
    scale = ragam_data["arohanam"] + ragam_data["avarohanam"][1:-1]
    
    # Helper to find valid swara in Ragam
    def get_ragam_swara(base_char, ragam_scale):
        # ragam_scale is boolean combined list.
        # Find R1/R2/R3 in the list if base_char is 'R'
        for s in ragam_scale:
            if s.startswith(base_char):
                return s
        # Fallback if not found (e.g. Varja ragam missing a note) - return closest or Pa/Sa
        if base_char == 'P': return 'P'
        return 'S'

    melody_swaras = []
    
    # Pre-compute unique swaras in this ragam for lookup
    unique_swaras = set(scale)
    
    # Swara mapping for input detection
    input_map = {
        "sa": "S", "s": "S",
        "ri": "R", "r": "R",
        "ga": "G", "g": "G",
        "ma": "M", "m": "M",
        "pa": "P", "p": "P",
        "da": "D", "da": "D", "dha": "D", "d": "D",
        "ni": "N", "n": "N"
    }

    scale_index = 0
    for i, syl in enumerate(syllables):
        # Clean syllable to check if it's a swara
        clean = syl.lower().strip().replace("aa", "a").replace("ee", "i")
        
        # Check if user typed a specific swara
        base_swara = None
        for k, v in input_map.items():
            if clean == k:
                base_swara = v
                break
        
        if base_swara:
            # User wants a specific note (e.g. "Ri")
            # We must find WHICH Ri is allowed in this Ragam.
            # We search the unique_swaras set.
            found = False
            for valid_s in unique_swaras:
                if valid_s.startswith(base_swara): # matches R1, R2...
                    melody_swaras.append(valid_s)
                    found = True
                    break
            if not found:
                 # Ragam doesn't have this note (e.g. Mohanam has no Ma)
                 # Fallback: Just play Sa or keep previous?
                 # Let's play next in scale to keep flow
                 swara = scale[scale_index % len(scale)]
                 melody_swaras.append(swara)
                 scale_index += 1
        else:
            # Random text -> Generate melody based on scale walk
            swara = scale[scale_index % len(scale)]
            melody_swaras.append(swara)
            scale_index += 1

    if req.talam not in TALAM_DB:
        talam_pattern = [1] * 8
    else:
        talam_pattern = TALAM_DB[req.talam]
        
    notes = []
    notation_display = []
    base_beat_duration = 0.5
    
    scale_index = 0
    # For random wolk, we prefer a linear pitch space to move up/down
    # We'll use Arohanam repeatedly or construct a 2-octave map if possible.
    # For simplicity, let's use the combined scale we already have but treat it as valid notes
    # Valid notes for random access:
    valid_notes = sorted(list(set(scale)), key=lambda x: get_freq(x, base_freq=req.pitch))
    # Reset index to middle
    current_note_idx = 0 
    
    for i, syl in enumerate(syllables):
        # Clean syllable to check if it's a swara
        clean = syl.lower().strip().replace("aa", "a").replace("ee", "i")
        
        # Check if user typed a specific swara
        input_map = {
            "sa": "S", "s": "S",
            "ri": "R", "r": "R", "re": "R",
            "ga": "G", "g": "G",
            "ma": "M", "m": "M",
            "pa": "P", "p": "P",
            "da": "D", "da": "D", "dha": "D", "d": "D",
            "ni": "N", "n": "N"
        }
        
        base_swara = None
        for k, v in input_map.items():
            if clean == k:
                base_swara = v
                break
        
        swara = ""
        duration = 0.5 # Default short
        
        # 1. Determine Rhythm (Duration) input heuristics
        # If syllable has double vowels or is long, make it a Long beat (1.0s) or aligned to Talam
        # Simple heuristic: 'aa', 'ee', 'oo', 'ii' or Length > 3
        if "aa" in syl.lower() or "ee" in syl.lower() or "oo" in syl.lower() or "ii" in syl.lower() or len(syl) > 4:
            duration = 1.0
        
        # 2. Determine Pitch (Swara)
        if base_swara:
            # Explicit Swara Mode
            unique_swaras = set(scale)
            found = False
            for valid_s in unique_swaras:
                if valid_s.startswith(base_swara): 
                    swara = valid_s
                    found = True
                    break
            if not found:
                 swara = valid_notes[current_note_idx % len(valid_notes)]
            
            # Update current index to this explicit note to smooth transitions
            try:
                current_note_idx = valid_notes.index(swara)
            except:
                pass
                
        else:
            # Generative "Song" Mode (Random Walk)
            # biased random walk: stay(20%), +/-1(50%), +/-2(30%)
            step = random.choices([0, 1, -1, 2, -2], weights=[20, 30, 30, 10, 10])[0]
            current_note_idx += step
            
            # Bounds check (bounce)
            if current_note_idx < 0:
                current_note_idx = 1
            if current_note_idx >= len(valid_notes):
                current_note_idx = len(valid_notes) - 2
                
            swara = valid_notes[current_note_idx]

        # Apply Talam override? 
        # Talam dictates the grid. Duration should fit the grid.
        # But for "Singing", duration is lyrical. 
        # Let's keep lyrical duration but display Talam Beat Index.
        
        beat_idx = i % len(talam_pattern)
        is_strong = talam_pattern[beat_idx] == 1
        
        freq = get_freq(swara, base_freq=req.pitch)
        
        applied_gamaka = None
        if req.gamaka_style != "None":
            # Higher chance of gamaka on long notes
            chance = 0.8 if duration > 0.6 else 0.3
            if random.random() < chance: 
                applied_gamaka = req.gamaka_style
        
        notes.append(Note(freq, duration, applied_gamaka))
        notation_display.append({
            "lyric": syl,
            "swara": swara,
            "duration": duration,
            "gamaka": applied_gamaka
        })
        
    # Generate Audio
    if req.instrument == "Voice":
        from .audio_engine import FormantSynthesizer
        synth = FormantSynthesizer()
        wav_io = synth.generate_melody(notes, lyrics=syllables)
    elif req.instrument == "MyVoice" and file:
        from .audio_engine import SamplerSynthesizer
        # Save temp file
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        
        try:
            # Assume user sings at ~C4 (261Hz)
            synth = SamplerSynthesizer(tmp_path, base_freq=261.63)
            wav_io = synth.generate_melody(notes)
        finally:
            os.remove(tmp_path)
    else:
        synth = ViolinSynthesizer()
        wav_io = synth.generate_melody(notes)
    
    import base64
    audio_b64 = base64.b64encode(wav_io.read()).decode('utf-8')
    
    return {
        "notation": notation_display,
        "audio_base64": audio_b64
    }
