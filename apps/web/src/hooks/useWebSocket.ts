import { useEffect, useState, useCallback, useRef } from 'react';
import { wsClient } from '../lib/websocket';

// Reference counter to track how many components are using the WebSocket
let activeConnections = 0;

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(wsClient.isConnected);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    // Increment reference counter and connect if this is the first component
    activeConnections++;
    if (activeConnections === 1) {
      wsClient.connect();
    }

    // Set up handlers for this component
    const unsubConnect = wsClient.on('connected', () => setIsConnected(true));
    const unsubDisconnect = wsClient.on('disconnected', () =>
      setIsConnected(false)
    );

    // Store cleanup function
    cleanupRef.current = () => {
      unsubConnect();
      unsubDisconnect();
    };

    return () => {
      // Clean up this component's handlers
      if (cleanupRef.current) {
        cleanupRef.current();
        cleanupRef.current = null;
      }

      // Decrement reference counter and disconnect only if this is the last component
      activeConnections--;
      if (activeConnections === 0) {
        wsClient.disconnect();
      }
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
