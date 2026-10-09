import React from 'react';
import {
  ShieldAlert,
  Activity,
  AlertTriangle,
  Search,
  Sliders,
  Server,
  FileText,
  Radio,
} from 'lucide-react';
import { ConnectionStatus } from '../services/websocket';

export type NavTab = 'overview' | 'events' | 'incidents' | 'investigation' | 'analytics' | 'explorer' | 'status';

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  activeIncidentsCount: number;
  wsStatus: ConnectionStatus;
  selectedIncidentId: string | null;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  activeIncidentsCount,
  wsStatus,
  selectedIncidentId,
}) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-icon">
          <ShieldAlert size={22} />
        </div>
        <div className="brand-text">
          <h1>LogShield</h1>
          <span>SOC AI Engine • Laptop 3</span>
        </div>
      </div>

      <ul className="nav-links">
        <li
          className={`nav-item ${currentTab === 'overview' ? 'active' : ''}`}
          onClick={() => onSelectTab('overview')}
        >
          <Activity size={18} />
          <span>Overview</span>
        </li>

        <li
          className={`nav-item ${currentTab === 'events' ? 'active' : ''}`}
          onClick={() => onSelectTab('events')}
        >
          <Radio size={18} />
          <span>Live Events</span>
          <span className="badge" style={{ background: 'rgba(6, 182, 212, 0.15)', color: 'var(--cyan-bright)' }}>
            Live
          </span>
        </li>

        <li
          className={`nav-item ${currentTab === 'incidents' ? 'active' : ''}`}
          onClick={() => onSelectTab('incidents')}
        >
          <AlertTriangle size={18} />
          <span>Incidents</span>
          {activeIncidentsCount > 0 && (
            <span className="badge badge-alert">{activeIncidentsCount}</span>
          )}
        </li>

        <li
          className={`nav-item ${currentTab === 'investigation' ? 'active' : ''}`}
          onClick={() => onSelectTab('investigation')}
        >
          <FileText size={18} />
          <span>Investigation</span>
          {selectedIncidentId && (
            <span className="badge" style={{ background: 'rgba(99, 102, 241, 0.2)', color: 'var(--blue-400)' }}>
              {selectedIncidentId}
            </span>
          )}
        </li>

        <li
          className={`nav-item ${currentTab === 'analytics' ? 'active' : ''}`}
          onClick={() => onSelectTab('analytics')}
        >
          <Sliders size={18} />
          <span>Threat Analytics</span>
        </li>

        <li
          className={`nav-item ${currentTab === 'explorer' ? 'active' : ''}`}
          onClick={() => onSelectTab('explorer')}
        >
          <Search size={18} />
          <span>Log Explorer</span>
        </li>

        <li
          className={`nav-item ${currentTab === 'status' ? 'active' : ''}`}
          onClick={() => onSelectTab('status')}
        >
          <Server size={18} />
          <span>System Status</span>
        </li>
      </ul>

      <div className="sidebar-footer">
        <div className="ws-status-badge">
          <div
            className={`status-dot ${
              wsStatus === 'CONNECTED'
                ? 'connected'
                : wsStatus === 'CONNECTING'
                ? 'connecting'
                : 'disconnected'
            }`}
          />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.78rem' }}>
              {wsStatus === 'CONNECTED'
                ? 'WebSocket Stream Live'
                : wsStatus === 'CONNECTING'
                ? 'Connecting to WS...'
                : 'WS Disconnected'}
            </span>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
              /ws/events fan-out
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
};
