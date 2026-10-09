import React, { useState } from 'react';
import {
  Code,
  Database,
  Play,
  Search,
} from 'lucide-react';
import { api } from '../services/api';
import { LogEvent } from '../types';

export const LogExplorerPage: React.FC = () => {
  // Query Filters
  const [userQuery, setUserQuery] = useState('');
  const [ipQuery, setIpQuery] = useState('');
  const [typeQuery, setTypeQuery] = useState('');
  const [limit, setLimit] = useState(50);
  const [results, setResults] = useState<LogEvent[]>([]);
  const [totalFound, setTotalFound] = useState<number | null>(null);
  const [searching, setSearching] = useState(false);

  // Parse Preview Sandbox
  const [rawInput, setRawInput] = useState(
    'CEF:0|SecurityApp|AuthShield|1.0|LOGIN_FAIL|User authentication failed|8|src=10.0.0.41 dst=10.0.0.10 suser=jdoe app=https msg=bad_password'
  );
  const [parsedOutput, setParsedOutput] = useState<any>(null);
  const [parsing, setParsing] = useState(false);

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    setSearching(true);
    try {
      const res = await api.getEvents({
        user: userQuery.trim() || undefined,
        source_ip: ipQuery.trim() || undefined,
        event_type: typeQuery || undefined,
        limit,
      });
      setResults(res.items || []);
      setTotalFound(res.total || 0);
    } catch (err: any) {
      alert(`Query failed: ${err.message}`);
    } finally {
      setSearching(false);
    }
  };

  const handleTestParse = async () => {
    setParsing(true);
    try {
      let payload: any = rawInput;
      try {
        payload = JSON.parse(rawInput);
      } catch {
        // Raw string format (CEF, Syslog)
      }
      const res = await api.parseLogPreview(payload);
      setParsedOutput(res);
    } catch (err: any) {
      setParsedOutput({ error: err.message });
    } finally {
      setParsing(false);
    }
  };

  return (
    <div>
      {/* Historical Query Panel */}
      <div className="glass-panel" style={{ marginBottom: '24px' }}>
        <div className="panel-header">
          <div className="panel-title">
            <Database size={18} color="var(--cyan-bright)" />
            <span>SQLite Historical Log Query Engine</span>
          </div>
          <span className="mono-cell" style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            GET /api/events
          </span>
        </div>

        <div className="panel-body">
          <form onSubmit={handleQuery} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr)) auto', gap: '12px', alignItems: 'flex-end' }}>
            <div>
              <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Filter User
              </label>
              <input
                type="text"
                className="input-control"
                placeholder="e.g. jdoe, admin"
                value={userQuery}
                onChange={(e) => setUserQuery(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Filter Source IP
              </label>
              <input
                type="text"
                className="input-control"
                placeholder="e.g. 10.0.0.41"
                value={ipQuery}
                onChange={(e) => setIpQuery(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Event Type
              </label>
              <select
                className="select-control"
                value={typeQuery}
                onChange={(e) => setTypeQuery(e.target.value)}
                style={{ width: '100%' }}
              >
                <option value="">All Types</option>
                <option value="authentication">authentication</option>
                <option value="resource_access">resource_access</option>
                <option value="network">network</option>
                <option value="privilege_escalation">privilege_escalation</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Limit
              </label>
              <select
                className="select-control"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                style={{ width: '100%' }}
              >
                <option value={25}>25 items</option>
                <option value={50}>50 items</option>
                <option value={100}>100 items</option>
                <option value={500}>500 items</option>
              </select>
            </div>

            <div>
              <button type="submit" className="btn btn-primary" disabled={searching}>
                <Search size={14} />
                <span>{searching ? 'Querying...' : 'Query Logs'}</span>
              </button>
            </div>
          </form>

          {/* Results Table */}
          {totalFound !== null && (
            <div style={{ marginTop: '20px' }}>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
                Matched <strong>{totalFound}</strong> records in database. Displaying {results.length}.
              </div>

              <div className="data-table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Event ID</th>
                      <th>Timestamp</th>
                      <th>Source IP</th>
                      <th>User</th>
                      <th>Type</th>
                      <th>Action</th>
                      <th>Status</th>
                      <th>Resource</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.length === 0 ? (
                      <tr>
                        <td colSpan={8} style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                          No records matched search parameters.
                        </td>
                      </tr>
                    ) : (
                      results.map((r) => (
                        <tr key={r.event_id}>
                          <td className="mono-cell" style={{ color: 'var(--cyan-bright)' }}>{r.event_id}</td>
                          <td className="mono-cell">{r.timestamp ? r.timestamp.replace('T', ' ').substring(0, 19) : ''}</td>
                          <td className="mono-cell">{r.source_ip || '-'}</td>
                          <td>{r.user || '-'}</td>
                          <td><span className="badge-pill">{r.event_type}</span></td>
                          <td style={{ fontWeight: 600 }}>{r.action}</td>
                          <td>
                            <span className={`badge-pill ${r.status === 'success' ? 'severity-LOW' : 'severity-CRITICAL'}`}>
                              {r.status}
                            </span>
                          </td>
                          <td className="mono-cell">{r.resource || '-'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Parser Preview Sandbox */}
      <div className="glass-panel">
        <div className="panel-header">
          <div className="panel-title">
            <Code size={18} color="var(--purple-400)" />
            <span>Interactive Log Parser & Normalizer Sandbox</span>
          </div>
          <span className="mono-cell" style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            POST /api/events/parse
          </span>
        </div>

        <div className="panel-body">
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            Test log normalization in real-time without writing to SQLite. Supports raw CEF, syslog, or JSON payloads.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div>
              <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                Raw Log Payload (CEF / Syslog / JSON)
              </label>
              <textarea
                className="input-control"
                rows={7}
                style={{ width: '100%', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', resize: 'vertical' }}
                value={rawInput}
                onChange={(e) => setRawInput(e.target.value)}
              />
              <button
                className="btn btn-primary"
                style={{ marginTop: '10px' }}
                onClick={handleTestParse}
                disabled={parsing}
              >
                <Play size={14} />
                <span>{parsing ? 'Parsing...' : 'Simulate Parser'}</span>
              </button>
            </div>

            <div>
              <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                Normalized Schema Preview
              </label>
              <pre
                style={{
                  background: '#020617',
                  padding: '14px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.76rem',
                  color: 'var(--cyan-bright)',
                  maxHeight: '190px',
                  overflowY: 'auto',
                }}
              >
                {parsedOutput ? JSON.stringify(parsedOutput, null, 2) : '// Click "Simulate Parser" to inspect output'}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
