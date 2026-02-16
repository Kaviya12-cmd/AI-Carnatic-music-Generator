from typing import List, Dict, Tuple

# Base frequency for Shadjam (Middle C equivalent)
BASE_FREQ = 261.63  # C4

# Semitone ratios (Just Intonation preferred for Carnatic, but Equal Temperament is easier for synthesis)
# We'll use Equal Temperament for simplicity in this V0, or simple multipliers.
# Frequency = Base * (2 ** (semitone / 12))

SWARA_MAP = {
    "S": 0,
    "R1": 1, "R2": 2, "R3": 3,
    "G1": 2, "G2": 3, "G3": 4,  # Overlaps handled by Ragam definition
    "M1": 5, "M2": 6,
    "P": 7,
    "D1": 8, "D2": 9, "D3": 10,
    "N1": 9, "N2": 10, "N3": 11
}

# 20 Ragams - Arohanam (Ascending) and Avarohanam (Descending)
# Defined as list of Swaras
RAGAM_DB = {
    "Mayamalavagowla": {
        "arohanam": ["S", "R1", "G3", "M1", "P", "D1", "N3", "S'"],
        "avarohanam": ["S'", "N3", "D1", "P", "M1", "G3", "R1", "S"]
    },
    "Shankarabharanam": {
        "arohanam": ["S", "R2", "G3", "M1", "P", "D2", "N3", "S'"],
        "avarohanam": ["S'", "N3", "D2", "P", "M1", "G3", "R2", "S"]
    },
    "Mohanam": {
        "arohanam": ["S", "R2", "G3", "P", "D2", "S'"],
        "avarohanam": ["S'", "D2", "P", "G3", "R2", "S"]
    },
    "Hamsadhwani": {
        "arohanam": ["S", "R2", "G3", "P", "N3", "S'"],
        "avarohanam": ["S'", "N3", "P", "G3", "R2", "S"]
    },
    "Kalyani": {
        "arohanam": ["S", "R2", "G3", "M2", "P", "D2", "N3", "S'"],
        "avarohanam": ["S'", "N3", "D2", "P", "M2", "G3", "R2", "S"]
    },
    "Kharaharapriya": {
        "arohanam": ["S", "R2", "G2", "M1", "P", "D2", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D2", "P", "M1", "G2", "R2", "S"]
    },
    "Hindolam": {
        "arohanam": ["S", "G2", "M1", "D1", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D1", "M1", "G2", "S"]
    },
    "Abhogi": {
        "arohanam": ["S", "R2", "G2", "M1", "D2", "S'"],
        "avarohanam": ["S'", "D2", "M1", "G2", "R2", "S"]
    },
    "Malayamarutam": {
        "arohanam": ["S", "R1", "G3", "P", "D2", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D2", "P", "G3", "R1", "S"]
    },
    "Arabhi": {
        "arohanam": ["S", "R2", "M1", "P", "D2", "S'"],
        "avarohanam": ["S'", "N3", "D2", "P", "M1", "G3", "R2", "S"]
    },
    "Bilahari": {
        "arohanam": ["S", "R2", "G3", "P", "D2", "S'"],
        "avarohanam": ["S'", "N3", "D2", "P", "M1", "G3", "R2", "S"]
    },
    "Madhyamavati": {
        "arohanam": ["S", "R2", "M1", "P", "N2", "S'"],
        "avarohanam": ["S'", "N2", "P", "M1", "R2", "S"]
    },
    "Todi": {
        "arohanam": ["S", "R1", "G2", "M1", "P", "D1", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D1", "P", "M1", "G2", "R1", "S"]
    },
    "Bhairavi": {
        "arohanam": ["S", "R2", "G2", "M1", "P", "D2", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D1", "P", "M1", "G2", "R2", "S"]
    },
    "Anandabhairavi": {
        "arohanam": ["S", "G2", "R2", "G2", "M1", "P", "D2", "P", "S'"],
        "avarohanam": ["S'", "N2", "D2", "P", "M1", "G2", "R2", "S"]
    },
    "Sri": {
        "arohanam": ["S", "R2", "M1", "P", "N2", "S'"],
        "avarohanam": ["S'", "N2", "P", "M1", "R2", "G2", "R2", "S"]
    },
    "Sahana": {
        "arohanam": ["S", "R2", "G3", "M1", "P", "M1", "D2", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D2", "P", "M1", "G3", "M1", "R2", "S"]
    },
    "Kapi": {
        "arohanam": ["S", "R2", "M1", "P", "N3", "S'"],
        "avarohanam": ["S'", "N2", "D2", "N2", "P", "M1", "G2", "R2", "S"]
    },
    "Kanada": {
        "arohanam": ["S", "R2", "G2", "M1", "D1", "N2", "S'"],
        "avarohanam": ["S'", "N2", "P", "M1", "G2", "M1", "R2", "S"]
    },
    "Simhendramadhyamam": {
        "arohanam": ["S", "R2", "G2", "M2", "P", "D1", "N2", "S'"],
        "avarohanam": ["S'", "N2", "D1", "P", "M2", "G2", "R2", "S"]
    }
}

# Talams - defined by beat counts and structure
# Laghu (L) and Dhrutam (D)
# Adi: I4 O O (4 + 2 + 2 = 8 beats)
TALAM_DB = {
    "Adi": [1, 1, 1, 1, 0, 0, 0, 0], # Simplified beat emphasis (1=Strong, 0=Weak/Normal) for synthesis timing
    "Rupaka": [1, 1, 0, 1, 0, 0], # 2 + 4
    "Misra Chapu": [1, 0, 1, 1, 0, 1, 0], # 3 + 4 (7)
    "Khanda Chapu": [1, 0, 1, 1, 0], # 5
    "Eka": [1, 0, 0, 0] # 4 (I4)
}

def get_freq(swara: str, base_freq=BASE_FREQ) -> float:
    # Handle higher octave
    octave_shift = 0
    clean_swara = swara
    if "'" in swara:
        octave_shift = 1
        clean_swara = swara.replace("'", "")
    
    semitone = SWARA_MAP.get(clean_swara, 0)
    freq = base_freq * (2 ** ((semitone + (12 * octave_shift)) / 12))
    return freq
