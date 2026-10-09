/**
 * REST API client communicating with Laptop 2 (LogShield Engine).
 */

import {
  Incident,
  IncidentDetail,
  IncidentTimelineResponse,
  LogEvent,
  SecurityAlert,
  SystemStatistics,
  SystemStatusData,
} from '../types';

export const API_BASE = import.meta.env.VITE_LOGSHIELD_API || 'http://127.0.0.1:8000';

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API Error [${response.status} ${response.statusText}]: ${errorBody}`);
  }

  return response.json();
}

export const api = {
  getHealth: () => fetchJson<{ status: string; service: string; phase: number }>('/api/health'),

  getSystemStatus: () => fetchJson<SystemStatusData>('/api/system-status'),

  getStatistics: () => fetchJson<SystemStatistics>('/api/statistics'),

  getEvents: (params?: {
    limit?: number;
    offset?: number;
    user?: string;
    source_ip?: string;
    event_type?: string;
    since?: string;
    until?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    if (params?.user) query.set('user', params.user);
    if (params?.source_ip) query.set('source_ip', params.source_ip);
    if (params?.event_type) query.set('event_type', params.event_type);
    if (params?.since) query.set('since', params.since);
    if (params?.until) query.set('until', params.until);

    const qs = query.toString();
    return fetchJson<{ items: LogEvent[]; total: number; limit: number; offset: number }>(
      `/api/events${qs ? `?${qs}` : ''}`
    );
  },

  getEvent: (eventId: string) => fetchJson<LogEvent>(`/api/events/${encodeURIComponent(eventId)}`),

  parseLogPreview: (payload: any) =>
    fetchJson<any>('/api/events/parse', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  ingestEvent: (payload: any) =>
    fetchJson<any>('/api/events', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getIncidents: (params?: {
    status?: string;
    severity?: string;
    user?: string;
    source_ip?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.severity) query.set('severity', params.severity);
    if (params?.user) query.set('user', params.user);
    if (params?.source_ip) query.set('source_ip', params.source_ip);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));

    const qs = query.toString();
    return fetchJson<{ items: Incident[]; total: number; limit: number; offset: number }>(
      `/api/incidents${qs ? `?${qs}` : ''}`
    );
  },

  getIncident: (incidentId: string) =>
    fetchJson<IncidentDetail>(`/api/incidents/${encodeURIComponent(incidentId)}`),

  patchIncident: (
    incidentId: string,
    update: { status?: string; notes?: string; assigned_to?: string; analyst?: string }
  ) =>
    fetchJson<IncidentDetail>(`/api/incidents/${encodeURIComponent(incidentId)}`, {
      method: 'PATCH',
      body: JSON.stringify(update),
    }),

  addIncidentNote: (incidentId: string, note: { note: string; analyst?: string }) =>
    fetchJson<IncidentDetail>(`/api/incidents/${encodeURIComponent(incidentId)}/notes`, {
      method: 'POST',
      body: JSON.stringify(note),
    }),

  getIncidentTimeline: (incidentId: string) =>
    fetchJson<IncidentTimelineResponse>(`/api/incidents/${encodeURIComponent(incidentId)}/timeline`),

  getAlerts: (params?: { limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    const qs = query.toString();
    return fetchJson<{ items: SecurityAlert[]; total: number; limit: number; offset: number }>(
      `/api/alerts${qs ? `?${qs}` : ''}`
    );
  },

  getRiskWeights: () => fetchJson<{ weights: Record<string, number>; severity_bands: Record<string, string>; formula: string }>('/api/risk/weights'),

  calculateRisk: (scores: {
    rule_score: number;
    ml_score: number;
    correlation_score: number;
    behavioral_score: number;
    custom_weights?: Record<string, number>;
  }) =>
    fetchJson<any>('/api/risk/calculate', {
      method: 'POST',
      body: JSON.stringify(scores),
    }),
};
