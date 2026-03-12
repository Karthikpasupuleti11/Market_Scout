import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import './Header.css';

const PAGE_TITLES = {
    '/': 'Dashboard',
    '/run': 'Run Pipeline',
    '/reports': 'Reports',
    '/competitors': 'Competitors',
};

export default function Header() {
    const location = useLocation();
    const title = PAGE_TITLES[location.pathname] || 'Market Scout';
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        const checkConnection = async () => {
            try {
                // Ping the backend root, using 'no-cors' so the browser doesn't block the network request.
                // If the server is offline, fetch itself throws a TypeError. If it's online, it succeeds (opaque response).
                await fetch('http://localhost:8000/', { mode: 'no-cors' });
                setConnected(true);
            } catch (err) {
                setConnected(false);
            }
        };

        checkConnection();
        const interval = setInterval(checkConnection, 5000);
        return () => clearInterval(interval);
    }, []);

    return (
        <header className="header">
            <div className="header-left">
                <h2 className="header-title">{title}</h2>
            </div>
            <div className="header-right">
                <div className={`header-status ${!connected ? 'disconnected' : ''}`} style={!connected ? { backgroundColor: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)', color: '#EF4444' } : {}}>
                    <span
                        className="status-dot"
                        style={!connected ? { backgroundColor: '#EF4444', animation: 'none' } : {}}
                    />
                    <span className="status-text">
                        {connected ? 'Backend Connected' : 'Backend Offline'}
                    </span>
                </div>
            </div>
        </header>
    );
}
