import { config } from './config';
import { AuthStorage } from './authStorage';

const API_URL = config.apiUrl;

export type QueryParams = Record<string, string | number | boolean | undefined>;

interface FetchOptions extends RequestInit {
  params?: QueryParams;
  requireAuth?: boolean; // Whether this endpoint requires authentication
}

async function fetchApi<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { params, requireAuth = false, ...fetchOptions } = options;

  let url = `${API_URL}${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  // Build headers - use Record<string, string> to allow indexing
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(fetchOptions.headers as Record<string, string> | undefined),
  };

  // Add authentication header if token exists
  const accessToken = AuthStorage.getAccessToken();
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  } else if (requireAuth) {
    throw new Error('Authentication required');
  }

  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  });

  // Handle 401 Unauthorized - clear tokens
  if (response.status === 401) {
    AuthStorage.clearToken();
    throw new Error('Authentication failed. Please log in again.');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Events
  getEvents: (params?: QueryParams) =>
    fetchApi<Event[]>('/api/v1/events', { params }),
  getTimeline: (hours = 24) =>
    fetchApi<Event[]>('/api/v1/events/timeline', { params: { hours } }),
  createEvents: (events: EventCreate[]) =>
    fetchApi<{ created: number }>('/api/v1/events', {
      method: 'POST',
      body: JSON.stringify({ events }),
    }),

  // Patterns
  getPatterns: (params?: QueryParams) =>
    fetchApi<Pattern[]>('/api/v1/patterns', { params }),
  detectPatterns: (params?: QueryParams) =>
    fetchApi<DetectedPatterns>('/api/v1/patterns/detect', { params }),
  getPattern: (id: string) => fetchApi<Pattern>(`/api/v1/patterns/${id}`),

  // Suggestions
  getSuggestions: (params?: QueryParams) =>
    fetchApi<Suggestion[]>('/api/v1/suggestions', { params }),
  acceptSuggestion: (id: string) =>
    fetchApi<{ agent_id: string }>(`/api/v1/suggestions/${id}/accept`, {
      method: 'POST',
    }),
  dismissSuggestion: (id: string) =>
    fetchApi<{ message: string }>(`/api/v1/suggestions/${id}/dismiss`, {
      method: 'POST',
    }),

  // Agents
  getAgents: (params?: QueryParams) =>
    fetchApi<Agent[]>('/api/v1/agents', { params }),
  getAgent: (id: string) => fetchApi<Agent>(`/api/v1/agents/${id}`),
  createAgent: (data: AgentCreate) =>
    fetchApi<Agent>('/api/v1/agents', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateAgent: (id: string, data: Partial<AgentCreate>) =>
    fetchApi<Agent>(`/api/v1/agents/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteAgent: (id: string) =>
    fetchApi<{ message: string }>(`/api/v1/agents/${id}`, { method: 'DELETE' }),
  runAgent: (id: string, context?: Record<string, unknown>) =>
    fetchApi<AgentRunResult>(`/api/v1/agents/${id}/run`, {
      method: 'POST',
      body: JSON.stringify(context || {}),
    }),
  enableAgent: (id: string) =>
    fetchApi<Agent>(`/api/v1/agents/${id}/enable`, { method: 'POST' }),
  disableAgent: (id: string) =>
    fetchApi<Agent>(`/api/v1/agents/${id}/disable`, { method: 'POST' }),
  getAgentLogs: (id: string, params?: QueryParams) =>
    fetchApi<AgentLog[]>(`/api/v1/agents/${id}/logs`, { params }),

  // Analytics
  getSummary: (params?: QueryParams) =>
    fetchApi<AnalyticsSummary>('/api/v1/analytics/summary', { params }),
  getCategories: (params?: QueryParams) =>
    fetchApi<CategoryBreakdown[]>('/api/v1/analytics/categories', { params }),
  getAppUsage: (params?: QueryParams) =>
    fetchApi<AppUsage[]>('/api/v1/analytics/apps', { params }),
  getProductivity: (params?: QueryParams) =>
    fetchApi<ProductivityScore>('/api/v1/analytics/productivity', { params }),
  getTrends: (params?: QueryParams) =>
    fetchApi<TrendData[]>('/api/v1/analytics/trends', { params }),

  // Chat
  chat: (message: string, context?: Record<string, unknown>) =>
    fetchApi<ChatResponse>('/api/v1/chat', {
      method: 'POST',
      body: JSON.stringify({ message, context }),
    }),
  getChatHistory: (sessionId?: string) =>
    fetchApi<ChatMessage[]>('/api/v1/chat/history', {
      params: { session_id: sessionId },
    }),

  // Audit Logs
  getAuditLogs: (params?: QueryParams) =>
    fetchApi<AuditLog[]>('/api/v1/automation/audit-logs', { params }),

  // Health Check
  checkHealth: () =>
    fetchApi<HealthCheckResponse>('/api/v1/health'),

  // Settings
  getSettings: (deviceId: string) =>
    fetchApi<UserSettings>('/api/v1/settings', {
      params: { device_id: deviceId },
    }),
  saveSettings: (deviceId: string, settings: Record<string, unknown>) =>
    fetchApi<UserSettings>('/api/v1/settings', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId, settings }),
    }),
};

// Types
export interface Event {
  id: string;
  device_id: string;
  event_type: string;
  timestamp: string;
  app_name: string | null;
  window_title: string | null;
  url: string | null;
  data: Record<string, unknown>;
  category: string | null;
  created_at: string;
}

export interface EventCreate {
  device_id: string;
  event_type: string;
  timestamp: string;
  app_name?: string;
  window_title?: string;
  url?: string;
  data?: Record<string, unknown>;
  category?: string;
}

export interface Pattern {
  id: string;
  name: string;
  description: string | null;
  pattern_type: string;
  trigger_conditions: Record<string, unknown>;
  sequence: Record<string, unknown>[];
  occurrences: number;
  avg_duration_seconds: number | null;
  automatable: boolean;
  complexity: string;
  time_saved_minutes: number;
  status: string;
}

export interface DetectedPatterns {
  app_sequences: PatternSequence[];
  time_patterns: TimePattern[];
  context_switches: ContextSwitches;
}

export interface PatternSequence {
  type: string;
  sequence: string[];
  occurrences: number;
  automatable: boolean;
}

export interface TimePattern {
  type: string;
  hour: number;
  app: string;
  occurrences: number;
  automatable: boolean;
}

export interface ContextSwitches {
  total_switches: number;
  switch_rate: number;
  assessment: string;
}

export interface Suggestion {
  id: string;
  title: string;
  description: string | null;
  pattern_id: string | null;
  agent_type: string;
  agent_config: Record<string, unknown>;
  confidence: number;
  impact: string;
  time_saved_minutes: number;
  status: string;
  created_at: string;
}

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  agent_type: string;
  trigger_config: Record<string, unknown>;
  actions: Record<string, unknown>[];
  settings: Record<string, unknown>;
  code: string | null;
  status: string;
  last_run_at: string | null;
  last_error: string | null;
  run_count: number;
  success_count: number;
  error_count: number;
  total_time_saved_seconds: number;
  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  description?: string;
  agent_type: string;
  trigger_config: Record<string, unknown>;
  actions: Record<string, unknown>[];
  settings?: Record<string, unknown>;
  code?: string;
}

export interface AgentRunResult {
  success: boolean;
  error: string | null;
  results: Record<string, unknown>[];
  executed_at: string;
}

export interface AgentLog {
  id: string;
  agent_id: string;
  level: string;
  message: string;
  data: Record<string, unknown> | null;
  created_at: string;
}

export interface AnalyticsSummary {
  total_events: number;
  period: { start: string; end: string };
  top_apps: [string, number][];
  categories: Record<string, number>;
  hourly_activity: Record<number, number>;
}

export interface CategoryBreakdown {
  category: string;
  count: number;
}

export interface AppUsage {
  app_name: string;
  event_count: number;
}

export interface ProductivityScore {
  score: number;
  productive_events: number;
  total_events: number;
  trend: string;
}

export interface TrendData {
  date: string;
  count: number;
}

export interface ChatResponse {
  id: string;
  message: string;
  response: string;
  timestamp: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  action_type: string;
  actor: string;
  device_id: string | null;
  command_type: string | null;
  command_params: Record<string, unknown> | null;
  result: string;
  error_message: string | null;
  duration_ms: number | null;
  ip_address: string | null;
}

export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: number;
  response_time_ms: number;
  checks: {
    database: { status: string; latency_ms?: number; error?: string };
    redis: { status: string; latency_ms?: number; error?: string };
    memory: { status: string; percent_used?: number; error?: string };
    disk: { status: string; percent_used?: number; error?: string };
  };
}

export interface UserSettings {
  device_id: string;
  settings: Record<string, unknown>;
}
