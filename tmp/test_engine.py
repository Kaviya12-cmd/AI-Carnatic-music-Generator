"""Smoke test for the rebuilt audio_engine."""
import sys
sys.path.insert(0, "d:/violin_based_generator/backend")

from app.audio_engine import ViolinSynthesizer, Note

# Quick test WITHOUT reverb (reverb is CPU-heavy – tested separately)
synth = ViolinSynthesizer(reverb=False)

notes = [
    Note(freq=261.63, duration=0.4, swara_type="S"),
    Note(freq=293.66, duration=0.4, swara_type="R2"),   # gamaka swara
    Note(freq=329.63, duration=0.4, swara_type="G3"),   # gamaka swara
    Note(freq=349.23, duration=0.4, swara_type="M1"),
    Note(freq=392.00, duration=0.4, swara_type="P"),
    Note(freq=440.00, duration=0.4, swara_type="D2"),   # gamaka swara
    Note(freq=493.88, duration=0.4, swara_type="N3"),   # gamaka swara
    Note(freq=523.26, duration=0.6, swara_type="S", is_last=True),
]

buf = synth.synthesize_melody(notes)
data = buf.read()
print(f"OK  size={len(data):,}B  ({len(data)/1024:.1f} KB)  sr=44100  notes={len(notes)}")
assert len(data) > 44, "WAV too small – synthesis likely failed"

# Test with reverb on a shorter sequence
synth_rev = ViolinSynthesizer(reverb=True)
short_notes = [
    Note(freq=261.63, duration=0.25, swara_type="S"),
    Note(freq=392.00, duration=0.25, swara_type="P"),
]
buf2 = synth_rev.synthesize_melody(short_notes)
data2 = buf2.read()
print(f"OK  reverb size={len(data2):,}B")

print("ALL TESTS PASSED")
