import React from 'react';
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  Database,
  ExternalLink,
  Radio,
  Server,
  ShieldAlert,
  User,
} from 'lucide-react';
import { RiskGauge } from '../components/RiskGauge';
import { Incident, LogEvent, SystemStatistics, SystemStatusData } from '../types';

interface OverviewPageProps {
  statistics: SystemStatistics;
  incidents: Incident[];
  liveEvents: LogEvent[];
  systemStatus: SystemStatusData | null;
  onSelectIncident: (incidentId: string) => void;
  onNavigateTab: (tab: any) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  statistics,
  incidents,
  liveEvents,
  systemStatus,
  onSelectIncident,
  onNavigateTab,
}) => {
  const activeIncidents = incidents.filter(
    (i) => i.status === 'NEW' || i.status === 'INVESTIGATING' || i.status === 'CONTAINED'
  );

  return (
    <div>
      {/* Three-Laptop Architecture Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(6, 182, 212, 0.08))',
          border: '1px solid var(--border-cyan)',
          borderRadius: 'var(--radius-md)',
          padding: '16px 20px',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(6, 182, 212, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--cyan-bright)',
            }}
          >
            <Server size={22} />
          </div>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>
              Three-Laptop SOC Topology Active
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Laptop 1 (Simulator) &rarr; Laptop 2 (AI Engine @ {systemStatus?.public_base_url || '127.0.0.1:8000'}) &rarr; Laptop 3 (SOC Dashboard)
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <span className="badge-pill" style={{ background: 'rgba(16, 185, 129, 0.2)', color: 'var(--emerald-400)', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
            Engine: {systemStatus?.system || 'ONLINE'}
          </span>
          <span className="badge-pill" style={{ background: 'rgba(6, 182, 212, 0.2)', color: 'var(--cyan-bright)', border: '1px solid var(--border-cyan)' }}>
            ML: {systemStatus?.ml_model || 'Isolation Forest'}
          </span>
          <span className="badge-pill" style={{ background: 'rgba(99, 102, 241, 0.2)', color: 'var(--blue-400)', border: '1px solid rgba(99, 102, 241, 0.4)' }}>
            Window: {systemStatus?.correlation_window_seconds || 300}s
          </span>
        </div>
      </div>

      {/* 5 Real-Time Telemetry Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-header">
            <span>Total Log Events</span>
            <div className="stat-icon" style={{ color: 'var(--cyan-400)' }}>
              <Database size={18} />
            </div>
          </div>
          <div className="stat-value">{statistics.total_events.toLocaleString()}</div>
          <div className="stat-footer">
            <span style={{ color: 'var(--emerald-400)', fontWeight: 600 }}>Streaming</span> via SQLite & WS
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span>Threats Detected</span>
            <div className="stat-icon" style={{ color: 'var(--amber-400)' }}>
              <ShieldAlert size={18} />
            </div>
          </div>
          <div className="stat-value" style={{ color: statistics.threats_detected > 0 ? 'var(--amber-400)' : 'inherit' }}>
            {statistics.threats_detected}
          </div>
          <div className="stat-footer">
            Rules & Isolation Forest ML
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span>Active Incidents</span>
            <div className="stat-icon" style={{ color: 'var(--blue-400)' }}>
              <AlertTriangle size={18} />
            </div>
          </div>
          <div className="stat-value" style={{ color: statistics.active_incidents > 0 ? 'var(--blue-400)' : 'inherit' }}>
            {statistics.active_incidents}
          </div>
          <div className="stat-footer">
            Correlated open kill-chains
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span>Critical Incidents</span>
            <div className="stat-icon" style={{ color: 'var(--rose-400)' }}>
              <AlertOctagon size={18} />
            </div>
          </div>
          <div className="stat-value" style={{ color: statistics.critical_incidents > 0 ? 'var(--rose-400)' : 'inherit' }}>
            {statistics.critical_incidents}
          </div>
          <div className="stat-footer">
            Urgent analyst triage required
          </div>
        </div>

        <div className="stat-card" style={{ gridColumn: 'span 1' }}>
          <div className="stat-header">
            <span>Current Risk Score</span>
            <div className="stat-icon" style={{ color: 'var(--purple-400)' }}>
              <Activity size={18} />
            </div>
          </div>
          <div style={{ marginTop: '2px' }}>
            <RiskGauge score={statistics.current_risk} size="sm" showLabel={true} />
          </div>
          <div className="stat-footer" style={{ marginTop: '12px' }}>
            Computed 0–100 (never probabilities)
          </div>
        </div>
      </div>

      {/* Split View: Active Incidents & Live Telemetry Stream */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)', gap: '24px' }}>
        {/* Left: Active Incidents */}
        <div className="glass-panel">
          <div className="panel-header">
            <div className="panel-title">
              <AlertTriangle size={18} color="var(--amber-400)" />
              <span>Correlated Incidents ({activeIncidents.length})</span>
            </div>
            <button
              className="btn"
              style={{ fontSize: '0.76rem', padding: '5px 10px' }}
              onClick={() => onNavigateTab('incidents')}
            >
              <span>View All</span>
              <ArrowRight size={14} />
            </button>
          </div>

          <div className="panel-body" style={{ padding: 0 }}>
            {activeIncidents.length === 0 ? (
              <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <ShieldAlert size={36} style={{ margin: '0 auto 12px', opacity: 0.3 }} />
                <p style={{ fontSize: '0.9rem', fontWeight: 600 }}>No active security incidents</p>
                <p style={{ fontSize: '0.78rem' }}>Run simulator scenarios A–F to populate live incidents.</p>
              </div>
            ) : (
              <div className="data-table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Incident</th>
                      <th>Severity</th>
                      <th>Risk</th>
                      <th>Entity</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeIncidents.slice(0, 6).map((inc) => (
                      <tr key={inc.incident_id}>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
                            {inc.incident_id}
                          </div>
                          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {inc.summary}
                          </div>
                        </td>
                        <td>
                          <span className={`badge-pill severity-${inc.severity}`}>
                            {inc.severity}
                          </span>
                        </td>
                        <td>
                          <span style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
                            {inc.risk_score}/100
                          </span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.78rem' }}>
                            <User size={13} color="var(--cyan-400)" />
                            <span>{inc.affected_user || inc.source_ip || 'N/A'}</span>
                          </div>
                        </td>
                        <td>
                          <span className={`badge-pill status-${inc.status}`}>
                            {inc.status}
                          </span>
                        </td>
                        <td>
                          <button
                            className="btn btn-primary"
                            style={{ padding: '4px 8px', fontSize: '0.72rem' }}
                            onClick={() => onSelectIncident(inc.incident_id)}
                          >
                            <span>Investigate</span>
                            <ExternalLink size={12} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right: Live Telemetry Event Stream */}
        <div className="glass-panel">
          <div className="panel-header">
            <div className="panel-title">
              <Radio size={18} color="var(--cyan-bright)" />
              <span>Live Ingest Stream ({liveEvents.length})</span>
            </div>
            <button
              className="btn"
              style={{ fontSize: '0.76rem', padding: '5px 10px' }}
              onClick={() => onNavigateTab('events')}
            >
              <span>Full Stream</span>
              <ArrowRight size={14} />
            </button>
          </div>

          <div className="panel-body" style={{ padding: 0 }}>
            <div className="terminal-window" style={{ border: 'none', borderRadius: 0 }}>
              <div className="terminal-header">
                <div className="terminal-dots">
                  <span className="terminal-dot" style={{ background: '#ef4444' }} />
                  <span className="terminal-dot" style={{ background: '#f59e0b' }} />
                  <span className="terminal-dot" style={{ background: '#10b981' }} />
                </div>
                <span>/ws/events tail -f</span>
              </div>

              <div className="terminal-body" style={{ maxHeight: '340px' }}>
                {liveEvents.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    Listening for incoming events from Laptop 1...
                  </div>
                ) : (
                  liveEvents.slice(0, 15).map((evt, idx) => (
                    <div className="log-row" key={evt.event_id || idx}>
                      <span className="log-time">
                        {evt.timestamp ? evt.timestamp.substring(11, 19) : '00:00:00'}
                      </span>
                      <span style={{ color: 'var(--text-muted)' }}>[{evt.source_ip || 'local'}]</span>
                      <span style={{ color: 'var(--blue-400)', fontWeight: 500 }}>
                        {evt.user || 'system'}:
                      </span>
                      <span className={`log-action ${evt.status === 'failure' || evt.status === 'denied' ? 'log-fail' : 'log-success'}`}>
                        {evt.action}
                      </span>
                      {evt.resource && (
                        <span style={{ color: 'var(--text-muted)' }}>&rarr; {evt.resource}</span>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
