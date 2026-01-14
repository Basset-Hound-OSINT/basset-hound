import { useEffect, useRef, useCallback, useState } from 'react';
import type { SuggestionEvent } from '@/types';
import { useSuggestionsStore } from '@/store';

/**
 * WebSocket connection state
 */
export type WebSocketState = 'connecting' | 'connected' | 'disconnected' | 'error';

/**
 * WebSocket hook options
 */
interface UseWebSocketOptions {
  projectId: string;
  onEvent?: (event: SuggestionEvent) => void;
  autoReconnect?: boolean;
  reconnectDelay?: number;
  maxReconnectAttempts?: number;
}

/**
 * Custom hook for WebSocket connection to suggestions endpoint
 * Based on Phase 45 WebSocket specification
 */
export function useWebSocket({
  projectId,
  onEvent,
  autoReconnect = true,
  reconnectDelay = 1000,
  maxReconnectAttempts = 5,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const [state, setState] = useState<WebSocketState>('disconnected');
  const [error, setError] = useState<string | null>(null);

  const handleWebSocketEvent = useSuggestionsStore((s) => s.handleWebSocketEvent);

  /**
   * Connect to WebSocket server
   */
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setState('connecting');
    setError(null);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/suggestions/${projectId}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setState('connected');
        reconnectAttempts.current = 0;
        console.log(`[WebSocket] Connected to ${wsUrl}`);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle ping/pong
          if (data.type === 'pong') {
            return;
          }

          // Handle connection confirmation
          if (data.type === 'connected' || data.type === 'subscribed') {
            console.log(`[WebSocket] ${data.type}:`, data);
            return;
          }

          // Handle suggestion events
          const suggestionEvent: SuggestionEvent = {
            eventType: data.type || data.event_type,
            timestamp: data.timestamp || new Date().toISOString(),
            data: data.data || data,
            _links: data._links,
          };

          // Update store
          handleWebSocketEvent(suggestionEvent);

          // Call custom handler if provided
          onEvent?.(suggestionEvent);
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('[WebSocket] Error:', event);
        setState('error');
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log(`[WebSocket] Closed: ${event.code} ${event.reason}`);
        setState('disconnected');
        wsRef.current = null;

        // Auto-reconnect with exponential backoff
        if (autoReconnect && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = reconnectDelay * Math.pow(2, reconnectAttempts.current);
          console.log(`[WebSocket] Reconnecting in ${delay}ms...`);

          reconnectTimeoutRef.current = window.setTimeout(() => {
            reconnectAttempts.current += 1;
            connect();
          }, delay);
        }
      };
    } catch (err) {
      setState('error');
      setError((err as Error).message);
    }
  }, [projectId, autoReconnect, reconnectDelay, maxReconnectAttempts, handleWebSocketEvent, onEvent]);

  /**
   * Disconnect from WebSocket server
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setState('disconnected');
  }, []);

  /**
   * Send ping to keep connection alive
   */
  const ping = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ping' }));
    }
  }, []);

  /**
   * Subscribe to entity-specific suggestions
   */
  const subscribeToEntity = useCallback((entityId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'subscribe_entity',
          entity_id: entityId,
        })
      );
    }
  }, []);

  /**
   * Unsubscribe from entity-specific suggestions
   */
  const unsubscribeFromEntity = useCallback((entityId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'unsubscribe_entity',
          entity_id: entityId,
        })
      );
    }
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Keepalive ping every 30 seconds
  useEffect(() => {
    const interval = window.setInterval(ping, 30000);
    return () => window.clearInterval(interval);
  }, [ping]);

  return {
    state,
    error,
    connect,
    disconnect,
    ping,
    subscribeToEntity,
    unsubscribeFromEntity,
  };
}
