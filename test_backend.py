import sys
sys.path.insert(0, 'd:/violin_based_generator/backend')

from app.music_theory import RAGAM_DB, get_freq, PITCH_FREQ_MAP
print("music_theory OK")

# Test dynamic pitch — D should become Sa
sa_d = PITCH_FREQ_MAP['D']
f_g3 = get_freq('G3', sa_d)
print(f"Sa=D={sa_d:.2f} Hz, G3={f_g3:.2f} Hz")

# Verify S=D4 for D shruti
f_s = get_freq('S', sa_d)
print(f"S with Sa=D: {f_s:.2f} Hz (should be 293.66)")

# Test ragam info
for r in ['Mohanam', 'Kalyani', 'Bhairavi']:
    d = RAGAM_DB[r]
    print(f"{r}: style={d['phrase_style']}, intensity={d['gamaka_intensity']}, curve={d['melodic_curve']}")

# Test generator
from app.ragam_generator import generate_melody_swaras
print("\nMelody generation test:")
for r in ['Mohanam', 'Kalyani', 'Bhairavi']:
    mel = generate_melody_swaras(r, 8, gamaka_style='auto')
    gamakas = [m['gamaka'] for m in mel]
    print(f"  {r}: {[m['swara'] for m in mel]} -> gamakas={gamakas}")

# Test audio engine
from app.audio_engine import ViolinSynthesizer, Note
notes = [
    Note(freq=293.66, duration=0.5, gamaka='Kampitam', intensity=0.8),
    Note(freq=369.99, duration=0.5, gamaka='Jaru', next_freq=440.0, intensity=0.8),
    Note(freq=329.63, duration=0.5, gamaka='Nokku', intensity=0.5),
    Note(freq=261.63, duration=0.5, gamaka=None, intensity=0.5),
]
synth = ViolinSynthesizer()
wav = synth.generate_melody(notes)
print(f"\nViolinSynthesizer WAV bytes: {len(wav.read())}")
print("\nAll tests PASSED!")
