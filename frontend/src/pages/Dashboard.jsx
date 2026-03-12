import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { HiOutlinePlay, HiOutlineDocumentText, HiOutlineUserGroup, HiOutlineShieldCheck, HiOutlineClock, HiOutlineSparkles } from 'react-icons/hi';
import { getCompetitors, getHealth } from '../api';
import './Dashboard.css';

const PIPELINE_NODES = [
    { label: 'Entry', title: 'Input Guardrails', sub: 'OWASP security validation' },
    { label: 'Orchestrator', title: 'Supervisor Agent', sub: 'Deterministic routing + LLM fallback' },
    { label: 'Agent 1', title: 'Research Agent', sub: 'Search, scrape, date filter' },
    { label: 'Agent 2', title: 'Analysis Agent', sub: 'Filter, extract, verify, score' },
    { label: 'Agent 3', title: 'Critic Agent', sub: 'Quality review + feedback' },
    { label: 'Agent 4', title: 'Synthesis Agent', sub: 'Report generation' },
    { label: 'Exit', title: 'Output Guardrail', sub: 'Report validation' },
];

export default function Dashboard() {
    const [competitors, setCompetitors] = useState([]);
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        async function load() {
            try {
                const [compData, healthData] = await Promise.all([
                    getCompetitors().catch(() => []),
                    getHealth().catch(() => null),
                ]);
                setCompetitors(compData);
                setHealth(healthData);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    return (
        <div className="fade-in">
            <div className="page-header">
                <h1>Intelligence Dashboard</h1>
                <p>Multi-agent competitive analysis powered by LangGraph & LLaMA 3.3</p>
            </div>

            {/* Stats */}
            <div className="stats-grid stagger">
                <div className="card stat-card fade-in">
                    <div className="stat-icon" style={{ background: 'rgba(255,90,36,0.1)', color: '#FF5A24' }}>
                        <HiOutlineUserGroup />
                    </div>
                    <div className="stat-info">
                        <h3>{loading ? '—' : competitors.length}</h3>
                        <p>Tracked Companies</p>
                    </div>
                </div>

                <div className="card stat-card fade-in">
                    <div className="stat-icon" style={{ background: 'rgba(16,185,129,0.1)', color: '#10B981' }}>
                        <HiOutlineShieldCheck />
                    </div>
                    <div className="stat-info">
                        {health ? (
                            <div className="status-inline">
                                <div className="pulse-dot" />
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color: 'var(--success)', fontWeight: 600 }}>Connected</span>
                            </div>
                        ) : (
                            <h3 style={{ fontSize: 15 }}>—</h3>
                        )}
                        <p>System Status</p>
                    </div>
                </div>

                <div className="card stat-card fade-in">
                    <div className="stat-icon" style={{ background: 'rgba(13,255,240,0.06)', color: '#0DFFF0' }}>
                        <HiOutlineSparkles />
                    </div>
                    <div className="stat-info">
                        <h3 className="small">LLaMA 3.3</h3>
                        <p>LLM Engine</p>
                    </div>
                </div>

                <div className="card stat-card fade-in">
                    <div className="stat-icon" style={{ background: 'rgba(245,158,11,0.1)', color: '#F59E0B' }}>
                        <HiOutlineClock />
                    </div>
                    <div className="stat-info">
                        <h3 className="small">7 Days</h3>
                        <p>Recency Window</p>
                    </div>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="actions-grid">
                <div className="card action-card fade-in" onClick={() => navigate('/run')}>
                    <div className="action-icon" style={{ background: 'rgba(255,90,36,0.1)', color: '#FF5A24' }}>
                        <HiOutlinePlay />
                    </div>
                    <div className="action-body">
                        <div className="action-title">Run Pipeline</div>
                        <div className="action-desc">Initiate the multi-agent pipeline to generate a comprehensive feature report.</div>
                    </div>
                    <span className="action-arrow">&rarr;</span>
                </div>

                <div className="card action-card green fade-in" onClick={() => navigate('/reports')}>
                    <div className="action-icon" style={{ background: 'rgba(16,185,129,0.1)', color: '#10B981' }}>
                        <HiOutlineDocumentText />
                    </div>
                    <div className="action-body">
                        <div className="action-title">View Reports</div>
                        <div className="action-desc">Browse past intelligence reports with confidence scores and cited sources.</div>
                    </div>
                    <span className="action-arrow">&rarr;</span>
                </div>

                <div className="card action-card amber fade-in" onClick={() => navigate('/competitors')}>
                    <div className="action-icon" style={{ background: 'rgba(245,158,11,0.1)', color: '#F59E0B' }}>
                        <HiOutlineUserGroup />
                    </div>
                    <div className="action-body">
                        <div className="action-title">Competitors</div>
                        <div className="action-desc">Track companies in your competitive landscape and add new targets.</div>
                    </div>
                    <span className="action-arrow">&rarr;</span>
                </div>
            </div>

            {/* Pipeline Architecture — Clean single flow */}
            <div className="card pipeline-card fade-in">
                <div className="section-header">
                    <span className="section-title">Pipeline Architecture</span>
                    <span className="section-sub">LangGraph multi-agent graph</span>
                </div>

                <div className="pipeline-flow">
                    {PIPELINE_NODES.map((node, i) => (
                        <div key={i} className="pipeline-flow-node">
                            <div className="flow-node">
                                <div className="flow-node-label">{node.label}</div>
                                <div className="flow-node-title">{node.title}</div>
                                <div className="flow-node-sub">{node.sub}</div>
                            </div>
                            {i < PIPELINE_NODES.length - 1 && (
                                <div className="flow-arrow">&rarr;</div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
