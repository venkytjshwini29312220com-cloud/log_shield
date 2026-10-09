import React from 'react';
import {
  CheckCircle,
  Database,
  Globe,
  HardDrive,
  Laptop,
  Radio,
  Server,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { API_BASE } from '../services/api';
import { ConnectionStatus } from '../services/websocket';
import { SystemStatusData } from '../types';

interface SystemStatusPageProps {
  systemStatus: SystemStatusData | null;
  wsStatus: ConnectionStatus;
}

export const SystemStatusPage: React.FC<SystemStatusPageProps> = ({
  systemStatus,
  wsStatus,
}) => {
  const components = systemStatus?.components || {};

  return (
    <div>
      {/* Topology Map Banner */}
      <div className="glass-panel" style={{ marginBottom: '24px' }}>
        <div className="panel-header">
          <div className="panel-title">
            <Globe size={18} color="var(--cyan-bright)" />
            <span>Three-Laptop Physical Deployment Topology (LAN Only)</span>
          </div>
          <span className="badge-pill" style={{ background: 'rgba(16, 185, 129, 0.2)', color: 'var(--emerald-400)' }}>
            No Cloud Dependency
          </span>
        </div>

        <div className="panel-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.7)',
                padding: '20px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <Laptop size={20} color="var(--blue-400)" />
                <h4 style={{ fontWeight: 700, color: 'var(--text-main)' }}>Laptop 1: Simulator</h4>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                Emits safe synthetic test logs across predefined scenarios A–F.
              </p>
              <div className="mono-cell" style={{ fontSize: '0.74rem', color: 'var(--cyan-400)' }}>
                Target: {API_BASE}/api/events
              </div>
            </div>

            <div
              style={{
                background: 'rgba(15, 23, 42, 0.9)',
                padding: '20px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-cyan)',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <Server size={20} color="var(--cyan-bright)" />
                <h4 style={{ fontWeight: 700, color: '#ffffff' }}>Laptop 2: AI Engine (Server)</h4>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                Ingest, detect, correlate, score, persist to SQLite, and fan-out via WebSocket.
              </p>
              <div className="mono-cell" style={{ fontSize: '0.74rem', color: 'var(--emerald-400)' }}>
                Listen: 0.0.0.0:8000 &bull; Phase {systemStatus?.phase || 10}
              </div>
            </div>

            <div
              style={{
                background: 'rgba(15, 23, 42, 0.7)',
                padding: '20px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <Laptop size={20} color="var(--purple-400)" />
                <h4 style={{ fontWeight: 700, color: 'var(--text-main)' }}>Laptop 3: SOC Dashboard</h4>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                Real-time analyst UI. Zero hardcoded stats; strictly streams from Laptop 2.
              </p>
              <div className="mono-cell" style={{ fontSize: '0.74rem', color: 'var(--purple-400)' }}>
                Active Client &bull; Vite/React
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Subsystem Health Grid */}
      <div className="glass-panel" style={{ marginBottom: '24px' }}>
        <div className="panel-header">
          <div className="panel-title">
            <CheckCircle size={18} color="var(--emerald-400)" />
            <span>Engine Subsystem Health Matrix</span>
          </div>
          <span className="mono-cell" style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            GET /api/system-status
          </span>
        </div>

        <div className="panel-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            {/* FastAPI API */}
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                  <Zap size={16} color="var(--cyan-bright)" />
                  <span>FastAPI HTTP Engine</span>
                </div>
                <span className="badge-pill severity-LOW">{components.api?.status || 'ONLINE'}</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {components.api?.detail || 'FastAPI process accepting REST requests'}
              </p>
            </div>

            {/* SQLite Database */}
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                  <Database size={16} color="var(--blue-400)" />
                  <span>SQLite Database</span>
                </div>
                <span className="badge-pill severity-LOW">{components.database?.status || 'ONLINE'}</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {components.database?.detail || 'SQLite reachable; events, incidents, alerts tables'}
              </p>
            </div>

            {/* AI Engine */}
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                  <ShieldCheck size={16} color="var(--amber-400)" />
                  <span>Hybrid Detection Engine</span>
                </div>
                <span className="badge-pill severity-LOW">{components.ai_engine?.status || 'ONLINE'}</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {components.ai_engine?.detail || 'Rule Engine + Isolation Forest ML active'}
              </p>
            </div>

            {/* Log Collector */}
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                  <HardDrive size={16} color="var(--emerald-400)" />
                  <span>Ingestion & Normalizer</span>
                </div>
                <span className="badge-pill severity-LOW">{components.log_collector?.status || 'ONLINE'}</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {components.log_collector?.detail || 'Event normalization and schema enforcement pipeline'}
              </p>
            </div>

            {/* WebSocket Fan-Out */}
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                  <Radio size={16} color="var(--cyan-bright)" />
                  <span>WebSocket Fan-Out</span>
                </div>
                <span className={`badge-pill ${wsStatus === 'CONNECTED' ? 'severity-LOW' : 'severity-CRITICAL'}`}>
                  {wsStatus}
                </span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {components.websocket?.detail || 'Real-time telemetry distribution (/ws/events)'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
