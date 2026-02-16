import { useState, useEffect } from 'react';
import axios from 'axios';

const SHRUTI_MAP = {
    "1 (C)": 261.63,
    "1.5 (C#)": 277.18,
    "2 (D)": 293.66,
    "2.5 (D#)": 311.13,
    "3 (E)": 329.63,
    "4 (F)": 349.23,
    "4.5 (F#)": 369.99,
    "5 (G)": 392.00,
    "5.5 (G#)": 415.30,
    "6 (A)": 440.00,
    "6.5 (A#)": 466.16,
    "7 (B)": 493.88
};

const SongGenerator = () => {
    const [lyrics, setLyrics] = useState('');
    const [ragams, setRagams] = useState([]);
    const [talams, setTalams] = useState([]);
    const [selectedRagam, setSelectedRagam] = useState('');
    const [selectedTalam, setSelectedTalam] = useState('');
    const [selectedShruti, setSelectedShruti] = useState("1 (C)");
    const [gamaka, setGamaka] = useState('None');
    const [instrument, setInstrument] = useState('Violin');
    const [loading, setLoading] = useState(false);
    const [training, setTraining] = useState(false);
    const [trainMessage, setTrainMessage] = useState('');
    const [result, setResult] = useState(null);

    useEffect(() => {
        // Fetch options
        const fetchData = async () => {
            try {
                const rRes = await axios.get('/api/ragams');
                const tRes = await axios.get('/api/talams');
                setRagams(rRes.data);
                setTalams(tRes.data);
                if (rRes.data.length > 0) setSelectedRagam(rRes.data[0]);
                if (tRes.data.length > 0) setSelectedTalam(tRes.data[0]);
            } catch (e) {
                console.error("Failed to fetch metadata", e);
            }
        };
        fetchData();
    }, []);

    const [audioFile, setAudioFile] = useState(null);
    const [conversionStatus, setConversionStatus] = useState('');

    const bufferToWav = (buffer) => {
        const numOfChan = buffer.numberOfChannels;
        const length = buffer.length * numOfChan * 2 + 44;
        const out = new ArrayBuffer(length);
        const view = new DataView(out);
        const channels = [];
        let sample;
        let offset = 0;
        let pos = 0;

        // write RIFF chunk descriptor
        writeString(view, pos, 'RIFF'); pos += 4;
        view.setUint32(pos, length - 8, true); pos += 4;
        writeString(view, pos, 'WAVE'); pos += 4;
        writeString(view, pos, 'fmt '); pos += 4;
        view.setUint32(pos, 16, true); pos += 4;
        view.setUint16(pos, 1, true); pos += 2;
        view.setUint16(pos, numOfChan, true); pos += 2;
        view.setUint32(pos, buffer.sampleRate, true); pos += 4;
        view.setUint32(pos, buffer.sampleRate * 2 * numOfChan, true); pos += 4;
        view.setUint16(pos, numOfChan * 2, true); pos += 2;
        view.setUint16(pos, 16, true); pos += 2;
        writeString(view, pos, 'data'); pos += 4;
        view.setUint32(pos, length - pos - 4, true); pos += 4;

        for (let i = 0; i < buffer.numberOfChannels; i++) channels.push(buffer.getChannelData(i));

        while (pos < length) {
            for (let i = 0; i < numOfChan; i++) {
                sample = Math.max(-1, Math.min(1, channels[i][offset]));
                sample = (0.5 + sample < 0 ? sample * 32768 : sample * 32767) | 0;
                view.setInt16(pos, sample, true); pos += 2;
            }
            offset++;
        }
        return new Blob([out], { type: 'audio/wav' });
    };

    const writeString = (view, offset, string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    };

    const handleFileChange = async (e) => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            setConversionStatus('Converting audio format...');

            try {
                const arrayBuffer = await file.arrayBuffer();
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);

                // Convert to WAV
                const wavBlob = bufferToWav(audioBuffer);
                const wavFile = new File([wavBlob], "converted_voice.wav", { type: "audio/wav" });

                setAudioFile(wavFile);
                setConversionStatus('Ready (Converted to WAV)');
            } catch (err) {
                console.error("Conversion failed", err);
                setConversionStatus('Error converting file. Please use WAV.');
                // Fallback
                setAudioFile(file);
            }
        }
    };

    const handleTrain = async () => {
        if (!audioFile) return;
        setTraining(true);
        setTrainMessage('Uploading and calibrating voice profile...');
        try {
            const token = localStorage.getItem('token');
            const formData = new FormData();
            formData.append('pitch', SHRUTI_MAP[selectedShruti]);
            formData.append('file', audioFile);

            const res = await axios.post('/api/train_voice', formData, {
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'multipart/form-data'
                }
            });
            setTrainMessage(res.data.message);
        } catch (e) {
            console.error(e);
            if (e.response && e.response.status === 401) {
                alert("Session expired. Please login again.");
                localStorage.removeItem('token');
                window.location.reload();
            } else {
                setTrainMessage('Training failed. Check server connection.');
            }
        } finally {
            setTraining(false);
        }
    };

    const handleGenerate = async () => {
        if (!lyrics) {
            alert("Please enter lyrics to generate music.");
            return;
        }
        setLoading(true);
        setResult(null);
        try {
            const token = localStorage.getItem('token');
            let response;
            if (instrument === "MyVoice" && audioFile) {
                const formData = new FormData();
                formData.append('lyrics', lyrics);
                formData.append('ragam', selectedRagam);
                formData.append('talam', selectedTalam);
                formData.append('gamaka_style', gamaka);
                formData.append('instrument', instrument);
                formData.append('pitch', SHRUTI_MAP[selectedShruti]);
                formData.append('file', audioFile);

                response = await axios.post('/api/generate_with_audio', formData, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                        'Content-Type': 'multipart/form-data'
                    }
                });
            } else {
                response = await axios.post('/api/generate', {
                    lyrics,
                    ragam: selectedRagam,
                    talam: selectedTalam,
                    gamaka_style: gamaka,
                    instrument,
                    pitch: SHRUTI_MAP[selectedShruti]
                }, {
                    headers: { Authorization: `Bearer ${token}` }
                });
            }
            setResult(response.data);
        } catch (e) {
            console.error(e);
            if (e.response && e.response.status === 401) {
                alert("Session expired. Please login again.");
                localStorage.removeItem('token');
                window.location.reload();
            } else {
                alert("Generation failed");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="glass-panel animate-fade-in" style={{ width: '100%', maxWidth: '800px', display: 'flex', flexDirection: 'column', gap: '2rem' }}>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                {/* Left Column: Controls */}
                <div>
                    <h2>Composition Controls</h2>

                    <label>Select Ragam</label>
                    <select value={selectedRagam} onChange={e => setSelectedRagam(e.target.value)}>
                        {ragams.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>

                    <label>Select Talam</label>
                    <select value={selectedTalam} onChange={e => setSelectedTalam(e.target.value)}>
                        {talams.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>

                    <label>Gamaka Style (Violin)</label>
                    <select value={gamaka} onChange={e => setGamaka(e.target.value)}>
                        <option value="None">Straight Notes</option>
                        <option value="Kampitam">Kampitam (Shake)</option>
                        <option value="Jaru">Jaru (Slide)</option>
                        <option value="Nokku">Nokku (Stress)</option>
                    </select>

                    <label>Pitch / Shruti (Scale)</label>
                    <select value={selectedShruti} onChange={e => setSelectedShruti(e.target.value)}>
                        {Object.keys(SHRUTI_MAP).map(s => <option key={s} value={s}>{s}</option>)}
                    </select>

                    <label>Instrument</label>
                    <select value={instrument} onChange={e => setInstrument(e.target.value)}>
                        <option value="Violin">Violin</option>
                        <option value="Voice">Voice Synthesizer (Beta)</option>
                        <option value="MyVoice">My Voice (Clone)</option>
                    </select>

                    {instrument === 'MyVoice' && (
                        <div className="glass-panel" style={{ marginTop: '1rem', padding: '1rem', border: '1px solid var(--accent-pink)' }}>
                            <h4 style={{ margin: '0 0 1rem 0' }}>Voice Clone Setup</h4>
                            <label>Cloning Reference (AAC/WAV/MP3)</label>
                            <input type="file" accept="audio/*" onChange={handleFileChange} />
                            {conversionStatus && <div style={{ fontSize: '0.8rem', color: '#ffd700', margin: '0.5rem 0' }}>{conversionStatus}</div>}

                            <button
                                onClick={handleTrain}
                                disabled={training || !audioFile}
                                style={{ background: 'var(--accent-pink)', fontSize: '0.8rem', padding: '0.5rem' }}
                            >
                                {training ? 'Calibrating...' : 'Train Voice Profile'}
                            </button>
                            {trainMessage && <div style={{ fontSize: '0.8rem', color: '#4caf50', marginTop: '0.5rem' }}>{trainMessage}</div>}
                        </div>
                    )}
                </div>

                {/* Right Column: Lyrics */}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <h2>Lyrics</h2>
                    <textarea
                        rows="8"
                        placeholder="Type your lyrics here (e.g. 'Sa ri ga ma pa da ni sa')"
                        value={lyrics}
                        onChange={e => setLyrics(e.target.value)}
                        style={{ flex: 1, resize: 'none' }}
                    ></textarea>
                </div>
            </div>

            <button onClick={handleGenerate} disabled={loading}>
                {loading ? 'Synthesizing Audio...' : 'Generate Composition'}
            </button>

            {/* Results Section */}
            {
                result && (
                    <div className="animate-fade-in" style={{ marginTop: '2rem', borderTop: '1px solid var(--glass-border)', paddingTop: '2rem' }}>
                        <h3 style={{ textAlign: 'center' }}>Generated Notation</h3>

                        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', marginBottom: '2rem' }}>
                            {result.notation.map((note, idx) => (
                                <div key={idx} className="swara-card">
                                    <div className="swara-symbol">{note.swara}</div>
                                    <div className="lyric-text">{note.lyric}</div>
                                    {note.gamaka && <div style={{ fontSize: '0.7rem', color: 'var(--accent-pink)', marginTop: '0.2rem' }}>~{note.gamaka}</div>}
                                </div>
                            ))}
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'center' }}>
                            <audio controls src={`data:audio/wav;base64,${result.audio_base64}`} style={{ width: '100%' }} />
                        </div>
                    </div>
                )
            }

        </div >
    );
};

export default SongGenerator;
