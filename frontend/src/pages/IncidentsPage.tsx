import React, { useState } from 'react';
import {
  AlertTriangle,
  ExternalLink,
  Filter,
  Search,
  ShieldAlert,
  User,
} from 'lucide-react';
import { api } from '../services/api';
import { Incident, IncidentStatus } from '../types';

interface IncidentsPageProps {
  incidents: Incident[];
  onSelectIncident: (incidentId: string) => void;
  onRefresh: () => void;
}

export const IncidentsPage: React.FC<IncidentsPageProps> = ({
  incidents,
  onSelectIncident,
  onRefresh,
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [search, setSearch] = useState<string>('');
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const filteredIncidents = incidents.filter((inc) => {
    if (statusFilter !== 'ALL' && inc.status !== statusFilter) return false;
    if (severityFilter !== 'ALL' && inc.severity !== severityFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      const match =
        inc.incident_id.toLowerCase().includes(q) ||
        (inc.affected_user && inc.affected_user.toLowerCase().includes(q)) ||
        (inc.source_ip && inc.source_ip.toLowerCase().includes(q)) ||
        (inc.summary && inc.summary.toLowerCase().includes(q));
      if (!match) return false;
    }
    return true;
  });

  const handleQuickStatusChange = async (incidentId: string, newStatus: IncidentStatus) => {
    try {
      setUpdatingId(incidentId);
      await api.patchIncident(incidentId, {
        status: newStatus,
        notes: `Analyst quick-updated status to ${newStatus}`,
      });
      onRefresh();
    } catch (err: any) {
      alert(`Failed to update incident: ${err.message}`);
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div>
      {/* Filtering Header */}
      <div className="glass-panel" style={{ marginBottom: '24px' }}>
        <div
          className="panel-body"
          style={{
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap', flex: 1 }}>
            <div style={{ position: 'relative', minWidth: '260px' }}>
              <Search
                size={15}
                style={{ position: 'absolute', left: '12px', top: '11px', color: 'var(--text-muted)' }}
              />
              <input
                type="text"
                className="input-control"
                placeholder="Search incident ID, user, IP, summary..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ paddingLeft: '34px', width: '100%' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Filter size={15} color="var(--text-muted)" />
              <select
                className="select-control"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="ALL">All Statuses</option>
                <option value="NEW">NEW</option>
                <option value="INVESTIGATING">INVESTIGATING</option>
                <option value="CONTAINED">CONTAINED</option>
                <option value="RESOLVED">RESOLVED</option>
                <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <select
                className="select-control"
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">CRITICAL (81-100)</option>
                <option value="HIGH">HIGH (61-80)</option>
                <option value="MEDIUM">MEDIUM (31-60)</option>
                <option value="LOW">LOW (0-30)</option>
              </select>
            </div>
          </div>

          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Showing <strong>{filteredIncidents.length}</strong> of <strong>{incidents.length}</strong> incidents
          </div>
        </div>
      </div>

      {/* Incidents Table */}
      <div className="glass-panel">
        <div className="panel-header">
          <div className="panel-title">
            <AlertTriangle size={18} color="var(--amber-400)" />
            <span>Correlated Incident Portfolio</span>
          </div>
        </div>

        <div className="panel-body" style={{ padding: 0 }}>
          {filteredIncidents.length === 0 ? (
            <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <ShieldAlert size={42} style={{ margin: '0 auto 16px', opacity: 0.3 }} />
              <p style={{ fontSize: '1rem', fontWeight: 600 }}>No incidents match the active filter</p>
              <p style={{ fontSize: '0.82rem' }}>Change status/severity filters or ingest new attack scenarios.</p>
            </div>
          ) : (
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID & Summary</th>
                    <th>Severity</th>
                    <th>Risk Score</th>
                    <th>Victim / Attacker</th>
                    <th>Status Lifecycle</th>
                    <th>Time Span</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredIncidents.map((inc) => (
                    <tr key={inc.incident_id}>
                      <td style={{ maxWidth: '280px' }}>
                        <div
                          style={{
                            fontWeight: 700,
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--cyan-bright)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                          }}
                        >
                          {inc.incident_id}
                        </div>
                        <div
                          style={{
                            fontSize: '0.78rem',
                            color: 'var(--text-main)',
                            marginTop: '2px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {inc.summary}
                        </div>
                      </td>

                      <td>
                        <span className={`badge-pill severity-${inc.severity}`}>
                          {inc.severity}
                        </span>
                      </td>

                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span
                            style={{
                              fontFamily: 'var(--font-mono)',
                              fontWeight: 700,
                              fontSize: '0.95rem',
                              color: inc.risk_score >= 81 ? '#f87171' : inc.risk_score >= 61 ? '#fbbf24' : 'var(--text-main)',
                            }}
                          >
                            {inc.risk_score}
                          </span>
                          <div style={{ width: '60px' }} className="risk-meter">
                            <div
                              className="risk-meter-fill"
                              style={{
                                width: `${inc.risk_score}%`,
                                background:
                                  inc.risk_score >= 81
                                    ? '#ef4444'
                                    : inc.risk_score >= 61
                                    ? '#f59e0b'
                                    : inc.risk_score >= 31
                                    ? '#3b82f6'
                                    : '#10b981',
                              }}
                            />
                          </div>
                        </div>
                      </td>

                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '0.78rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-main)', fontWeight: 500 }}>
                            <User size={13} color="var(--cyan-400)" />
                            <span>{inc.affected_user || 'unknown user'}</span>
                          </div>
                          <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.74rem' }}>
                            {inc.source_ip || 'IP unknown'}
                          </span>
                        </div>
                      </td>

                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span className={`badge-pill status-${inc.status}`}>
                            {inc.status}
                          </span>
                          <select
                            className="select-control"
                            style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                            value={inc.status}
                            disabled={updatingId === inc.incident_id}
                            onChange={(e) => handleQuickStatusChange(inc.incident_id, e.target.value as IncidentStatus)}
                          >
                            <option value="NEW">Set NEW</option>
                            <option value="INVESTIGATING">INVESTIGATING</option>
                            <option value="CONTAINED">CONTAINED</option>
                            <option value="RESOLVED">RESOLVED</option>
                            <option value="FALSE_POSITIVE">FALSE POSITIVE</option>
                          </select>
                        </div>
                      </td>

                      <td className="mono-cell" style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                        <div>{inc.created_at ? inc.created_at.substring(11, 19) : ''}</div>
                        <div>to {inc.last_seen ? inc.last_seen.substring(11, 19) : ''}</div>
                      </td>

                      <td>
                        <button
                          className="btn btn-primary"
                          style={{ padding: '5px 10px', fontSize: '0.75rem' }}
                          onClick={() => onSelectIncident(inc.incident_id)}
                        >
                          <span>Investigate</span>
                          <ExternalLink size={13} />
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
    </div>
  );
};
