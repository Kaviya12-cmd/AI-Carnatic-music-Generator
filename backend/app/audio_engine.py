import numpy as np
from scipy.io.wavfile import write, read
import io
from dataclasses import dataclass
from typing import List, Optional

SAMPLE_RATE = 44100

@dataclass
class Note:
    freq: float
    duration: float  # seconds
    gamaka: Optional[str] = None
    next_freq: Optional[float] = None  # For slides/Jaru

class SamplerSynthesizer:
    def __init__(self, sample_path: str, base_freq: float = 261.63):
        self.sr, self.data = read(sample_path)
        # Convert to mono if stereo
        if len(self.data.shape) > 1:
            self.data = np.mean(self.data, axis=1)
        self.data = self.data.astype(np.float32) / 32768.0
        self.base_freq = base_freq

    def _pitch_shift(self, audio, n_steps):
        # n_steps is semitones. 
        # Calculate speed factor. Higher pitch = faster speed = shorter duration.
        # factor = 2 ** (n_steps / 12.0)
        # We need to RESAMPLE.
        # If we want higher pitch, we play faster (fewer samples for same content).
        # But we actually want to sustain duration?
        # A simple sampler changes duration with pitch. "Chipmunk effect".
        # For a "Song Generator", we need to stretch/loop to match duration.
        pass

    def _get_note_audio(self, target_freq, duration):
        # 1. Calculate pitch ratio
        ratio = target_freq / self.base_freq
        
        # 2. Resample
        # New length = original_len / ratio
        new_len = int(len(self.data) / ratio)
        
        # Simple Linear Interpolation Resampling
        indices = np.linspace(0, len(self.data)-1, new_len)
        resampled = np.interp(indices, np.arange(len(self.data)), self.data)
        
        # 3. Match Duration
        target_samples = int(duration * self.sr)
        
        if len(resampled) >= target_samples:
            # Crop
            return resampled[:target_samples]
        else:
            # Loop/Tile to fill duration
            repeats = int(np.ceil(target_samples / len(resampled)))
            tiled = np.tile(resampled, repeats)
            return tiled[:target_samples]

    def generate_melody(self, notes: List[Note]):
        full_wave = np.array([])
        for note in notes:
            chunk = self._get_note_audio(note.freq, note.duration)
            
            # Simple envelope to avoid clicks
            fade_len = int(0.01 * self.sr)
            if len(chunk) > 2 * fade_len:
                chunk[:fade_len] *= np.linspace(0, 1, fade_len)
                chunk[-fade_len:] *= np.linspace(1, 0, fade_len)
                
            full_wave = np.concatenate((full_wave, chunk))
            
        # Normalize
        if len(full_wave) > 0:
            mx = np.max(np.abs(full_wave))
            if mx > 0: full_wave = full_wave / mx
        
        audio_data = (full_wave * 32767).astype(np.int16)
        byte_io = io.BytesIO()
        write(byte_io, self.sr, audio_data)
        byte_io.seek(0)
        return byte_io

class ViolinSynthesizer:
    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sr = sample_rate

    def _get_sawtooth(self, freq, duration, t):
        return 2 * (t * freq - np.floor(t * freq + 0.5))

    def _apply_envelope(self, wave, duration):
        attack = 0.05
        decay = 0.1
        release = 0.05
        sustain_level = 0.8
        
        total_samples = len(wave)
        attack_samples = int(attack * self.sr)
        decay_samples = int(decay * self.sr)
        release_samples = int(release * self.sr)
        
        # Ensure envelope doesn't exceed duration
        if attack_samples + decay_samples + release_samples > total_samples:
            scale = total_samples / (attack_samples + decay_samples + release_samples)
            attack_samples = int(attack_samples * scale)
            decay_samples = int(decay_samples * scale)
            release_samples = int(release_samples * scale)

        env = np.ones(total_samples) * sustain_level
        # Attack
        env[:attack_samples] = np.linspace(0, 1, attack_samples)
        # Decay
        env[attack_samples:attack_samples+decay_samples] = np.linspace(1, sustain_level, decay_samples)
        # Release
        env[-release_samples:] = np.linspace(sustain_level, 0, release_samples)
        
        return wave * env

    def _generate_note_wave(self, note: Note):
        t = np.linspace(0, note.duration, int(self.sr * note.duration), endpoint=False)
        current_freq = note.freq
        
        # Gamaka Logic
        modulator = 0
        if note.gamaka == "Kampitam":
            # Oscillate pitch ~5Hz, depth ~semitone
            vibrato_freq = 5.0 
            vibrato_depth = 0.03 * current_freq # +/- 3%
            modulator = vibrato_depth * np.sin(2 * np.pi * vibrato_freq * t)
            
        elif note.gamaka == "Jaru" and note.next_freq:
            # Slide from freq to next_freq
            freq_sweep = np.linspace(note.freq, note.next_freq, len(t))
            # Integrate phase for variable frequency
            phase = np.cumsum(freq_sweep) / self.sr
            wave = 2 * (phase - np.floor(phase + 0.5))
            return self._apply_envelope(wave, note.duration)
            
        elif note.gamaka == "Nokku":
             # Quick dip from above
             pass 

        # Default vibrato for violin feel
        normal_vibrato = 0.005 * current_freq * np.sin(2 * np.pi * 6.0 * t)
        
        # Instantaneous phase integration for modulation
        inst_freq = current_freq + modulator + normal_vibrato
        phase = np.cumsum(inst_freq) / self.sr
        
        # Synthesis: Sawtooth for Violin Body
        # Adding harmonics for richness
        wave = 0.5 * (2 * (phase - np.floor(phase + 0.5))) # Fundamental
        
        # Simple recursive harmonics to simulate bowing friction (roughly)
        # Or just a couple of harmonics
        phase2 = 2 * phase
        wave += 0.25 * (2 * (phase2 - np.floor(phase2 + 0.5)))
        
        phase3 = 3 * phase
        wave += 0.12 * (2 * (phase3 - np.floor(phase3 + 0.5)))

        return self._apply_envelope(wave, note.duration)

    def generate_melody(self, notes: List[Note]):
        full_wave = np.array([])
        for i, note in enumerate(notes):
             # Lookahead for Jaru
            if note.gamaka == "Jaru" and i + 1 < len(notes):
                note.next_freq = notes[i+1].freq
            
            chunk = self._generate_note_wave(note)
            full_wave = np.concatenate((full_wave, chunk))
            
        # Normalize
        if len(full_wave) > 0:
            full_wave = full_wave / np.max(np.abs(full_wave))
        
        # Convert to 16-bit PCM
        audio_data = (full_wave * 32767).astype(np.int16)
        
        byte_io = io.BytesIO()
        write(byte_io, self.sr, audio_data)
        byte_io.seek(0)
        return byte_io

class FormantSynthesizer(ViolinSynthesizer):
    def __init__(self, sample_rate=SAMPLE_RATE):
        super().__init__(sample_rate)
        # Approximate formant frequencies for 'a', 'i', 'u', 'e', 'o' (Tenor)
        self.vowels = {
            'a': [(730, 0), (1090, 0), (2440, 0)],
            'i': [(270, 0), (2290, 0), (3010, 0)],
            'u': [(300, 0), (870, 0), (2240, 0)],
            'e': [(530, 0), (1840, 0), (2480, 0)],
            'o': [(570, 0), (840, 0), (2410, 0)],
        }

    def _apply_formant_filter(self, wave, freq, formants):
        # A simple implementation of formant using bandpass filters is complex in time domain without scipy.signal
        # Simplified approach: Add sine waves at formant frequencies? No, that's additive synthesis.
        # Subtractive: Generate rich buzz (Sawtooth) and filter.
        # Since we use numpy, let's try a spectral envelope approach or just additive synthesis of formants.
        
        # Better: Additive synthesis of formants driven by fundamental pulse.
        # Pulse train spectrum is flat. Formants shape it.
        # Let's do simple Additive Synthesis: Sum of Formants.
        # For each formant: A damped sine wave reset every pitch period? 
        # Or just generate sine waves at F1, F2, F3 modulated by F0?
        # Let's stick to the Violin sawtooth but apply a crude EQ filter manually or just 3 resonant filters.
        
        # Simplest reasonable "Voice" for this constraint:
        # A Pulse wave (rich harmonics) low-pass filtered.
        # PLUS mixing in sine waves at the Formant Frequencies.
        
        t = np.linspace(0, len(wave)/self.sr, len(wave), endpoint=False)
        output = np.zeros_like(wave)
        
        # Base rich tone (Glottal source)
        output += 0.5 * wave
        
        # Add formants (Resonances)
        # Using simple decaying sine waves triggered at fundamental frequency is "FOF" synthesis, hard to do efficient here.
        # Let's just add continuous sine waves at formant freqs, amplitude modulated by the source wave? 
        # No, that's Ring Mod.
        
        # Let's go with "Pulse Wave + Fixed Formant Sines" approximation
        for f_freq, _ in formants:
            # Create a resonance at f_freq
            # To sound like a formant, it must be excited by the fundamental.
            # Simple approximation: Sine wave at f_freq, but amplitude follows the envelope of the note
            
            # Actually, standard subtractive is best.
            # But implementing a filter in pure numpy without lfilter is slow/messy.
            
            # Let's return the input wave but modified to be "softer" (Triangle) for 'u'/'o' and brighter for 'a'/'i'
            pass
            
        # Fallback to simple variable-width pulse (PWM) which sounds vocal-ish
        return wave 

    def _generate_note_wave(self, note: Note, vowel='a'):
        # Generate glottal source (Pulse train / Sawtooth)
        t = np.linspace(0, note.duration, int(self.sr * note.duration), endpoint=False)
        
        freq = note.freq
        
        # Vibrato (Singers use heavy vibrato)
        vibrato_freq = 5.5
        vibrato_depth = 0.02 * freq
        modulator = vibrato_depth * np.sin(2 * np.pi * vibrato_freq * t)
        inst_freq = freq + modulator
        phase = np.cumsum(inst_freq) / self.sr
        
        # Glottal Source: Band-limited Impulse Train approximation or simple Sawtooth
        # Sawtooth is decent.
        source = 2 * (phase - np.floor(phase + 0.5))
        
        # Vowel Shaping (Crude Formant Synthesis via Additive bands)
        # Instead of filtering, we generate the harmonics nearest to formants with higher amplitude.
        
        # Get target formants
        f_freqs = self.vowels.get(vowel, self.vowels['a'])
        
        output = np.zeros_like(source)
             
        # Add fundamental
        output += 0.5 * np.sin(2 * np.pi * phase)
        
        # Add formants: Add sine waves at specific harmonics closest to formant frequencies
        # This keeps it harmonic (singing) rather than inharmonic (bell)
        for f_freq, _ in f_freqs:
            harmonic_idx = round(f_freq / freq)
            if harmonic_idx < 1: harmonic_idx = 1
            
            # Amplitudes fall off
            amp = 0.3 * (1.0 / (1.0 + 0.001 * abs(f_freq - (harmonic_idx * freq)))) 
            
            output += amp * np.sin(2 * np.pi * harmonic_idx * phase)
            
            # Also add neighbors for width
            output += (amp/2) * np.sin(2 * np.pi * (harmonic_idx+1) * phase)
            output += (amp/2) * np.sin(2 * np.pi * (harmonic_idx-1) * phase)

        return self._apply_envelope(output, note.duration)

    def generate_melody(self, notes: List[Note], lyrics: List[str] = None):
        if lyrics is None:
            lyrics = ["a"] * len(notes)
            
        full_wave = np.array([])
        
        # Basic vowel mapper
        def get_vowel(text):
            text = text.lower()
            if 'a' in text: return 'a'
            if 'i' in text: return 'i'
            if 'ee' in text: return 'i'
            if 'u' in text: return 'u'
            if 'o' in text: return 'o'
            if 'e' in text: return 'e'
            return 'a'

        for i, (note, lyric) in enumerate(zip(notes, lyrics)):
            vowel = get_vowel(lyric)
            chunk = self._generate_note_wave(note, vowel)
            full_wave = np.concatenate((full_wave, chunk))
            
        if len(full_wave) > 0:
            full_wave = full_wave / np.max(np.abs(full_wave))
            
        audio_data = (full_wave * 32767).astype(np.int16)
        byte_io = io.BytesIO()
        write(byte_io, self.sr, audio_data)
        byte_io.seek(0)
        return byte_io
