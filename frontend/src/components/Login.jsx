import { useState } from 'react';
import axios from 'axios';

const Login = ({ onLogin }) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        const params = new URLSearchParams();
        params.append('username', username.trim());
        params.append('password', password.trim());

        try {
            // Assuming Vite proxy handles /api -> http://127.0.0.1:8000
            const response = await axios.post('/api/token', params, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });
            onLogin(response.data.access_token);
        } catch (err) {
            console.error(err);
            if (err.code === "ERR_NETWORK") {
                setError('Cannot connect to server. Is the backend running?');
            } else {
                setError('Invalid credentials (try user/password123)');
            }
        }
    };

    return (
        <div className="glass-panel animate-fade-in" style={{ width: '100%', maxWidth: '400px', margin: 'auto' }}>
            <h2 style={{ textAlign: 'center', marginBottom: '2rem' }}>Musician Login</h2>
            <form onSubmit={handleSubmit}>
                <div>
                    <label>Username</label>
                    <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="Enter username"
                    />
                </div>
                <div>
                    <label>Password</label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Enter password"
                    />
                </div>
                {error && <p style={{ color: '#ff4081', fontSize: '0.9rem' }}>{error}</p>}
                <button type="submit" style={{ width: '100%', marginTop: '1rem' }}>Enter Studio</button>
            </form>
        </div>
    );
};

export default Login;
