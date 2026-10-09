import { useEffect, useState } from 'react';
import { ConnectionStatus, wsClient } from '../services/websocket';
import { WebSocketEventType, WebSocketMessage } from '../types';

export function useWebSocket() {
  const [status, setStatus] = useState<ConnectionStatus>(wsClient.getStatus());
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  useEffect(() => {
    wsClient.connect();

    const unsubscribeStatus = wsClient.onStatusChange((newStatus) => {
      setStatus(newStatus);
    });

    const unsubscribeMessage = wsClient.subscribe((msg) => {
      setLastMessage(msg);
    });

    return () => {
      unsubscribeStatus();
      unsubscribeMessage();
    };
  }, []);

  const subscribeToType = (type: WebSocketEventType, callback: (msg: WebSocketMessage) => void) => {
    return wsClient.subscribe((msg) => {
      if (msg.type === type) {
        callback(msg);
      }
    });
  };

  return {
    status,
    lastMessage,
    subscribeToType,
    send: wsClient.send.bind(wsClient),
    reconnect: wsClient.connect.bind(wsClient),
  };
}
