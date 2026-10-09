import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import { wsClient } from '../services/websocket';
import { Incident, LogEvent, SystemStatistics, SystemStatusData, WebSocketMessage } from '../types';

export function useSOCData() {
  const [statistics, setStatistics] = useState<SystemStatistics>({
    total_events: 0,
    threats_detected: 0,
    active_incidents: 0,
    critical_incidents: 0,
    current_risk: 0,
    source: 'loading',
  });
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [liveEvents, setLiveEvents] = useState<LogEvent[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInitialData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsRes, incRes, evtRes, statusRes] = await Promise.all([
        api.getStatistics().catch((e) => {
          console.warn('Stats fetch error:', e);
          return { total_events: 0, threats_detected: 0, active_incidents: 0, critical_incidents: 0, current_risk: 0, source: 'offline' };
        }),
        api.getIncidents({ limit: 50 }).catch((e) => {
          console.warn('Incidents fetch error:', e);
          return { items: [] };
        }),
        api.getEvents({ limit: 50 }).catch((e) => {
          console.warn('Events fetch error:', e);
          return { items: [] };
        }),
        api.getSystemStatus().catch((e) => {
          console.warn('System status fetch error:', e);
          return null;
        }),
      ]);

      setStatistics(statsRes);
      setIncidents(incRes.items || []);
      setLiveEvents(evtRes.items || []);
      if (statusRes) setSystemStatus(statusRes);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInitialData();

    // Subscribe to live WebSocket events
    const unsubscribe = wsClient.subscribe((msg: WebSocketMessage) => {
      if (msg.type === 'event.created' && msg.payload) {
        setLiveEvents((prev) => [msg.payload as LogEvent, ...prev.slice(0, 99)]);
        setStatistics((prev) => ({
          ...prev,
          total_events: prev.total_events + 1,
        }));
      } else if (msg.type === 'incident.created' && msg.payload) {
        const newInc = msg.payload as Incident;
        setIncidents((prev) => [newInc, ...prev.filter((i) => i.incident_id !== newInc.incident_id)]);
        // Re-query statistics to maintain accurate counts
        api.getStatistics().then(setStatistics).catch(() => {});
      } else if (msg.type === 'incident.updated' && msg.payload) {
        const updated = msg.payload as Incident;
        setIncidents((prev) => {
          const exists = prev.some((i) => i.incident_id === updated.incident_id);
          if (exists) {
            return prev.map((i) => (i.incident_id === updated.incident_id ? { ...i, ...updated } : i));
          }
          return [updated, ...prev];
        });
        api.getStatistics().then(setStatistics).catch(() => {});
      } else if (msg.type === 'risk.changed' && msg.payload) {
        const { incident_id, risk_score, severity } = msg.payload;
        setIncidents((prev) =>
          prev.map((i) => (i.incident_id === incident_id ? { ...i, risk_score, severity } : i))
        );
        api.getStatistics().then(setStatistics).catch(() => {});
      } else if (msg.type === 'alert.created') {
        setStatistics((prev) => ({
          ...prev,
          threats_detected: prev.threats_detected + 1,
        }));
      }
    });

    return () => {
      unsubscribe();
    };
  }, [fetchInitialData]);

  return {
    statistics,
    incidents,
    liveEvents,
    systemStatus,
    loading,
    error,
    refresh: fetchInitialData,
  };
}
