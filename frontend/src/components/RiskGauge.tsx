import React from 'react';
import { ShieldAlert, ShieldCheck } from 'lucide-react';
import { SeverityLevel } from '../types';

interface RiskGaugeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({ score, size = 'md', showLabel = true }) => {
  const clampedScore = Math.max(0, Math.min(100, Math.round(score)));

  const getSeverity = (s: number): SeverityLevel => {
    if (s <= 30) return 'LOW';
    if (s <= 60) return 'MEDIUM';
    if (s <= 80) return 'HIGH';
    return 'CRITICAL';
  };

  const severity = getSeverity(clampedScore);

  const getColor = (sev: SeverityLevel) => {
    switch (sev) {
      case 'CRITICAL':
        return '#ef4444';
      case 'HIGH':
        return '#f59e0b';
      case 'MEDIUM':
        return '#3b82f6';
      case 'LOW':
      default:
        return '#10b981';
    }
  };

  const color = getColor(severity);

  const radius = size === 'lg' ? 48 : size === 'md' ? 36 : 24;
  const strokeWidth = size === 'lg' ? 8 : size === 'md' ? 6 : 4;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (clampedScore / 100) * circumference;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
      <div style={{ position: 'relative', width: radius * 2 + strokeWidth * 2, height: radius * 2 + strokeWidth * 2 }}>
        <svg
          width={radius * 2 + strokeWidth * 2}
          height={radius * 2 + strokeWidth * 2}
          style={{ transform: 'rotate(-90deg)' }}
        >
          {/* Background circle */}
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            stroke="rgba(30, 41, 59, 0.7)"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Progress circle */}
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            stroke={color}
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{
              transition: 'stroke-dashoffset 0.8s ease-in-out, stroke 0.4s ease',
              filter: `drop-shadow(0 0 6px ${color}88)`,
            }}
          />
        </svg>

        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span
            style={{
              fontSize: size === 'lg' ? '1.5rem' : size === 'md' ? '1.15rem' : '0.85rem',
              fontWeight: 800,
              fontFamily: 'var(--font-mono)',
              color: '#ffffff',
              lineHeight: 1,
            }}
          >
            {clampedScore}
          </span>
          <span
            style={{
              fontSize: size === 'lg' ? '0.65rem' : '0.55rem',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            /100
          </span>
        </div>
      </div>

      {showLabel && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {severity === 'CRITICAL' || severity === 'HIGH' ? (
              <ShieldAlert size={16} color={color} />
            ) : (
              <ShieldCheck size={16} color={color} />
            )}
            <span
              className={`badge-pill severity-${severity}`}
              style={{ fontSize: '0.72rem', padding: '2px 8px' }}
            >
              {severity}
            </span>
          </div>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
            Explainable Composite Risk
          </span>
        </div>
      )}
    </div>
  );
};
