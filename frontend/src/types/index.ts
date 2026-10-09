/**
 * TypeScript contract interfaces mirroring the FastAPI backend schemas.
 */

export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type IncidentStatus = 'NEW' | 'INVESTIGATING' | 'CONTAINED' | 'RESOLVED' | 'FALSE_POSITIVE';

export interface LogEvent {
  event_id: string;
  timestamp: string;
  source_ip?: string | null;
  destination_ip?: string | null;
  user?: string | null;
  event_type: string;
  action: string;
  status?: string | null;
  resource?: string | null;
  protocol?: string | null;
  source_device?: string | null;
  metadata?: Record<string, any>;
  raw?: any;
  ingested_at: string;
}

export interface SecurityAlert {
  alert_id: string;
  created_at: string;
  source: string;
  severity: SeverityLevel;
  title: string;
  message: string;
  event_id?: string | null;
  incident_id?: string | null;
  extras?: Record<string, any>;
}

export interface RiskBreakdown {
  composite_score?: number;
  severity?: SeverityLevel;
  components?: {
    rule_score?: number;
    ml_score?: number;
    correlation_score?: number;
    behavioral_score?: number;
  };
  contributions?: {
    rule_contribution?: number;
    ml_contribution?: number;
    correlation_contribution?: number;
    behavioral_contribution?: number;
  };
  weights?: {
    w_rule?: number;
    w_ml?: number;
    w_corr?: number;
    w_beh?: number;
  };
  stages_detected?: string[];
  analyst_history?: Array<{
    timestamp: string;
    analyst: string;
    old_status?: string;
    new_status?: string;
    action?: string;
    note?: string;
  }>;
  notes?: Array<{
    timestamp: string;
    analyst: string;
    note: string;
  }>;
  assigned_to?: string;
  [key: string]: any;
}

export interface Incident {
  incident_id: string;
  created_at: string;
  updated_at: string;
  first_seen?: string | null;
  last_seen?: string | null;
  severity: SeverityLevel;
  risk_score: number;
  status: IncidentStatus;
  summary: string;
  explanation: string;
  recommendation: string;
  affected_user?: string | null;
  source_ip?: string | null;
  resource?: string | null;
  risk_breakdown?: RiskBreakdown;
}

export interface IncidentDetail extends Incident {
  events: LogEvent[];
  alerts: SecurityAlert[];
}

export interface TimelineItem {
  timestamp: string;
  item_type: 'event' | 'alert' | 'audit';
  title: string;
  details: Record<string, any>;
}

export interface IncidentTimelineResponse {
  incident_id: string;
  items: TimelineItem[];
  total: number;
}

export interface SystemStatistics {
  total_events: number;
  threats_detected: number;
  active_incidents: number;
  critical_incidents: number;
  current_risk: number;
  source: string;
  note?: string;
}

export interface ComponentHealth {
  status: 'ONLINE' | 'NOT_READY' | 'OFFLINE';
  detail: string;
}

export interface SystemStatusData {
  system: string;
  ai_engine: string;
  log_collector: string;
  ml_model: string;
  correlation_window_seconds: number;
  public_base_url: string;
  phase: number;
  components: Record<string, ComponentHealth>;
}

export type WebSocketEventType =
  | 'event.created'
  | 'alert.created'
  | 'incident.created'
  | 'incident.updated'
  | 'risk.changed'
  | 'system.status'
  | 'pong';

export interface WebSocketMessage<T = any> {
  type: WebSocketEventType;
  timestamp: string;
  payload: T;
}
