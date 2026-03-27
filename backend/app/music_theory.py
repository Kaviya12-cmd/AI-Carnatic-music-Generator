"""
music_theory.py – Carnatic Music Theory & Frequency Engine (REBUILT)
==================================================================
- Implements strict Just Intonation ratios for Carnatic swaras.
- Comprehensive database of 15 essential Ragams.
- Octave-safe frequency calculation with full floating precision.
- Mandatory debug printing for validation.
"""

from typing import List, Dict, Any

# ── Part 1: Universal Swara Ratio Table ─────────────────────────────
# Precise Just Intonation ratios according to Carnatic standards.
# These are GLOBAL and NOT redefined per ragam.
SWARA_RATIOS: Dict[str, float] = {
    "S":  1.0,          # Adhara Shadjam (1)
    "R1": 16.0/15.0,    # Shuddha Rishabham (1.0667)
    "R2": 9.0/8.0,      # Chatusruti Rishabham (1.125)
    "G2": 6.0/5.0,      # Sadharana Gandharam (1.2)
    "G3": 5.0/4.0,      # Antara Gandharam (1.25)
    "M1": 4.0/3.0,      # Shuddha Madhyamam (1.3333)
    "M2": 45.0/32.0,    # Prati Madhyamam (1.40625)
    "P":  3.0/2.0,      # Panchamam (1.5)
    "D1": 8.0/5.0,      # Shuddha Dhaivatam (1.6)
    "D2": 5.0/3.0,      # Chatusruti Dhaivatam (1.6667)
    "N2": 9.0/5.0,      # Kaishiki Nishadam (1.8)
    "N3": 15.0/8.0,     # Kakali Nishadam (1.875)
}

# ── Part 2: Ragam Database (15 Ragams) ────────────────────────────────
# Each ragam defines its scale (Arohanam/Avarohanam) and Swara TYPES.
RAGAM_DB: Dict[str, Dict[str, Any]] = {
    "Mayamalavagowla": {
        "swara_types": ["S", "R1", "G3", "M1", "P", "D1", "N3"],
        "arohanam": ["S", "R1", "G3", "M1", "P", "D1", "N3", "S'"],
        "avarohanam": ["S'", "N3", "D1", "P", "M1", "G3", "R1", "S"],
        "jiva": ["G3", "D1"],
        "nyasa": ["S", "P"],
        "prayogams": [["S", "R1", "G3"], ["G3", "M1", "P"], ["P", "D1", "N3", "S'"]]
    },
    "Shankarabharanam": {
        "swara_types": ["S", "R2", "G3", "M1", "P", "D2", "N3"],
        "arohanam": ["S", "R2", "G3", "M1", "P", "D2", "N3", "S'"],
        "avarohanam": ["S'", "N3", "D2", "P", "M1", "G3", "R2", "S"],
        "jiva": ["G3", "N3", "R2"],
        "nyasa": ["P", "S"],
        "prayogams": [["S", "R2", "G3"], ["G3", "M1", "P"], ["P", "D2", "N3", "S'"]]
    },
    "Kalyani": {
        "swara_types": ["S", "R2", "G3", "M2", "P", "D2", "N3"],
        "arohanam": ["S", "R2", "G3", "M2", "P", "D2", "N3", "S'"],
        "avarohanam": ["S'", "N3", "D2", "P", "M2", "G3", "R2", "S"],
        "jiva": ["G3", "M2", "N3"],
        "nyasa": ["G3", "P", "N3"],
        "prayogams": [["S", "R2", "G3", "M2"], ["G3", "M2", "P"], ["P", "D2", "N3", "S'"]]
    },
    "Mohanam": {
        "swara_types": ["S", "R2", "G3", "P", "D2"],
        "arohanam": ["S", "R2", "G3", "P", "D2", "S'"],
        "avarohanam": ["S'", "D2", "P", "G3", "R2", "S"],
        "jiva": ["G3", "D2"],
        "nyasa": ["P", "S"],
        "prayogams": [["S", "R2", "G3"], ["G3", "P", "D2"], ["D2", "P", "G3"]]
    },
    "Hamsadhwani": {
        "swara_types": ["S", "R2", "G3", "P", "N3"],
        "arohanam": ["S", "R2", "G3", "P", "N3", "S'"],
        "avarohanam": ["S'", "N3", "P", "G3", "R2", "S"],
        "jiva": ["R2", "P"],
        "nyasa": ["S", "P", "G3"],
        "prayogams": [["S", "R2", "G3"], ["G3", "P", "N3"], ["P", "R2", "S"]]
    },
    "Bhairavi": {
        "swara_types": ["S", "R2", "G2", "M1", "P", "D1", "N2"],
        "arohanam": ["S", "R2", "G2", "M1", "P", "D1", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D1", "P", "M1", "G2", "R2", "S"],
        "jiva": ["G2", "M1", "P", "N2"],
        "nyasa": ["P", "S"],
        "prayogams": [["S", "G2", "R2", "G2"], ["M1", "P", "D1", "P"]]
    },
    "Kharaharapriya": {
        "swara_types": ["S", "R2", "G2", "M1", "P", "D2", "N2"],
        "arohanam": ["S", "R2", "G2", "M1", "P", "D2", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D2", "P", "M1", "G2", "R2", "S"],
        "jiva": ["R2", "G2", "D2"],
        "nyasa": ["P", "R2"],
        "prayogams": [["S", "R2", "G2", "M1"], ["P", "D2", "N2", "S'"]]
    },
    "Todi": {
        "swara_types": ["S", "R1", "G2", "M1", "P", "D1", "N2"],
        "arohanam": ["S", "R1", "G2", "M1", "P", "D1", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D1", "P", "M1", "G2", "R1", "S"],
        "jiva": ["G2", "D1"],
        "nyasa": ["M1", "G2"],
        "prayogams": [["G2", "R1", "S"], ["M1", "G2", "R1", "S"]]
    },
    "Charukesi": {
        "swara_types": ["S", "R2", "G3", "M1", "P", "D1", "N2"],
        "arohanam": ["S", "R2", "G3", "M1", "P", "D1", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D1", "P", "M1", "G3", "R2", "S"],
        "jiva": ["M1", "D1"],
        "nyasa": ["P", "S"],
        "prayogams": [["G3", "M1", "P"], ["P", "D1", "N2", "S'"]]
    },
    "Abheri": {
        "swara_types": ["S", "G2", "M1", "P", "D2", "N2"],
        "arohanam": ["S", "G2", "M1", "P", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D2", "P", "M1", "G2", "S"],
        "jiva": ["G2", "M1", "N2"],
        "nyasa": ["P", "S"],
        "prayogams": [["S", "G2", "M1", "P"], ["P", "N2", "S'"], ["N2", "D2", "P", "M1"]]
    },
    "Saveri": {
        "swara_types": ["S", "R1", "M1", "P", "D1", "N3", "G3"],
        "arohanam": ["S", "R1", "M1", "P", "D1", "S'"],
        "avarohanam": ["S'", "N3", "D1", "P", "M1", "G3", "R1", "S"],
        "jiva": ["R1", "D1"],
        "nyasa": ["P", "S"],
        "prayogams": [["S", "R1", "M1", "P"], ["P", "D1", "S'"]]
    },
    "Kambhoji": {
        "swara_types": ["S", "R2", "G3", "M1", "P", "D2", "N2"],
        "arohanam": ["S", "R2", "G3", "M1", "P", "D2", "S'"],
        "avarohanam": ["S'", "N2", "D2", "P", "M1", "G3", "R2", "S"],
        "jiva": ["G3", "M1", "D2"],
        "nyasa": ["P", "S"],
        "prayogams": [["S", "R2", "G3", "M1", "P"], ["D2", "S'", "N2", "D2", "P"]]
    },
    "Hindolam": {
        "swara_types": ["S", "G2", "M1", "D1", "N2"],
        "arohanam": ["S", "G2", "M1", "D1", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D1", "M1", "G2", "S"],
        "jiva": ["M1", "D1"],
        "nyasa": ["S", "M1"],
        "prayogams": [["S", "G2", "M1"], ["M1", "D1", "N2", "S'"]]
    },
    "Harikambhoji": {
        "swara_types": ["S", "R2", "G3", "M1", "P", "D2", "N2"],
        "arohanam": ["S", "R2", "G3", "M1", "P", "D2", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D2", "P", "M1", "G3", "R2", "S"],
        "jiva": ["M1", "P"],
        "nyasa": ["S", "P"],
        "prayogams": [["G3", "M1", "P"], ["P", "D2", "N2", "S'"]]
    },
    "Sahana": {
        "swara_types": ["S", "R2", "G3", "M1", "P", "D2", "N2"],
        "arohanam": ["S", "R2", "G3", "M1", "P", "M1", "D2", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D2", "P", "M1", "G3", "M1", "R2", "S"],
        "jiva": ["R2", "G3", "M1"],
        "nyasa": ["R2", "P"],
        "prayogams": [["S", "R2", "G3", "M1"], ["P", "M1", "D2", "N2", "S'"]],
        "vakra": True
    },
}

# ── Pitch Frequency Map — Octave 3 (Low Register) ────────────────────────────
# Standard equal-temperament: fₙ = 440 × 2^((n−69)/12), Octave 3
PITCH_FREQ_MAP: Dict[str, float] = {
    "C":  130.81,  # C3
    "C#": 138.59,  # C#3
    "D":  146.83,  # D3
    "D#": 155.56,  # D#3
    "E":  164.81,  # E3
    "F":  174.61,  # F3
    "F#": 185.00,  # F#3
    "G":  196.00,  # G3
    "G#": 207.65,  # G#3
    "A":  220.00,  # A3
    "A#": 233.08,  # A#3
    "B":  246.94,  # B3
}
DEFAULT_BASE_FREQ: float = 130.81   # C3 — low register Sa

TALAM_DB: Dict[str, List[int]] = {
    "Adi":      [4, 2, 2],
    "Rupaka":   [2, 4],
    "Triputa":  [3, 2, 2],
}

# ── Part 3: Correct Frequency Formula Implementation ───────────────────

def get_freq(swara: str, sa_frequency: float, ragam_name: str = "Unknown") -> float:
    """
    Step 1: Get Sa base frequency from selected pitch.
    Step 2: Get swara ratio from universal table.
    Step 3: Apply octave multiplier LAST.
    Correct formula:
        frequency = sa_frequency * ratio
        frequency = frequency * octave_multiplier
    """
    # 1. Determine Octave from notation
    octave_multiplier = 1.0
    octave_name = "Madhya"
    
    if swara.endswith("'"):
        octave_multiplier = 2.0
        octave_name = "Tara"
    elif swara.endswith("_"):
        octave_multiplier = 0.5
        octave_name = "Mandara"

    # 2. Extract swara type and handle Tara Sa rule
    clean_swara = swara.replace("'", "").replace("_", "")
    
    # Tara Sa Bug Fix: Must be exactly 2 * Sa
    if clean_swara == "S" and octave_name == "Tara":
        ratio = 1.0 # Base ratio for S
    else:
        # Get ratio from universal table
        ratio = SWARA_RATIOS.get(clean_swara, 1.0)

    # 3. Calculate following the exact rule: Apply octave multiplier LAST
    freq_at_madhya = sa_frequency * ratio
    final_frequency = freq_at_madhya * octave_multiplier

    # 4. Debug Print (Part 6)
    print("--- Note Debug ---")
    print(f"Ragam: {ragam_name}")
    print(f"Swara: {swara}")
    print(f"Swara Type: {clean_swara}")
    print(f"Octave: {octave_name}")
    print(f"Final Frequency: {final_frequency}")
    print("------------------")

    return final_frequency

def ragam_validation(swara_sequence: List[str], ragam_name: str) -> bool:
    """
    Validates that a sequence only uses swaras within the ragam's allowed TYPES.
    Mohanam must not produce Ma or Ni.
    """
    if ragam_name not in RAGAM_DB:
        return False
    
    allowed_types = RAGAM_DB[ragam_name]["swara_types"]
    
    for s in swara_sequence:
        clean_s = s.replace("'", "").replace("_", "")
        if clean_s not in allowed_types:
            # Special case for S' (Tara Sa) which is allowed if S is allowed
            if clean_s == "S":
                continue
            return False
    return True

def pitch_validation(pitch_name: str, expected_hz: float) -> bool:
    """Validates that a pitch name maps to its exact frequency."""
    actual_hz = PITCH_FREQ_MAP.get(pitch_name.upper())
    return actual_hz == expected_hz
