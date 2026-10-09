import React, { useEffect, useState } from 'react';
import { RefreshCw, Clock, Globe } from 'lucide-react';
import { API_BASE } from '../services/api';

interface HeaderProps {
  title: string;
  subtitle: string;
  onRefresh: () => void;
  loading: boolean;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle, onRefresh, loading }) => {
  const [time, setTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="top-header">
      <div className="header-title">
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>

      <div className="header-actions">
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(15, 23, 42, 0.6)',
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.78rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-secondary)',
          }}
        >
          <Clock size={14} color="var(--cyan-400)" />
          <span>{time}</span>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(15, 23, 42, 0.6)',
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.78rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
          }}
          title="Laptop 2 Backend Host"
        >
          <Globe size={14} color="var(--blue-400)" />
          <span>{API_BASE}</span>
        </div>

        <button
          className="btn"
          onClick={onRefresh}
          disabled={loading}
          style={{ cursor: loading ? 'wait' : 'pointer' }}
        >
          <RefreshCw size={15} className={loading ? 'spin' : ''} />
          <span>Sync</span>
        </button>
      </div>
    </header>
  );
};
