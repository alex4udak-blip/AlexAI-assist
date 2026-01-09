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

export function useDeviceUpdates(onUpdate: (data: DeviceUpdate) => void) {
  const handleUpdate = useCallback(
    (data: unknown) => {
      onUpdate(data as DeviceUpdate);
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
      onResult(data as CommandResult);
    },
    [onResult]
  );

  useWebSocketEvent('command_result', handleResult);
}

export function useEventsCreated(onEvents: (data: EventsCreated) => void) {
  const handleEvents = useCallback(
    (data: unknown) => {
      onEvents(data as EventsCreated);
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
