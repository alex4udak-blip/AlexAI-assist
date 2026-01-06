import { useEffect, useState, useCallback } from 'react';
import { wsClient } from '../lib/websocket';

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    wsClient.connect();

    const unsubConnect = wsClient.on('connected', () => setIsConnected(true));
    const unsubDisconnect = wsClient.on('disconnected', () =>
      setIsConnected(false)
    );

    return () => {
      unsubConnect();
      unsubDisconnect();
    };
  }, []);

  const send = useCallback((type: string, data: unknown) => {
    wsClient.send(type, data);
  }, []);

  const subscribe = useCallback(
    (event: string, handler: (data: unknown) => void) => {
      return wsClient.on(event, handler);
    },
    []
  );

  return { isConnected, send, subscribe };
}

export function useWebSocketEvent<T>(
  event: string,
  handler: (data: T) => void
) {
  useEffect(() => {
    return wsClient.on(event, handler as (data: unknown) => void);
  }, [event, handler]);
}
