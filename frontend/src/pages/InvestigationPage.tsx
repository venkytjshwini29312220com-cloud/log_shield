import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle,
  Clock,
  Cpu,
  FileText,
  Lock,
  MessageSquare,
  Send,
  Shield,
  ShieldAlert,
  Terminal,
  User,
} from 'lucide-react';
import { RiskGauge } from '../components/RiskGauge';
import { api } from '../services/api';
import { IncidentDetail, IncidentStatus, TimelineItem } from '../types';

interface InvestigationPageProps {
  incidentId: string | null;
  onBack: () => void;
  onRefresh: () => void;
}

export const InvestigationPage: React.FC<InvestigationPageProps> = ({
  incidentId,
  onBack,
  onRefresh,
}) => {
  const [detail, setDetail] = useState<IncidentDetail | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Status and Notes Form
  const [newStatus, setNewStatus] = useState<IncidentStatus>('NEW');
  const [analystNote, setAnalystNote] = useState('');
  const [analystName, setAnalystName] = useState('analyst_soc1');
  const [submittingNote, setSubmittingNote] = useState(false);

  useEffect(() => {
    if (!incidentId) return;

    const fetchDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const [incRes, timeRes] = await Promise.all([
          api.getIncident(incidentId),
          api.getIncidentTimeline(incidentId).catch(() => ({ items: [] })),
        ]);
        setDetail(incRes);
        setNewStatus(incRes.status);
        setTimeline(timeRes.items || []);
      } catch (err: any) {
        setError(err.message || 'Failed to load incident investigation details');
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [incidentId]);

  const handleUpdateStatus = async (status: IncidentStatus) => {
    if (!incidentId) return;
    try {
      const updated = await api.patchIncident(incidentId, {
        status,
        notes: `Analyst transitioned status to ${status}`,
        analyst: analystName,
      });
      setDetail(updated);
      setNewStatus(updated.status);
      onRefresh();
      // Refresh timeline
      api.getIncidentTimeline(incidentId).then((res) => setTimeline(res.items || [])).catch(() => {});
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!incidentId || !analystNote.trim()) return;
    setSubmittingNote(true);
    try {
      const updated = await api.addIncidentNote(incidentId, {
        note: analystNote.trim(),
        analyst: analystName,
      });
      setDetail(updated);
      setAnalystNote('');
      onRefresh();
      // Refresh timeline
      api.getIncidentTimeline(incidentId).then((res) => setTimeline(res.items || [])).catch(() => {});
    } catch (err: any) {
      alert(`Adding note failed: ${err.message}`);
    } finally {
      setSubmittingNote(false);
    }
  };

  if (!incidentId) {
    return (
      <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <FileText size={48} style={{ margin: '0 auto 16px', opacity: 0.3 }} />
        <h3 style={{ color: 'var(--text-main)', marginBottom: '8px' }}>No Incident Selected for Investigation</h3>
        <p style={{ fontSize: '0.85rem', marginBottom: '20px' }}>
          Select an incident from the Incidents or Overview page to inspect evidence, risk breakdown, and chronological timeline.
        </p>
        <button className="btn btn-primary" onClick={onBack}>
          <ArrowLeft size={15} />
          <span>Back to Incidents</span>
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--cyan-bright)' }}>
        <p>Loading incident evidence & timeline reconstruction for {incidentId}...</p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div style={{ padding: '40px 20px' }}>
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '20px', borderRadius: 'var(--radius-md)' }}>
          <p style={{ color: 'var(--rose-400)', fontWeight: 600 }}>Error loading incident: {error}</p>
          <button className="btn" style={{ marginTop: '12px' }} onClick={onBack}>
            <ArrowLeft size={14} /> Back
          </button>
        </div>
      </div>
    );
  }

  const riskData = detail.risk_breakdown || {};
  const components = riskData.components || {};
  const contributions = riskData.contributions || {};

  return (
    <div>
      {/* Investigation Top Navigation & Action Header */}
      <div
        className="glass-panel"
        style={{
          padding: '20px 24px',
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn" onClick={onBack} title="Return to incidents">
            <ArrowLeft size={16} />
            <span>Portfolio</span>
          </button>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffffff', fontFamily: 'var(--font-mono)' }}>
                {detail.incident_id}
              </h2>
              <span className={`badge-pill severity-${detail.severity}`}>{detail.severity}</span>
              <span className={`badge-pill status-${detail.status}`}>{detail.status}</span>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {detail.summary}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <RiskGauge score={detail.risk_score} size="md" showLabel={true} />

          {/* Quick Analyst Status Dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Status:</span>
            <select
              className="select-control"
              value={newStatus}
              onChange={(e) => handleUpdateStatus(e.target.value as IncidentStatus)}
            >
              <option value="NEW">NEW</option>
              <option value="INVESTIGATING">INVESTIGATING</option>
              <option value="CONTAINED">CONTAINED</option>
              <option value="RESOLVED">RESOLVED</option>
              <option value="FALSE_POSITIVE">FALSE POSITIVE</option>
            </select>
          </div>
        </div>
      </div>

      {/* Grid: Explanation & Defensive Recommendation */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
        <div className="glass-panel" style={{ margin: 0 }}>
          <div className="panel-header">
            <div className="panel-title">
              <ShieldAlert size={16} color="var(--amber-400)" />
              <span>Intrusion Explanation</span>
            </div>
          </div>
          <div className="panel-body">
            <p style={{ fontSize: '0.88rem', color: 'var(--text-main)', lineHeight: 1.6 }}>
              {detail.explanation}
            </p>
            <div style={{ marginTop: '14px', display: 'flex', gap: '16px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              <div>
                Target User: <strong style={{ color: 'var(--cyan-400)' }}>{detail.affected_user || 'N/A'}</strong>
              </div>
              <div>
                Source IP: <strong style={{ color: 'var(--cyan-400)' }}>{detail.source_ip || 'N/A'}</strong>
              </div>
              <div>
                Target Resource: <strong style={{ color: 'var(--cyan-400)' }}>{detail.resource || 'N/A'}</strong>
              </div>
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ margin: 0 }}>
          <div className="panel-header">
            <div className="panel-title">
              <Shield size={16} color="var(--emerald-400)" />
              <span>Recommended Defensive Action</span>
            </div>
          </div>
          <div className="panel-body">
            <p style={{ fontSize: '0.88rem', color: 'var(--emerald-400)', lineHeight: 1.6 }}>
              {detail.recommendation}
            </p>
            <div style={{ marginTop: '14px', display: 'flex', gap: '8px' }}>
              <button
                className="btn btn-primary"
                style={{ fontSize: '0.78rem' }}
                onClick={() => handleUpdateStatus('CONTAINED')}
              >
                <Lock size={13} />
                <span>Isolate / Contain</span>
              </button>
              <button
                className="btn"
                style={{ fontSize: '0.78rem' }}
                onClick={() => handleUpdateStatus('RESOLVED')}
              >
                <CheckCircle size={13} />
                <span>Mark Resolved</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Multi-Component Transparent Risk Breakdown */}
      <div className="glass-panel" style={{ marginBottom: '24px' }}>
        <div className="panel-header">
          <div className="panel-title">
            <Cpu size={18} color="var(--cyan-bright)" />
            <span>Explainable Risk Formula Breakdown (Score: {detail.risk_score}/100)</span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            risk = 100 * (0.30*rule + 0.30*ml + 0.25*corr + 0.15*beh)
          </span>
        </div>

        <div className="panel-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Rule Detection (30%)</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-main)', marginTop: '4px' }}>
                {components.rule_score ?? 0}
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>/100</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--cyan-400)', marginTop: '4px' }}>
                Contribution: <strong>+{contributions.rule_contribution ?? 0} pts</strong>
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Isolation Forest ML (30%)</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-main)', marginTop: '4px' }}>
                {components.ml_score ?? 0}
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>/100</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--cyan-400)', marginTop: '4px' }}>
                Contribution: <strong>+{contributions.ml_contribution ?? 0} pts</strong>
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Kill-Chain Correlation (25%)</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-main)', marginTop: '4px' }}>
                {components.correlation_score ?? 0}
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>/100</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--cyan-400)', marginTop: '4px' }}>
                Contribution: <strong>+{contributions.correlation_contribution ?? 0} pts</strong>
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Behavioral Context (15%)</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-main)', marginTop: '4px' }}>
                {components.behavioral_score ?? 0}
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>/100</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--cyan-400)', marginTop: '4px' }}>
                Contribution: <strong>+{contributions.behavioral_contribution ?? 0} pts</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Unified Chronological Timeline Reconstruction */}
      <div className="glass-panel" style={{ marginBottom: '24px' }}>
        <div className="panel-header">
          <div className="panel-title">
            <Clock size={18} color="var(--cyan-bright)" />
            <span>Chronological Incident Timeline Reconstruction ({timeline.length} items)</span>
          </div>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            Unifies Ingested Events &bull; Detection Alerts &bull; Analyst Audit History
          </span>
        </div>

        <div className="panel-body">
          {timeline.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px' }}>
              No timeline items recorded yet.
            </p>
          ) : (
            <div className="timeline-container">
              {timeline.map((item, idx) => (
                <div className="timeline-node" key={idx}>
                  <div
                    className="timeline-dot"
                    style={{
                      borderColor:
                        item.item_type === 'alert'
                          ? '#ef4444'
                          : item.item_type === 'audit'
                          ? '#a855f7'
                          : '#00f0ff',
                    }}
                  >
                    {item.item_type === 'alert' ? (
                      <AlertTriangle size={10} color="#ef4444" />
                    ) : item.item_type === 'audit' ? (
                      <User size={10} color="#a855f7" />
                    ) : (
                      <Terminal size={10} color="#00f0ff" />
                    )}
                  </div>

                  <div className="timeline-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span
                        className="badge-pill"
                        style={{
                          fontSize: '0.68rem',
                          background:
                            item.item_type === 'alert'
                              ? 'rgba(239, 68, 68, 0.2)'
                              : item.item_type === 'audit'
                              ? 'rgba(168, 85, 247, 0.2)'
                              : 'rgba(6, 182, 212, 0.2)',
                          color:
                            item.item_type === 'alert'
                              ? '#f87171'
                              : item.item_type === 'audit'
                              ? '#d8b4fe'
                              : 'var(--cyan-bright)',
                        }}
                      >
                        {item.item_type.toUpperCase()}
                      </span>
                      <span className="mono-cell" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {item.timestamp ? item.timestamp.replace('T', ' ').substring(0, 19) : ''}
                      </span>
                    </div>

                    <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.85rem' }}>
                      {item.title}
                    </div>

                    {item.details && (
                      <div style={{ marginTop: '6px', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                        {item.details.message && <p>{item.details.message}</p>}
                        {item.details.user && (
                          <span style={{ marginRight: '12px' }}>User: <strong style={{ color: 'var(--cyan-400)' }}>{item.details.user}</strong></span>
                        )}
                        {item.details.source_ip && (
                          <span style={{ marginRight: '12px' }}>IP: <strong style={{ color: 'var(--cyan-400)' }}>{item.details.source_ip}</strong></span>
                        )}
                        {item.details.analyst && (
                          <span>Analyst: <strong style={{ color: 'var(--purple-400)' }}>{item.details.analyst}</strong></span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Correlated Evidence Logs */}
      <div className="glass-panel" style={{ marginBottom: '24px' }}>
        <div className="panel-header">
          <div className="panel-title">
            <Terminal size={18} color="var(--cyan-bright)" />
            <span>Correlated Evidence Log Stream ({detail.events.length} events)</span>
          </div>
        </div>

        <div className="panel-body" style={{ padding: 0 }}>
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Timestamp</th>
                  <th>Source IP</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Status</th>
                  <th>Resource</th>
                </tr>
              </thead>
              <tbody>
                {detail.events.map((evt) => (
                  <tr key={evt.event_id}>
                    <td className="mono-cell" style={{ color: 'var(--cyan-bright)', fontWeight: 600 }}>{evt.event_id}</td>
                    <td className="mono-cell">{evt.timestamp ? evt.timestamp.replace('T', ' ').substring(0, 19) : ''}</td>
                    <td className="mono-cell">{evt.source_ip || '-'}</td>
                    <td>{evt.user || '-'}</td>
                    <td style={{ fontWeight: 600, color: evt.status === 'failure' || evt.status === 'denied' ? 'var(--rose-400)' : 'var(--text-main)' }}>
                      {evt.action}
                    </td>
                    <td>
                      <span className={`badge-pill ${evt.status === 'success' ? 'severity-LOW' : 'severity-CRITICAL'}`}>
                        {evt.status}
                      </span>
                    </td>
                    <td className="mono-cell">{evt.resource || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Operational Analyst Notes & Audit Form */}
      <div className="glass-panel">
        <div className="panel-header">
          <div className="panel-title">
            <MessageSquare size={18} color="var(--purple-400)" />
            <span>Analyst Investigation Notes & Operational Audit Log</span>
          </div>
        </div>

        <div className="panel-body">
          <form onSubmit={handleAddNote} style={{ marginBottom: '20px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr auto', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Analyst Handle
                </label>
                <input
                  type="text"
                  className="input-control"
                  style={{ width: '100%' }}
                  value={analystName}
                  onChange={(e) => setAnalystName(e.target.value)}
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Investigation Findings / Operational Containment Action
                </label>
                <input
                  type="text"
                  className="input-control"
                  style={{ width: '100%' }}
                  placeholder="e.g. Blocked egress port 4444 on host firewall, revoked AWS tokens..."
                  value={analystNote}
                  onChange={(e) => setAnalystNote(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                <button type="submit" className="btn btn-primary" disabled={submittingNote}>
                  <Send size={14} />
                  <span>{submittingNote ? 'Recording...' : 'Append Note'}</span>
                </button>
              </div>
            </div>
          </form>

          {/* Historical notes list */}
          {riskData.notes && riskData.notes.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {riskData.notes.map((n: any, idx: number) => (
                <div
                  key={idx}
                  style={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <span style={{ fontWeight: 600, color: 'var(--purple-400)', marginRight: '8px' }}>
                      @{n.analyst}:
                    </span>
                    <span style={{ color: 'var(--text-main)', fontSize: '0.85rem' }}>{n.note}</span>
                  </div>
                  <span className="mono-cell" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    {n.timestamp ? n.timestamp.replace('T', ' ').substring(0, 19) : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
