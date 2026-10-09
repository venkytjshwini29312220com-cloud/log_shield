import React, { useState } from 'react';
import {
  Filter,
  Pause,
  Play,
  Radio,
  Search,
  Send,
  Trash2,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import { LogEvent } from '../types';

interface LiveEventsPageProps {
  events: LogEvent[];
}

export const LiveEventsPage: React.FC<LiveEventsPageProps> = ({ events }) => {
  const [isPaused, setIsPaused] = useState(false);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<LogEvent | null>(null);

  // Quick event emitter modal/form
  const [showEmitter, setShowEmitter] = useState(false);
  const [emitUser, setEmitUser] = useState('test_analyst');
  const [emitIp, setEmitIp] = useState('10.0.0.99');
  const [emitType, setEmitType] = useState('authentication');
  const [emitAction, setEmitAction] = useState('login_failed');
  const [emitStatus, setEmitStatus] = useState('failure');
  const [emitResource, setEmitResource] = useState('bastion-host');
  const [emitting, setEmitting] = useState(false);

  const filteredEvents = events.filter((e) => {
    if (typeFilter && e.event_type !== typeFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      const match =
        (e.user && e.user.toLowerCase().includes(q)) ||
        (e.source_ip && e.source_ip.toLowerCase().includes(q)) ||
        (e.action && e.action.toLowerCase().includes(q)) ||
        (e.resource && e.resource.toLowerCase().includes(q)) ||
        (e.event_id && e.event_id.toLowerCase().includes(q));
      if (!match) return false;
    }
    return true;
  });

  const handleEmitEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmitting(true);
    try {
      await api.ingestEvent({
        timestamp: new Date().toISOString(),
        user: emitUser,
        source_ip: emitIp,
        event_type: emitType,
        action: emitAction,
        status: emitStatus,
        resource: emitResource,
        protocol: 'https',
      });
      setShowEmitter(false);
    } catch (err: any) {
      alert(`Error emitting test event: ${err.message}`);
    } finally {
      setEmitting(false);
    }
  };

  return (
    <div>
      {/* Controls Bar */}
      <div className="glass-panel" style={{ marginBottom: '20px' }}>
        <div className="panel-body" style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', flex: 1 }}>
            <div style={{ position: 'relative', minWidth: '240px' }}>
              <Search size={15} style={{ position: 'absolute', left: '12px', top: '11px', color: 'var(--text-muted)' }} />
              <input
                type="text"
                className="input-control"
                placeholder="Filter user, IP, action, ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ paddingLeft: '34px', width: '100%' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Filter size={15} color="var(--text-muted)" />
              <select
                className="select-control"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                <option value="">All Event Types</option>
                <option value="authentication">Authentication</option>
                <option value="resource_access">Resource Access</option>
                <option value="network">Network</option>
                <option value="privilege_escalation">Privilege Escalation</option>
                <option value="system">System</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              className={`btn ${isPaused ? 'btn-primary' : ''}`}
              onClick={() => setIsPaused(!isPaused)}
            >
              {isPaused ? <Play size={14} /> : <Pause size={14} />}
              <span>{isPaused ? 'Resume Stream' : 'Pause Stream'}</span>
            </button>

            <button
              className="btn btn-primary"
              onClick={() => setShowEmitter(true)}
            >
              <Send size={14} />
              <span>Inject Test Log</span>
            </button>
          </div>
        </div>
      </div>

      {/* Live Stream Terminal Table */}
      <div className="glass-panel">
        <div className="panel-header">
          <div className="panel-title">
            <Radio size={18} color="var(--cyan-bright)" />
            <span>Streaming Live Event Feed ({filteredEvents.length} frames)</span>
          </div>
          {isPaused && (
            <span className="badge-pill" style={{ background: 'rgba(245, 158, 11, 0.2)', color: 'var(--amber-400)', border: '1px solid rgba(245, 158, 11, 0.4)' }}>
              Stream Paused
            </span>
          )}
        </div>

        <div className="panel-body" style={{ padding: 0 }}>
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Timestamp (UTC)</th>
                  <th>Source IP</th>
                  <th>User</th>
                  <th>Type</th>
                  <th>Action</th>
                  <th>Status</th>
                  <th>Resource</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {filteredEvents.length === 0 ? (
                  <tr>
                    <td colSpan={9} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                      No events matching current filter criteria.
                    </td>
                  </tr>
                ) : (
                  filteredEvents.map((evt) => (
                    <tr
                      key={evt.event_id}
                      style={{ cursor: 'pointer' }}
                      onClick={() => setSelectedEvent(evt)}
                    >
                      <td className="mono-cell" style={{ color: 'var(--cyan-bright)', fontWeight: 600 }}>
                        {evt.event_id}
                      </td>
                      <td className="mono-cell" style={{ color: 'var(--text-muted)' }}>
                        {evt.timestamp ? evt.timestamp.replace('T', ' ').substring(0, 19) : ''}
                      </td>
                      <td className="mono-cell">{evt.source_ip || '-'}</td>
                      <td style={{ fontWeight: 500, color: 'var(--text-main)' }}>
                        {evt.user || '-'}
                      </td>
                      <td>
                        <span className="badge-pill" style={{ background: 'rgba(15, 23, 42, 0.8)', color: 'var(--text-secondary)' }}>
                          {evt.event_type}
                        </span>
                      </td>
                      <td style={{ fontWeight: 600, color: evt.status === 'failure' || evt.status === 'denied' ? 'var(--rose-400)' : 'var(--text-main)' }}>
                        {evt.action}
                      </td>
                      <td>
                        <span
                          className={`badge-pill ${
                            evt.status === 'success'
                              ? 'severity-LOW'
                              : evt.status === 'failure' || evt.status === 'denied'
                              ? 'severity-CRITICAL'
                              : 'status-NEW'
                          }`}
                        >
                          {evt.status || 'unknown'}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
                        {evt.resource || '-'}
                      </td>
                      <td>
                        <button
                          className="btn"
                          style={{ padding: '2px 8px', fontSize: '0.7rem' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedEvent(evt);
                          }}
                        >
                          JSON
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Event Details Modal */}
      {selectedEvent && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(4, 7, 17, 0.75)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '20px',
          }}
          onClick={() => setSelectedEvent(null)}
        >
          <div
            className="glass-panel"
            style={{ width: '100%', maxWidth: '650px', maxHeight: '85vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="panel-header">
              <div className="panel-title">
                <span>Event Telemetry Inspector: {selectedEvent.event_id}</span>
              </div>
              <button className="btn" style={{ padding: '4px 8px' }} onClick={() => setSelectedEvent(null)}>
                <X size={16} />
              </button>
            </div>
            <div className="panel-body" style={{ overflowY: 'auto' }}>
              <pre
                style={{
                  background: '#020617',
                  padding: '16px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.8rem',
                  color: 'var(--cyan-400)',
                  overflowX: 'auto',
                }}
              >
                {JSON.stringify(selectedEvent, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Inject Test Event Modal */}
      {showEmitter && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(4, 7, 17, 0.75)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '20px',
          }}
          onClick={() => setShowEmitter(false)}
        >
          <div
            className="glass-panel"
            style={{ width: '100%', maxWidth: '520px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="panel-header">
              <div className="panel-title">
                <Send size={18} color="var(--cyan-bright)" />
                <span>Inject Synthetic Event (Laptop 1 Simulator)</span>
              </div>
              <button className="btn" style={{ padding: '4px 8px' }} onClick={() => setShowEmitter(false)}>
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleEmitEvent} className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                  Target User
                </label>
                <input
                  type="text"
                  className="input-control"
                  style={{ width: '100%' }}
                  value={emitUser}
                  onChange={(e) => setEmitUser(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                    Source IP
                  </label>
                  <input
                    type="text"
                    className="input-control"
                    style={{ width: '100%' }}
                    value={emitIp}
                    onChange={(e) => setEmitIp(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                    Resource Target
                  </label>
                  <input
                    type="text"
                    className="input-control"
                    style={{ width: '100%' }}
                    value={emitResource}
                    onChange={(e) => setEmitResource(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                    Event Type
                  </label>
                  <select
                    className="select-control"
                    style={{ width: '100%' }}
                    value={emitType}
                    onChange={(e) => setEmitType(e.target.value)}
                  >
                    <option value="authentication">authentication</option>
                    <option value="resource_access">resource_access</option>
                    <option value="network">network</option>
                    <option value="privilege_escalation">privilege_escalation</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                    Action
                  </label>
                  <input
                    type="text"
                    className="input-control"
                    style={{ width: '100%' }}
                    value={emitAction}
                    onChange={(e) => setEmitAction(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button type="button" className="btn" onClick={() => setShowEmitter(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={emitting}>
                  {emitting ? 'Injecting...' : 'Transmit Event'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
