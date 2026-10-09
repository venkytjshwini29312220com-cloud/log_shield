import React, { useEffect, useState } from 'react';
import { Sliders } from 'lucide-react';
import { RiskGauge } from '../components/RiskGauge';
import { api } from '../services/api';
import { Incident } from '../types';

interface AnalyticsPageProps {
  incidents: Incident[];
}

export const AnalyticsPage: React.FC<AnalyticsPageProps> = ({ incidents }) => {
  // Simulator State
  const [ruleScore, setRuleScore] = useState(85);
  const [mlScore, setMlScore] = useState(75);
  const [corrScore, setCorrScore] = useState(90);
  const [behScore, setBehScore] = useState(80);
  const [simResult, setSimResult] = useState<any>(null);

  // Severity counts
  const criticalCount = incidents.filter((i) => i.severity === 'CRITICAL').length;
  const highCount = incidents.filter((i) => i.severity === 'HIGH').length;
  const mediumCount = incidents.filter((i) => i.severity === 'MEDIUM').length;
  const lowCount = incidents.filter((i) => i.severity === 'LOW').length;

  const triggerCalculate = async () => {
    try {
      const res = await api.calculateRisk({
        rule_score: ruleScore,
        ml_score: mlScore,
        correlation_score: corrScore,
        behavioral_score: behScore,
      });
      setSimResult(res);
    } catch (err: any) {
      console.error('Calculation error:', err);
    }
  };

  useEffect(() => {
    triggerCalculate();
  }, [ruleScore, mlScore, corrScore, behScore]);

  return (
    <div>
      {/* Top Threat Metrics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '18px', marginBottom: '24px' }}>
        <div className="stat-card" style={{ borderLeft: '3px solid #ef4444' }}>
          <div className="stat-header">
            <span>Critical Severity (81–100)</span>
          </div>
          <div className="stat-value" style={{ color: '#f87171' }}>{criticalCount}</div>
          <div className="stat-footer">Immediate kill-chain action</div>
        </div>

        <div className="stat-card" style={{ borderLeft: '3px solid #f59e0b' }}>
          <div className="stat-header">
            <span>High Severity (61–80)</span>
          </div>
          <div className="stat-value" style={{ color: '#fbbf24' }}>{highCount}</div>
          <div className="stat-footer">Priority SOC analyst triage</div>
        </div>

        <div className="stat-card" style={{ borderLeft: '3px solid #3b82f6' }}>
          <div className="stat-header">
            <span>Medium Severity (31–60)</span>
          </div>
          <div className="stat-value" style={{ color: '#60a5fa' }}>{mediumCount}</div>
          <div className="stat-footer">Suspicious anomaly monitor</div>
        </div>

        <div className="stat-card" style={{ borderLeft: '3px solid #10b981' }}>
          <div className="stat-header">
            <span>Low Severity (0–30)</span>
          </div>
          <div className="stat-value" style={{ color: '#34d399' }}>{lowCount}</div>
          <div className="stat-footer">Routine audit telemetry</div>
        </div>
      </div>

      {/* Interactive Risk Formula Weight Simulator */}
      <div className="glass-panel">
        <div className="panel-header">
          <div className="panel-title">
            <Sliders size={18} color="var(--cyan-bright)" />
            <span>Explainable Risk Formula Calibration Simulator</span>
          </div>
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            POST /api/risk/calculate
          </span>
        </div>

        <div className="panel-body">
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
            Tune the four input component scores below to simulate the exact composite risk and transparent mathematical contribution points computed by the engine.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '30px', alignItems: 'center' }}>
            {/* Sliders */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>Rule-Based Detection (30% weight)</span>
                  <span className="mono-cell" style={{ color: 'var(--cyan-bright)' }}>{ruleScore}/100</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={ruleScore}
                  onChange={(e) => setRuleScore(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--cyan-500)' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>Isolation Forest ML Anomaly (30% weight)</span>
                  <span className="mono-cell" style={{ color: 'var(--cyan-bright)' }}>{mlScore}/100</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={mlScore}
                  onChange={(e) => setMlScore(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--cyan-500)' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>Kill-Chain Correlation (25% weight)</span>
                  <span className="mono-cell" style={{ color: 'var(--cyan-bright)' }}>{corrScore}/100</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={corrScore}
                  onChange={(e) => setCorrScore(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--cyan-500)' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>Behavioral Context (15% weight)</span>
                  <span className="mono-cell" style={{ color: 'var(--cyan-bright)' }}>{behScore}/100</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={behScore}
                  onChange={(e) => setBehScore(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--cyan-500)' }}
                />
              </div>
            </div>

            {/* Simulated Result Card */}
            {simResult && (
              <div
                style={{
                  background: 'rgba(15, 23, 42, 0.8)',
                  padding: '24px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-cyan)',
                  boxShadow: 'var(--shadow-card)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                }}
              >
                <RiskGauge score={simResult.composite_score} size="lg" showLabel={true} />

                <div style={{ width: '100%', marginTop: '20px', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px', fontSize: '0.78rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Rule Contribution:</span>
                    <strong style={{ color: 'var(--cyan-bright)' }}>+{simResult.contributions?.rule_contribution} pts</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>ML Anomaly Contribution:</span>
                    <strong style={{ color: 'var(--cyan-bright)' }}>+{simResult.contributions?.ml_contribution} pts</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Kill-Chain Contribution:</span>
                    <strong style={{ color: 'var(--cyan-bright)' }}>+{simResult.contributions?.correlation_contribution} pts</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Behavioral Contribution:</span>
                    <strong style={{ color: 'var(--cyan-bright)' }}>+{simResult.contributions?.behavioral_contribution} pts</strong>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
