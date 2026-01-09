import { config } from './config';

type MessageHandler = (data: unknown) => void;

interface QueuedMessage {
  type: string;
  data: unknown;
  timestamp: number;
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private messageQueue: QueuedMessage[] = [];
  private maxQueueSize = 100;
  private heartbeatInterval: number | null = null;
  private heartbeatTimeout: number | null = null;
  private readonly HEARTBEAT_INTERVAL = 30000; // 30 seconds
  private readonly HEARTBEAT_TIMEOUT = 10000; // 10 seconds

  constructor() {
    this.url = `${config.wsUrl}/ws`;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.emit('connected', null);
        this.flushMessageQueue();
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const type = data.type || 'message';

          // Handle heartbeat responses
          if (type === 'pong') {
            this.clearHeartbeatTimeout();
          }

          this.emit(type, data);
        } catch (e) {
          console.warn('Failed to parse WebSocket message:', e);
          this.emit('message', event.data);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        this.stopHeartbeat();
        this.emit('disconnected', null);
        this.attemptReconnect();
      };

      this.ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        this.emit('error', { type: 'connection_error', message: 'WebSocket connection failed' });
      };
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      this.attemptReconnect();
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('reconnect_failed', {
        attempts: this.reconnectAttempts,
        message: 'Failed to reconnect after maximum attempts'
      });
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    );

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    this.emit('reconnecting', { attempt: this.reconnectAttempts, delay });

    setTimeout(() => {
      this.connect();
    }, delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();

    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));

        // Set timeout to detect dead connection
        this.heartbeatTimeout = setTimeout(() => {
          console.warn('Heartbeat timeout - closing stale connection');
          this.ws?.close();
        }, this.HEARTBEAT_TIMEOUT);
      }
    }, this.HEARTBEAT_INTERVAL);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    this.clearHeartbeatTimeout();
  }

  private clearHeartbeatTimeout(): void {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  private flushMessageQueue(): void {
    if (this.messageQueue.length === 0) return;

    console.log(`Flushing ${this.messageQueue.length} queued messages`);
    const messages = [...this.messageQueue];
    this.messageQueue = [];

    for (const msg of messages) {
      this.send(msg.type, msg.data);
    }
  }

  disconnect(): void {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.messageQueue = [];
  }

  send(type: string, data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify({ type, data }));
      } catch (e) {
        console.error('Failed to send message:', e);
        this.queueMessage(type, data);
      }
    } else {
      this.queueMessage(type, data);
    }
  }

  private queueMessage(type: string, data: unknown): void {
    // Add to queue if under max size
    if (this.messageQueue.length < this.maxQueueSize) {
      this.messageQueue.push({ type, data, timestamp: Date.now() });
      console.log(`Message queued (${this.messageQueue.length}/${this.maxQueueSize})`);
    } else {
      console.warn('Message queue full, dropping oldest message');
      this.messageQueue.shift(); // Remove oldest
      this.messageQueue.push({ type, data, timestamp: Date.now() });
    }
  }

  on(event: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);

    return () => {
      this.handlers.get(event)?.delete(handler);
    };
  }

  private emit(event: string, data: unknown): void {
    this.handlers.get(event)?.forEach((handler) => {
      try {
        handler(data);
      } catch (e) {
        console.error(`Error in handler for event ${event}:`, e);
      }
    });
    this.handlers.get('*')?.forEach((handler) => {
      try {
        handler({ event, data });
      } catch (e) {
        console.error(`Error in wildcard handler for event ${event}:`, e);
      }
    });
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get queuedMessageCount(): number {
    return this.messageQueue.length;
  }

  /**
   * Manually retry connection after max attempts reached
   */
  retry(): void {
    this.reconnectAttempts = 0;
    this.connect();
  }
}

export const wsClient = new WebSocketClient();
