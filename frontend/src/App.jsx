import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState } from 'react';
import Login from './components/Login';
import SongGenerator from './components/SongGenerator';

function App() {
    const [token, setToken] = useState(localStorage.getItem('token') || null);

    const handleLogin = (newToken) => {
        localStorage.setItem('token', newToken);
        setToken(newToken);
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        setToken(null);
    };

    return (
        <Router>
            <div className="app-container">
                <nav className="navbar">
                    <div className="logo"> Carnatic Music Generator</div>
                    {token && <button onClick={handleLogout} style={{ padding: '0.5rem 1rem', fontSize: '0.8rem' }}>Logout</button>}
                </nav>
                <div style={{ padding: '2rem', flex: 1, display: 'flex', justifyContent: 'center' }}>
                    <Routes>
                        <Route path="/login" element={!token ? <Login onLogin={handleLogin} /> : <Navigate to="/" />} />
                        <Route path="/" element={token ? <SongGenerator /> : <Navigate to="/login" />} />
                        <Route path="*" element={<Navigate to="/" />} />
                    </Routes>
                </div>
            </div>
        </Router>
    );
}

export default App;
