import { useState, useEffect } from 'react';
import axios from 'axios';

// ── Shruti Options — Octave 3 (Low Register, matching backend PITCH_FREQ_MAP) ───
const SHRUTI_OPTIONS = [
    { label: "1 — C  (130.81 Hz)",  name: "C",  hz: 130.81 },
    { label: "1½ — C# (138.59 Hz)", name: "C#", hz: 138.59 },
    { label: "2 — D  (146.83 Hz)",  name: "D",  hz: 146.83 },
    { label: "2½ — D# (155.56 Hz)", name: "D#", hz: 155.56 },
    { label: "3 — E  (164.81 Hz)",  name: "E",  hz: 164.81 },
    { label: "4 — F  (174.61 Hz)",  name: "F",  hz: 174.61 },
    { label: "4½ — F# (185.00 Hz)", name: "F#", hz: 185.00 },
    { label: "5 — G  (196.00 Hz)",  name: "G",  hz: 196.00 },
    { label: "5½ — G# (207.65 Hz)", name: "G#", hz: 207.65 },
    { label: "6 — A  (220.00 Hz)",  name: "A",  hz: 220.00 },
    { label: "6½ — A# (233.08 Hz)", name: "A#", hz: 233.08 },
    { label: "7 — B  (246.94 Hz)",  name: "B",  hz: 246.94 },
];


const TEMPO_OPTIONS = [
    { label: "Slow — 60 BPM (Vilamba)", bpm: 60 },
    { label: "Medium — 90 BPM (Madhyama)", bpm: 90 },
    { label: "Fast — 120 BPM (Druta)", bpm: 120 },
];

const SARALI_OPTIONS = [
    { label: "Pattern 1: Basic Ascent/Descent", value: 1 },
    { label: "Pattern 2: Pairs (S R | G M | ...)", value: 2 },
    { label: "Pattern 3: Triplets (S R G | ...)", value: 3 },
    { label: "Pattern 4: Groups of Four", value: 4 },
    { label: "Pattern 5: Fusion Jump (Modern)", value: 5 },
    { label: "Pattern 6: Wide Leap (Intervallic)", value: 6 },
    { label: "Pattern 7: Modern Staccato", value: 7 },
    { label: "Pattern 8: Arpeggio Fusion", value: 8 },
];

// Sarali reference patterns shown in the UI — use actual swara-type names (e.g. R1, G3)
// so the displayed notation exactly matches what the backend generates.
const SARALI_REFERENCE = {
    1: "S  R1  G3  M1    P  D1  N3  S' | S'  N3  D1  P    M1  G3  R1  S",
    2: "S  R1 | R1  S | S  R1 | G3  M1 | R1  G3 | M1  P | …  (pairs ascending)",
    3: "S  R1  G3 | R1  G3  M1 | G3  M1  P | M1  P  D1 | P  D1  N3 | D1  N3  S' | …",
    4: "S  R1  G3  M1 | R1  G3  M1  P | G3  M1  P  D1 | M1  P  D1  N3 | P  D1  N3  S' | …",
    5: "S  G3 | R1  M1 | G3  P | M1  D1 | P  N3 | D1  S' | S'  D1 | N3  P | …",
    6: "S  P | M1  S' | G'  R' | S'  P | … (Modern wide intervals)",
    7: "S-S  R1-R1  G3-G3  M1-M1  P-P  D1-D1  N3-N3  S'-S'",
    8: "S  G3  P  S' | P  G3  S | R1  M1  D1  S' | D1  M1  R1",
};

// ── Western Note Detection ─────────────────────────────────────────────────
const WESTERN_KEYS = new Set([
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B", "C'", "C2", "C+",
]);

const isWesternInput = (text) => {
    if (!text.trim()) return false;
    const tokens = text.trim().toUpperCase().replace(/-/g, " ").split(/\s+/);
    return tokens.length > 0 && tokens.every(t => WESTERN_KEYS.has(t));
};

// ── Just Intonation Ratios (for UI preview only) ───────────────────────────
const SWARA_RATIOS = {
    "S": 1.0, "R1": 16 / 15, "R2": 9 / 8, "G2": 6 / 5, "G3": 5 / 4,
    "M1": 4 / 3, "M2": 45 / 32, "P": 3 / 2, "D1": 8 / 5, "D2": 5 / 3, "N2": 9 / 5, "N3": 15 / 8,
};

const CHROMATIC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

// Maps Just Intonation freq → nearest keyboard note name relative to Sa
const freqToKey = (freq, saFreq, saName) => {
    if (!freq || !saFreq) return '?';
    const semitones = Math.round(12 * Math.log2(freq / saFreq));
    if (semitones === 12) return saName + "'";
    if (semitones < 0 || semitones > 12) return '?';
    const saIdx = CHROMATIC.indexOf(saName);
    if (saIdx === -1) return '?';
    return CHROMATIC[(saIdx + semitones) % 12];
};

// ─────────────────────────────────────────────────────────────────────────────

const SongGenerator = () => {
    const [lyrics, setLyrics] = useState('');
    const [ragams, setRagams] = useState([]);
    const [talams, setTalams] = useState([]);
    const [selectedRagam, setSelectedRagam] = useState('');
    const [selectedTalam, setSelectedTalam] = useState('');
    const [shruti, setShruti] = useState(SHRUTI_OPTIONS[0]); // C default
    const [tempo, setTempo] = useState(TEMPO_OPTIONS[0]); // Slow default
    const [useSarali, setUseSarali] = useState(true);
    const [saraliIndex, setSaraliIndex] = useState(1);
    const [instrument, setInstrument] = useState('Violin');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [ragamInfo, setRagamInfo] = useState(null);
    const [error, setError] = useState('');

    const westernDetected = !useSarali && isWesternInput(lyrics);

    // Load ragams + talams
    useEffect(() => {
        const load = async () => {
            try {
                const [r, t] = await Promise.all([
                    axios.get('/api/ragams'),
                    axios.get('/api/talams'),
                ]);
                setRagams(r.data); setTalams(t.data);
                if (r.data.length && !selectedRagam) setSelectedRagam(r.data[0]);
                if (t.data.length && !selectedTalam) setSelectedTalam(t.data[0]);
            } catch (e) { console.error("Init error:", e); }
        };
        load();
    }, []);

    // Load ragam info
    useEffect(() => {
        if (!selectedRagam) return;
        setRagamInfo(null);
        axios.get(`/api/ragam_info/${selectedRagam}`)
            .then(r => setRagamInfo(r.data))
            .catch(() => setRagamInfo(null));
    }, [selectedRagam]);

    // Reset result on settings change
    useEffect(() => {
        setResult(null); setError('');
    }, [selectedRagam, shruti, tempo, saraliIndex, useSarali, lyrics]);

    // ── FIX: Shruti handler — guaranteed to stay in sync ──────────────────
    const handleShrutiChange = (e) => {
        const found = SHRUTI_OPTIONS.find(o => o.name === e.target.value);
        if (found) setShruti(found);
    };

    // ── Generate ──────────────────────────────────────────────────────────
    const handleGenerate = async () => {
        if (!useSarali && !lyrics.trim()) {
            setError("Please enter lyrics or western notes (e.g. C D E F G A B C')");
            return;
        }
        setLoading(true); setResult(null); setError('');
        try {
            // FIX: pitch_name always from current shruti state
            const payload = {
                ragam: selectedRagam,
                talam: selectedTalam,
                pitch_name: shruti.name,   // ✅ correct — never stale
                tempo: tempo.bpm,
                lyrics: lyrics,
                use_sarali: useSarali,
                sarali_index: saraliIndex,
                instrument,
            };
            console.log("[SongGenerator] Payload →", payload);
            const token = localStorage.getItem('token');
            const res = await axios.post('/api/generate', payload, {
                headers: { Authorization: `Bearer ${token}` },
            });
            setResult(res.data);
        } catch (e) {
            console.error("Gen error:", e.response?.data || e.message);
            if (e.response?.status === 401) { localStorage.removeItem('token'); window.location.reload(); }
            else setError(e.response?.data?.detail || 'Generation failed. Check console.');
        } finally { setLoading(false); }
    };

    return (
        <div className="glass-panel animate-fade-in"
            style={{ width: '100%', maxWidth: '920px', display: 'flex', flexDirection: 'column', gap: '2rem' }}>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>

                {/* ── LEFT: Controls ──────────────────────────────────── */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <h2 style={{ margin: 0 }}>Composition Controls</h2>

                    {/* Ragam */}
                    <label>Select Ragam</label>
                    <select value={selectedRagam} onChange={e => setSelectedRagam(e.target.value)}>
                        {ragams.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>

                    {ragamInfo && (
                        <div style={{ padding: '0.5rem 0.75rem', background: 'rgba(255,255,255,0.06)', borderRadius: '8px', fontSize: '0.72rem', lineHeight: 1.9, color: '#ccc' }}>
                            <span style={{ color: '#ffd700' }}>Aro: </span>{ragamInfo.arohanam.join(' ')}<br />
                            <span style={{ color: '#7effa0' }}>Ava: </span>{ragamInfo.avarohanam.join(' ')}<br />
                            <span style={{ color: '#f9a' }}>Jiva: </span>{ragamInfo.jiva?.join(', ')}
                            &emsp;<span style={{ color: '#adf' }}>Nyasa: </span>{ragamInfo.nyasa?.join(', ')}
                        </div>
                    )}

                    {/* Shruti */}
                    <label>
                        Shruti (Pitch)
                        <span style={{ marginLeft: '0.5rem', fontSize: '0.74rem', color: 'var(--accent-pink)' }}>
                            Sa = {shruti.name} ({shruti.hz.toFixed(2)} Hz)
                        </span>
                    </label>
                    <select value={shruti.name} onChange={handleShrutiChange}>
                        {SHRUTI_OPTIONS.map(o => <option key={o.name} value={o.name}>{o.label}</option>)}
                    </select>

                    {/* Tempo */}
                    <label>Tempo (BPM)</label>
                    <select value={tempo.bpm} onChange={e => setTempo(TEMPO_OPTIONS.find(o => o.bpm === Number(e.target.value)))}>
                        {TEMPO_OPTIONS.map(o => <option key={o.bpm} value={o.bpm}>{o.label}</option>)}
                    </select>

                    {/* Mode Toggle */}
                    <label>Composition Mode</label>
                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                        <button onClick={() => setUseSarali(true)}
                            style={{ flex: 1, background: useSarali ? 'var(--accent-pink)' : '#333', fontSize: '0.8rem', padding: '0.5rem', borderRadius: '6px', border: 'none', cursor: 'pointer', color: '#fff' }}>
                            🎼 Lessons
                        </button>
                        <button onClick={() => setUseSarali(false)}
                            style={{ flex: 1, background: !useSarali ? 'var(--accent-pink)' : '#333', fontSize: '0.8rem', padding: '0.5rem', borderRadius: '6px', border: 'none', cursor: 'pointer', color: '#fff' }}>
                            🎹 Custom
                        </button>
                    </div>

                    {/* Instrument */}
                    <label>Instrument</label>
                    <select value={instrument} onChange={e => setInstrument(e.target.value)}>
                        <option value="Violin">🎻 Violin (Precise DSP)</option>
                        <option value="Voice">🎤 Voice Synthesizer</option>
                        <option value="Modern Synth">🎹 Modern Fusion Synth (Biting Lead)</option>
                    </select>
                </div>

                {/* ── RIGHT: Lyric Box / Input ────────────────────────── */}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    {useSarali ? (
                        <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.05)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', flex: 1 }}>
                            <h3 style={{ marginTop: 0, color: 'var(--accent-gold)' }}>Sarali Varisai Lessons</h3>
                            <label>Select Pattern</label>
                            <select value={saraliIndex} onChange={e => setSaraliIndex(Number(e.target.value))}>
                                {SARALI_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                            </select>
                            <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(255,215,0,0.06)', borderRadius: '10px', border: '1px solid rgba(255,215,0,0.1)' }}>
                                <div style={{ color: '#ffd700', fontSize: '0.7rem', fontWeight: 'bold', marginBottom: '0.5rem', letterSpacing: '1px' }}>NOTATION PREVIEW</div>
                                <div style={{ fontSize: '1.1rem', color: '#fff', fontFamily: 'monospace', lineHeight: 1.8, wordSpacing: '4px' }}>
                                    {SARALI_REFERENCE[saraliIndex]}
                                </div>
                            </div>
                            <div style={{ marginTop: '1.5rem', fontSize: '0.8rem', color: '#888', lineHeight: 1.6 }}>
                                Sarali Varisai are the fundamental sequences in Carnatic music. These exercises help in mastering the swarasthsanas (note positions) and rhythm.
                            </div>
                        </div>
                    ) : (
                        <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.05)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', flex: 1, display: 'flex', flexDirection: 'column' }}>
                            <h3 style={{ marginTop: 0, color: 'var(--accent-gold)' }}>Lyric & Note Editor</h3>
                            <label>
                                Composition Box
                                {westernDetected && <span style={{ marginLeft: '0.5rem', fontSize: '0.7rem', color: '#7effa0' }}>• Western Mode Active</span>}
                            </label>
                            <textarea
                                rows={8}
                                placeholder={"Type Carnatic syllables (ta na dhim) or Western notes (C D E)..."}
                                value={lyrics}
                                onChange={e => setLyrics(e.target.value)}
                                style={{
                                    flex: 1,
                                    resize: 'none',
                                    fontFamily: westernDetected ? 'monospace' : 'inherit',
                                    color: westernDetected ? '#7effa0' : '#fff',
                                    fontSize: '1.1rem',
                                    padding: '1.25rem',
                                    background: 'rgba(0,0,0,0.25)',
                                    border: '1px solid rgba(255,255,255,0.1)',
                                    lineHeight: 1.5,
                                    borderRadius: '8px'
                                }}
                            />
                            <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                <div style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', fontSize: '0.68rem', color: '#aaa', lineHeight: 1.5 }}>
                                    <strong style={{ color: '#ffd700' }}>Mayamalavagowla (Sa=C):</strong><br />
                                    C=S &nbsp;C#=R1 &nbsp;E=G3 &nbsp;F=M1<br />
                                    G=P &nbsp;G#=D1 &nbsp;B=N3 &nbsp;C'=S'
                                </div>
                                <div style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', fontSize: '0.68rem', color: '#aaa', lineHeight: 1.5 }}>
                                    <strong style={{ color: '#7effa0' }}>Pro Tip:</strong><br />
                                    Use ' for Tara sthayi (C', S'). Use - for gaps or long notes.
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Error */}
            {error && (
                <div style={{ padding: '0.75rem 1rem', background: 'rgba(255,80,80,0.12)', border: '1px solid rgba(255,80,80,0.35)', borderRadius: '8px', color: '#ff8888', fontSize: '0.85rem' }}>
                    ⚠️ {error}
                </div>
            )}

            {/* Generate Button */}
            <button onClick={handleGenerate} disabled={loading}
                style={{ height: '3.5rem', fontSize: '1.1rem', cursor: loading ? 'wait' : 'pointer' }}>
                {loading ? '⟳ Generating Mastered Audio…' : '▶ Generate Carnatic Piece'}
            </button>

            {/* Result */}
            {result && (
                <div className="animate-fade-in" style={{ borderTop: '1px solid var(--glass-border)', paddingTop: '2rem' }}>
                    <h3 style={{ textAlign: 'center', marginBottom: '0.4rem' }}>
                        Carnatic Notation
                        {result.input_mode === 'western' && (
                            <span style={{ marginLeft: '0.5rem', fontSize: '0.74rem', color: '#7effa0' }}>🎹 Western → Swaras</span>
                        )}
                    </h3>
                    <div style={{ textAlign: 'center', marginBottom: '1.5rem', fontSize: '0.78rem', color: '#aaa' }}>
                        Ragam: <strong style={{ color: '#ffd700' }}>{result.ragam}</strong>
                        &nbsp;|&nbsp; Sa = <strong style={{ color: '#7effa0' }}>{result.pitch_name} ({parseFloat(result.pitch_hz).toFixed(2)} Hz)</strong>
                        &nbsp;|&nbsp; <strong>{result.tempo} BPM</strong>
                    </div>

                    {/* Swara Cards — shows swara name, keyboard note (Western), lyric, and frequency */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '0.4rem', marginBottom: '2rem' }}>
                        {result.notation.map((note, idx) => (
                            <div key={idx} style={{
                                minWidth: '70px', padding: '0.55rem 0.45rem',
                                background: 'rgba(255,255,255,0.07)', borderRadius: '10px',
                                border: '1px solid rgba(255,255,255,0.12)', textAlign: 'center',
                            }}>
                                {/* Carnatic Swara name — e.g. G3, R1, D1 */}
                                <div style={{ color: '#ffd700', fontWeight: 'bold', fontSize: '1.05rem' }}>{note.swara}</div>
                                {/* Western keyboard note — e.g. E for G3, G# for D1 */}
                                {note.keyboard_note && (
                                    <div style={{ color: '#7effa0', fontSize: '0.7rem', fontWeight: '600', marginTop: '0.1rem' }}>
                                        ({note.keyboard_note})
                                    </div>
                                )}
                                {/* Lyric syllable (if any) */}
                                <div style={{ color: '#ccc', fontSize: '0.68rem', marginTop: '0.15rem' }}>
                                    {note.lyric || '—'}
                                </div>
                                {/* Frequency — always 2 dp */}
                                <div style={{ fontSize: '0.58rem', color: '#666', marginTop: '0.1rem' }}>
                                    {parseFloat(note.freq_hz).toFixed(2)} Hz
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Audio */}
                    <audio controls src={`data:audio/wav;base64,${result.audio_base64}`} style={{ width: '100%' }} />
                </div>
            )}
        </div>
    );
};

export default SongGenerator;