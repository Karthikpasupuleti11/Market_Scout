import { useState, useEffect, useRef } from 'react';
import { HiOutlinePlay, HiOutlineExternalLink, HiOutlineExclamationCircle, HiOutlineCheck } from 'react-icons/hi';
import { runPipeline } from '../api';
import './RunPipeline.css';

const PIPELINE_STEPS = [
    { num: '01', title: 'Input Guardrails', sub: 'OWASP security validation' },
    { num: '02', title: 'Supervisor Agent', sub: 'Deterministic routing + LLM fallback' },
    { num: '03', title: 'Research Agent', sub: 'Search → Scrape → Date filter → Self-review' },
    { num: '04', title: 'Analysis Agent', sub: 'Filter → Extract → Verify → Score' },
    { num: '05', title: 'Critic Agent', sub: 'Quality review + feedback loops' },
    { num: '06', title: 'Synthesis Agent', sub: 'Executive report generation' },
    { num: '07', title: 'Output Guardrail', sub: 'Report validation before delivery' },
];

export default function RunPipeline() {
    const [company, setCompany] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [activeStep, setActiveStep] = useState(-1);
    const [doneSteps, setDoneSteps] = useState([]);
    const intervalRef = useRef(null);

    useEffect(() => () => clearInterval(intervalRef.current), []);

    const handleRun = async (e) => {
        e.preventDefault();
        if (!company.trim()) return;
        setLoading(true);
        setError('');
        setResult(null);
        setActiveStep(0);
        setDoneSteps([]);

        // Animate pipeline steps
        let step = 0;
        intervalRef.current = setInterval(() => {
            setDoneSteps(d => [...d, step]);
            step++;
            setActiveStep(step);
            if (step >= PIPELINE_STEPS.length) {
                clearInterval(intervalRef.current);
            }
        }, 600);

        try {
            const data = await runPipeline(company.trim());
            setResult(data);
        } catch (err) {
            setError(err.message || 'Pipeline execution failed');
        } finally {
            clearInterval(intervalRef.current);
            setLoading(false);
            setActiveStep(-1);
            setDoneSteps(PIPELINE_STEPS.map((_, i) => i));
        }
    };

    const getStepState = (i) => {
        if (doneSteps.includes(i)) return 'done';
        if (activeStep === i) return 'active';
        return 'pending';
    };

    const report = result?.report || result;

    return (
        <div className="fade-in">
            <div className="pipeline-page">
                <div className="page-header">
                    <h1>Run Intelligence Pipeline</h1>
                    <p>Enter a company name to initiate the 11-node multi-agent analysis pipeline.</p>
                </div>

                <div className="status-badges">
                    <span className="badge ok"><HiOutlineCheck style={{ width: 10, height: 10 }} /> OWASP Guardrails Active</span>
                    <span className="badge info">LangGraph v0.2 · StateGraph</span>
                    <span className="badge ok">NVIDIA NIM · LLaMA 3.3-70B</span>
                    <span className="badge ok">Redis Cache · Connected</span>
                </div>

                <form onSubmit={handleRun}>
                    <div className="input-group">
                        <label className="input-label">Target Company</label>
                        <input
                            className="pipeline-input"
                            placeholder="e.g. Anthropic, OpenAI, Google DeepMind..."
                            value={company}
                            onChange={e => setCompany(e.target.value)}
                            disabled={loading}
                            maxLength={200}
                        />
                    </div>

                    <button type="submit" className="run-btn" disabled={loading || !company.trim()}>
                        {loading ? (
                            <><span className="spinner" style={{ width: 15, height: 15, borderWidth: 2 }} /> Analyzing {company}...</>
                        ) : (
                            <><HiOutlinePlay /> Run Pipeline</>
                        )}
                    </button>
                </form>

                {(loading || doneSteps.length > 0) && !result && !error && (
                    <div className="pipeline-progress">
                        <div className="progress-title">Execution Progress · {company}</div>
                        <div className="progress-steps">
                            {PIPELINE_STEPS.map((s, i) => {
                                const state = getStepState(i);
                                return (
                                    <div key={i} className={`progress-step ${state}`}>
                                        <div className={`step-indicator ${state}`}>
                                            {state === 'done' ? <HiOutlineCheck style={{ width: 12, height: 12 }} /> :
                                                state === 'active' ? <span className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} /> :
                                                    s.num}
                                        </div>
                                        <div className="step-name">{s.title}</div>
                                        <div className="step-desc">{s.sub}</div>
                                        {state === 'done' && <div className="step-time">✓</div>}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {error && (
                    <div className="card error-card">
                        <HiOutlineExclamationCircle className="error-icon" />
                        <div>
                            <h3>Pipeline Error</h3>
                            <p>{error}</p>
                        </div>
                    </div>
                )}

                {result && report && (
                    <div className="result-section">
                        <div className="card" style={{ padding: 20, borderColor: 'rgba(16,185,129,0.25)', background: 'rgba(16,185,129,0.05)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                                <HiOutlineCheck style={{ color: 'var(--success)', fontSize: '1.1rem' }} />
                                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--success)' }}>Pipeline Complete</span>
                            </div>
                            <p style={{ fontSize: 13, color: 'var(--muted)' }}>
                                Report for <strong style={{ color: 'var(--heading)' }}>{report.company_name || company}</strong> generated successfully.
                            </p>
                        </div>

                        <div className="card result-header">
                            <div className="result-meta">
                                <h2>{report.company_name || company}</h2>
                                <div className="result-badges">
                                    <span className="badge info">{report.total_features_verified || report.features?.length || 0} Features</span>
                                    <span className="badge ok">{report.total_sources_analysed || 0} Sources</span>
                                    {report.generated_at && (
                                        <span className="badge info" style={{ fontFamily: 'var(--font-mono)' }}>{new Date(report.generated_at).toLocaleString()}</span>
                                    )}
                                </div>
                            </div>
                        </div>

                        {report.executive_summary && (
                            <div className="card executive-summary">
                                <h3>Executive Summary</h3>
                                <p>{report.executive_summary}</p>
                            </div>
                        )}

                        {report.features && report.features.length > 0 && (
                            <div className="features-list">
                                <div className="section-title">
                                    🔬 Discovered Features
                                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--muted)', background: 'var(--elevated)', padding: '2px 8px', borderRadius: 4 }}>
                                        {report.features.length}
                                    </span>
                                </div>
                                {report.features.map((f, i) => (
                                    <div key={i} className="card feature-card">
                                        <div className="feature-header">
                                            <div className="feature-title-area">
                                                <h4>{f.title || f.feature_title || 'Untitled Feature'}</h4>
                                                {f.category && <span className="badge info">{f.category}</span>}
                                            </div>
                                            {f.confidence_score != null && (
                                                <div className={`confidence-badge ${f.confidence_score >= 0.7 ? 'high' : f.confidence_score >= 0.4 ? 'mid' : 'low'}`}>
                                                    {(f.confidence_score * 100).toFixed(0)}%
                                                </div>
                                            )}
                                        </div>
                                        <p className="feature-description">{f.description || f.feature_summary || ''}</p>
                                        <div className="feature-footer">
                                            {f.source_count && <span className="feature-meta">📊 {f.source_count} source{f.source_count > 1 ? 's' : ''}</span>}
                                            {f.key_metrics && f.key_metrics.length > 0 && (
                                                <div className="feature-metrics">
                                                    {f.key_metrics.map((m, j) => <span key={j} className="metric-tag">{m}</span>)}
                                                </div>
                                            )}
                                            {f.source_url && (
                                                <a href={f.source_url} target="_blank" rel="noopener noreferrer" className="source-link">
                                                    <HiOutlineExternalLink /> Source
                                                </a>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {report.all_sources && report.all_sources.length > 0 && (
                            <div className="card" style={{ padding: 20 }}>
                                <div className="sources-section">
                                    <h3>🔗 All Sources ({report.all_sources.length})</h3>
                                    <div className="sources-list">
                                        {report.all_sources.map((url, i) => (
                                            <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="source-item">
                                                <HiOutlineExternalLink /> {url.length > 80 ? url.slice(0, 80) + '...' : url}
                                            </a>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
