
"""
ragam_generator.py – Rule-Based Carnatic Phrase Engine (FULLY FIXED)
=====================================================================
FIXES:
1. SARALI_PATTERNS — correct ascent + descent sequences for all 4 patterns
2. swara_types-based mapping (not arohanam index) — fixes Vakra ragams
3. Pentatonic ragam safe fallback
4. Tara Sa always = S'
"""

import random
from typing import List, Dict
from .music_theory import RAGAM_DB

# ── Sarali Varisai Patterns ────────────────────────────────────────────────
# These are GENERIC patterns using position names S R G M P D N S'
# They get mapped to ragam-specific swaras via build_swara_map()
#
# Pattern 1: Basic ascent + descent (16 notes)
#   S R G M P D N S' | S' N D P M G R S
#
# Pattern 2: Pairs ascending + descending (40 notes)
#   S R|G M|R G|M P|G M|P D|M P|D N|P D|N S' | S' N|D P|N D|P M|D P|M G|P M|G R|M G|R S
#
# Pattern 3: Triplets ascending + descending (36 notes)
#   S R G|R G M|G M P|M P D|P D N|D N S' | S' N D|N D P|D P M|P M G|M G R|G R S
#
# Pattern 4: Groups of 4 ascending + descending (40 notes)
#   S R G M|R G M P|G M P D|M P D N|P D N S' | S' N D P|N D P M|D P M G|P M G R|M G R S

SARALI_PATTERNS: Dict[int, List[str]] = {

    1: [
        # Ascent
        "S", "R", "G", "M", "P", "D", "N", "S'",
        # Descent
        "S'", "N", "D", "P", "M", "G", "R", "S",
    ],

    2: [
        # Ascent — pairs
        "S",  "R",  "G",  "M",
        "R",  "G",  "M",  "P",
        "G",  "M",  "P",  "D",
        "M",  "P",  "D",  "N",
        "P",  "D",  "N",  "S'",
        # Descent — pairs
        "S'", "N",  "D",  "P",
        "N",  "D",  "P",  "M",
        "D",  "P",  "M",  "G",
        "P",  "M",  "G",  "R",
        "M",  "G",  "R",  "S",
    ],

    3: [
        # Ascent — triplets
        "S",  "R",  "G",
        "R",  "G",  "M",
        "G",  "M",  "P",
        "M",  "P",  "D",
        "P",  "D",  "N",
        "D",  "N",  "S'",
        # Descent — triplets
        "S'", "N",  "D",
        "N",  "D",  "P",
        "D",  "P",  "M",
        "P",  "M",  "G",
        "M",  "G",  "R",
        "G",  "R",  "S",
    ],

    4: [
        # Ascent — groups of 4
        "S",  "R",  "G",  "M",
        "R",  "G",  "M",  "P",
        "G",  "M",  "P",  "D",
        "M",  "P",  "D",  "N",
        "P",  "D",  "N",  "S'",
        # Descent — groups of 4
        "S'", "N",  "D",  "P",
        "N",  "D",  "P",  "M",
        "D",  "P",  "M",  "G",
        "P",  "M",  "G",  "R",
        "M",  "G",  "R",  "S",
    ],

    # ── Modern Fusion Patterns ──────────────────────────────────────────────
    5: [
        # Fusion Jump (syncopated flow)
        "S", "G", "R", "M", "G", "P", "M", "D", "P", "N", "D", "S'",
        "S'", "D", "N", "P", "D", "M", "P", "G", "M", "R", "G", "S",
    ],
    6: [
        # Wide Leap (modern intervallic leaps)
        "S", "P", "G", "S'", "G'", "R'", "S'", "P",
        "S'", "G", "N", "D", "P", "M", "G", "R", "S",
    ],
    7: [
        # Modern Staccato (rhythmic doubles)
        "S", "S", "R", "R", "G", "G", "M", "M", "P", "P", "D", "D", "N", "N", "S'", "S'",
        "S'", "S'", "N", "N", "D", "D", "P", "P", "M", "M", "G", "G", "R", "R", "S", "S",
    ],
    8: [
        # Arpeggio Fusion (contemporary chords)
        "S", "G", "P", "S'", "P", "G", "S", 
        "R", "M", "D", "S'", "D", "M", "R",
    ],
}


# ── Swara Map Builder ──────────────────────────────────────────────────────
def _build_swara_map(ragam_name: str) -> Dict[str, str]:
    """
    Builds position → actual swara mapping using swara_types.

    FIX: Uses swara_types (not arohanam indices) so Vakra ragams
    like Sahana (where M1 appears twice in arohanam) work correctly.

    Position mapping:
      S  → swara_types[0]  (always Sa)
      R  → swara_types[1]  (Ri variant)
      G  → swara_types[2]  (Ga variant)
      M  → swara_types[3]  (Ma variant — pentatonic fallback to Pa)
      P  → swara_types[4]  (Pa)
      D  → swara_types[5]  (Dha variant)
      N  → swara_types[6]  (Ni variant)
      S' → always "S'"     (Tara Sa)
    """
    ragam_data = RAGAM_DB.get(ragam_name)
    if not ragam_data:
        return {}

    types = ragam_data["swara_types"]

    def safe_get(idx: int) -> str:
        return types[idx] if idx < len(types) else types[-1]

    return {
        "S":  types[0],
        "R":  safe_get(1),
        "G":  safe_get(2),
        "M":  safe_get(3),
        "P":  safe_get(4),
        "D":  safe_get(5),
        "N":  safe_get(6),
        "S'": types[0] + "'",   # Tara Sa — always S'
    }


# ── Main Sarali Varisai Generator ─────────────────────────────────────────
def get_sarali_varisai(pattern_index: int, ragam_name: str) -> List[str]:
    """
    Returns the correct Sarali Varisai note sequence for a ragam.

    Steps:
    1. Get pattern template (generic S R G M positions)
    2. Map positions to actual ragam swaras using swara_types
    3. Validate — remove any note not in swara_types
    """
    ragam_data = RAGAM_DB.get(ragam_name)
    if not ragam_data:
        return []

    # Step 1: Get generic pattern
    pattern = SARALI_PATTERNS.get(pattern_index, SARALI_PATTERNS[1])

    # Step 2: Map to ragam-specific swaras
    swara_map = _build_swara_map(ragam_name)
    mapped = [swara_map.get(pos, pos) for pos in pattern]

    # Step 3: Validate — only allowed swaras pass through
    allowed = set(ragam_data["swara_types"]) | {"S'"}
    validated = []
    for note in mapped:
        clean = note.replace("'", "").replace("_", "")
        if clean in ragam_data["swara_types"] or note == "S'":
            validated.append(note)
        else:
            # Fallback to Sa if somehow invalid
            validated.append(ragam_data["swara_types"][0])

    return validated


# ── Debug Helper ──────────────────────────────────────────────────────────
def debug_pattern(ragam_name: str, pattern_index: int = 1):
    """Prints the sarali pattern for a ragam — use during testing."""
    notes = get_sarali_varisai(pattern_index, ragam_name)
    print(f"\n=== {ragam_name} | Pattern {pattern_index} ===")
    if pattern_index == 1:
        mid = len(notes) // 2
        print(f"  Ascent:  {' '.join(notes[:mid])}")
        print(f"  Descent: {' '.join(notes[mid:])}")
    elif pattern_index == 3:
        for i in range(0, len(notes), 3):
            print(f"  {' '.join(notes[i:i+3])}", end="  ")
        print()
    else:
        for i in range(0, len(notes), 4):
            print(f"  {' '.join(notes[i:i+4])}", end="  ")
        print()


# ── Phrase Engine ─────────────────────────────────────────────────────────
class RagamPhraseEngine:
    """Rule-based melody generator for non-sarali (lyrics) mode."""

    def __init__(self, ragam_name: str):
        self.ragam_name = ragam_name
        self.data = RAGAM_DB.get(ragam_name)
        if not self.data:
            raise ValueError(f"Ragam '{ragam_name}' not found.")

        self.aro      = self.data["arohanam"]
        self.ava      = self.data["avarohanam"]
        self.jiva     = self.data["jiva"]
        self.nyasa    = self.data["nyasa"]
        self.prayogams = self.data["prayogams"]

        # FIX: Use swara_types as note pool (not arohanam+avarohanam)
        # This prevents vakra/repeated notes from polluting selection
        self.allowed_swaras = self.data["swara_types"] + ["S'"]

    def generate_melody(self, length_in_beats: int) -> List[str]:
        """Generates melody by stitching prayogams and resolving gaps."""
        melody = []
        current_swara = "S"

        while len(melody) < length_in_beats:
            if random.random() < 0.7:
                block = random.choice(self.prayogams)
                melody.extend(block)
            else:
                next_note = self._get_next_logical_swara(current_swara)
                melody.append(next_note)
                current_swara = next_note

        melody = melody[:length_in_beats]

        # Resolve final note to Nyasa swara
        if melody and melody[-1] not in self.nyasa:
            melody[-1] = random.choice(self.nyasa)

        return melody

    def _get_next_logical_swara(self, prev: str) -> str:
        """Weighted selection — Jiva swaras get 3× weight."""
        candidates = self.allowed_swaras[:]
        weights = [
            3.0 if c in self.jiva else
            1.5 if c in self.nyasa else
            1.0
            for c in candidates
        ]
        return random.choices(candidates, weights=weights, k=1)[0]


# ── Factory Functions ──────────────────────────────────────────────────────
def generate_full_ascent_descent(ragam_name: str) -> List[str]:
    """Returns full arohanam + avarohanam sequence."""
    data = RAGAM_DB.get(ragam_name)
    if not data:
        return []
    return data["arohanam"] + data["avarohanam"]


def generate_ragam_melody(ragam_name: str, length: int) -> List[str]:
    """Factory function for phrase-based (lyrics) generation."""
    try:
        engine = RagamPhraseEngine(ragam_name)
        return engine.generate_melody(length)
    except Exception:
        data = RAGAM_DB.get(ragam_name)
        if not data:
            return []
        # FIX: fallback also uses swara_types
        allowed = data["swara_types"] + ["S'"]
        return [random.choice(allowed) for _ in range(length)]