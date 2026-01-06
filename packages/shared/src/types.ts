// Shared types for Observer

export interface Event {
  id: string;
  device_id: string;
  event_type: EventType;
  timestamp: string;
  app_name: string | null;
  window_title: string | null;
  url: string | null;
  data: Record<string, unknown>;
  category: Category | null;
  created_at: string;
}

export type EventType =
  | 'app_focus'
  | 'window_change'
  | 'url_visit'
  | 'file_open'
  | 'clipboard'
  | 'keystroke'
  | 'idle'
  | 'active';

export type Category =
  | 'coding'
  | 'browsing'
  | 'writing'
  | 'communication'
  | 'design'
  | 'research'
  | 'entertainment'
  | 'other';

export interface Pattern {
  id: string;
  name: string;
  description: string | null;
  pattern_type: PatternType;
  trigger_conditions: Record<string, unknown>;
  sequence: Record<string, unknown>[];
  occurrences: number;
  avg_duration_seconds: number | null;
  automatable: boolean;
  complexity: Complexity;
  time_saved_minutes: number;
  status: PatternStatus;
  first_seen_at: string | null;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export type PatternType = 'sequence' | 'time_based' | 'context_switch' | 'custom';
export type PatternStatus = 'active' | 'archived' | 'dismissed';
export type Complexity = 'low' | 'medium' | 'high';

export interface Suggestion {
  id: string;
  title: string;
  description: string | null;
  pattern_id: string | null;
  agent_type: AgentType;
  agent_config: Record<string, unknown>;
  confidence: number;
  impact: Impact;
  time_saved_minutes: number;
  status: SuggestionStatus;
  dismissed_at: string | null;
  accepted_at: string | null;
  created_at: string;
}

export type SuggestionStatus = 'pending' | 'accepted' | 'dismissed';
export type Impact = 'low' | 'medium' | 'high';

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  agent_type: AgentType;
  trigger_config: TriggerConfig;
  actions: Action[];
  settings: Record<string, unknown>;
  code: string | null;
  status: AgentStatus;
  last_run_at: string | null;
  last_error: string | null;
  run_count: number;
  success_count: number;
  error_count: number;
  total_time_saved_seconds: number;
  suggestion_id: string | null;
  created_at: string;
  updated_at: string;
}

export type AgentType = 'monitor' | 'reporter' | 'assistant' | 'automation';
export type AgentStatus = 'draft' | 'active' | 'disabled' | 'error';

export interface TriggerConfig {
  type: TriggerType;
  value?: string;
  condition?: string;
  schedule?: string;
}

export type TriggerType = 'schedule' | 'event' | 'pattern' | 'webhook' | 'manual';

export interface Action {
  type: ActionType;
  template?: string;
  prompt?: string;
  url?: string;
  method?: string;
  headers?: Record<string, string>;
  body?: unknown;
  seconds?: number;
  condition?: string;
  message?: string;
}

export type ActionType =
  | 'notify'
  | 'analyze'
  | 'http'
  | 'delay'
  | 'condition'
  | 'log';

export interface AgentLog {
  id: string;
  agent_id: string;
  level: LogLevel;
  message: string;
  data: Record<string, unknown> | null;
  created_at: string;
}

export type LogLevel = 'debug' | 'info' | 'warning' | 'error';

export interface Device {
  id: string;
  name: string;
  os: string;
  os_version: string | null;
  app_version: string | null;
  last_seen_at: string | null;
  created_at: string;
}

export interface AnalyticsSummary {
  total_events: number;
  period: {
    start: string;
    end: string;
  };
  top_apps: [string, number][];
  categories: Record<string, number>;
  hourly_activity: Record<number, number>;
}

export interface ProductivityScore {
  score: number;
  productive_events: number;
  total_events: number;
  trend: 'up' | 'down' | 'stable';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}
