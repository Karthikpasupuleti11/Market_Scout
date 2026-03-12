import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { HiOutlineUserGroup, HiOutlinePlay } from 'react-icons/hi';
import { getCompetitors } from '../api';
import './Competitors.css';

const AVATAR_COLORS = ['#0EA5E9', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444', '#EC4899'];

export default function Competitors() {
    const [competitors, setCompetitors] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        async function load() {
            try {
                const data = await getCompetitors();
                setCompetitors(data);
            } catch {
                setCompetitors([]);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    return (
        <div className="fade-in">
            <div className="competitors-header">
                <div>
                    <div className="page-header" style={{ marginBottom: 0 }}>
                        <h1>Competitor Landscape</h1>
                        <p>Tracking {competitors.length} companies · Updated continuously</p>
                    </div>
                </div>
            </div>

            {loading && (
                <div className="card" style={{ textAlign: 'center', padding: 40 }}>
                    <div className="spinner spinner-lg" style={{ margin: '0 auto 12px' }} />
                    <p style={{ color: 'var(--muted)', fontSize: 13 }}>Loading competitors...</p>
                </div>
            )}

            {!loading && competitors.length === 0 && (
                <div className="empty-state">
                    <div className="icon"><HiOutlineUserGroup /></div>
                    <h3>No competitors tracked yet</h3>
                    <p>Run the intelligence pipeline on a company to start tracking them.</p>
                    <button
                        className="btn btn-primary"
                        style={{ marginTop: 16 }}
                        onClick={() => navigate('/run')}
                    >
                        <HiOutlinePlay /> Run Pipeline
                    </button>
                </div>
            )}

            {!loading && competitors.length > 0 && (
                <div className="comp-grid stagger">
                    {competitors.map((comp, i) => (
                        <div key={comp.id || i} className="card comp-card fade-in">
                            <div className="comp-header">
                                <div
                                    className="competitor-avatar"
                                    style={{ background: AVATAR_COLORS[i % AVATAR_COLORS.length] }}
                                >
                                    {(comp.name || '?').slice(0, 2).toUpperCase()}
                                </div>
                                <div>
                                    <div className="comp-name">{comp.name}</div>
                                    {comp.industry && <div className="comp-sector">{comp.industry}</div>}
                                    {comp.created_at && (
                                        <div className="competitor-date">
                                            Added {new Date(comp.created_at).toLocaleDateString()}
                                        </div>
                                    )}
                                </div>
                                <div style={{ marginLeft: 'auto' }}>
                                    <div className="pulse-dot" style={{ width: 7, height: 7 }} />
                                </div>
                            </div>
                            <div className="comp-actions">
                                <button className="comp-btn comp-btn-primary" onClick={() => navigate('/run')}>
                                    Run Pipeline
                                </button>
                                <button className="comp-btn comp-btn-ghost" onClick={() => navigate('/reports')}>
                                    View Reports
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
