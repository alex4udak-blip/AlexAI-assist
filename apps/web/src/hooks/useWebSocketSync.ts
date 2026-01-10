import { useEffect, useCallback } from 'react';
import { useWebSocketEvent } from './useWebSocket';

interface DeviceUpdate {
  device_id: string;
  status: {
    connected: boolean;
    last_seen_at: string;
    last_sync_at?: string;
    status: string;
    [key: string]: unknown;
  };
}

interface CommandResult {
  command_id: string;
  device_id: string;
  result: {
    success: boolean;
    result?: unknown;
    error?: string;
    duration_ms?: number;
    completed_at?: string;
  };
}

interface EventsCreated {
  count: number;
  device_ids: string[];
  events: Array<{
    device_id: string;
    event_type: string;
    timestamp: string;
    app_name?: string;
    window_title?: string;
    url?: string;
    category?: string;
    data?: Record<string, unknown>;
  }>;
}

// Type guards for runtime validation
function isDeviceUpdate(data: unknown): data is DeviceUpdate {
  return (
    typeof data === 'object' &&
    data !== null &&
    'device_id' in data &&
    typeof (data as DeviceUpdate).device_id === 'string' &&
    'status' in data &&
    typeof (data as DeviceUpdate).status === 'object'
  );
}

function isCommandResult(data: unknown): data is CommandResult {
  return (
    typeof data === 'object' &&
    data !== null &&
    'command_id' in data &&
    typeof (data as CommandResult).command_id === 'string' &&
    'device_id' in data &&
    typeof (data as CommandResult).device_id === 'string' &&
    'result' in data &&
    typeof (data as CommandResult).result === 'object'
  );
}

function isEventsCreated(data: unknown): data is EventsCreated {
  return (
    typeof data === 'object' &&
    data !== null &&
    'count' in data &&
    typeof (data as EventsCreated).count === 'number' &&
    'device_ids' in data &&
    Array.isArray((data as EventsCreated).device_ids) &&
    'events' in data &&
    Array.isArray((data as EventsCreated).events)
  );
}

export function useDeviceUpdates(onUpdate: (data: DeviceUpdate) => void) {
  const handleUpdate = useCallback(
    (data: unknown) => {
      if (isDeviceUpdate(data)) {
        onUpdate(data);
      } else {
        console.warn('Invalid DeviceUpdate data received:', data);
      }
    },
    [onUpdate]
  );

  useWebSocketEvent('device_updated', handleUpdate);
}

export function useCommandResults(
  onResult: (data: CommandResult) => void
) {
  const handleResult = useCallback(
    (data: unknown) => {
      if (isCommandResult(data)) {
        onResult(data);
      } else {
        console.warn('Invalid CommandResult data received:', data);
      }
    },
    [onResult]
  );

  useWebSocketEvent('command_result', handleResult);
}

export function useEventsCreated(onEvents: (data: EventsCreated) => void) {
  const handleEvents = useCallback(
    (data: unknown) => {
      if (isEventsCreated(data)) {
        onEvents(data);
      } else {
        console.warn('Invalid EventsCreated data received:', data);
      }
    },
    [onEvents]
  );

  useWebSocketEvent('events_created', handleEvents);
}

export function useSyncStatus(
  onSync: (status: { connected: boolean; lastSync?: string }) => void
) {
  useEffect(() => {
    const checkInterval = setInterval(() => {
      onSync({ connected: true, lastSync: new Date().toISOString() });
    }, 30000);

    return () => clearInterval(checkInterval);
  }, [onSync]);
}
