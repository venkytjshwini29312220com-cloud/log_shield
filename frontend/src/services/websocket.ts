/**
 * Real-time WebSocket connection to /ws/events with reconnect logic and subscriber fan-out.
 */

import { WebSocketMessage } from '../types';
import { API_BASE } from './api';

export type ConnectionStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED';
export type MessageListener = (message: WebSocketMessage) => void;
export type StatusListener = (status: ConnectionStatus) => void;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private listeners: Set<MessageListener> = new Set();
  private statusListeners: Set<StatusListener> = new Set();
  private status: ConnectionStatus = 'DISCONNECTED';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 20;
  private reconnectDelay = 2000;
  private pingInterval: any = null;
  private explicitClose = false;

  public getStatus(): ConnectionStatus {
    return this.status;
  }

  private setStatus(newStatus: ConnectionStatus) {
    this.status = newStatus;
    this.statusListeners.forEach((listener) => {
      try {
        listener(newStatus);
      } catch (err) {
        console.error('Error in WS status listener:', err);
      }
    });
  }

  public connect() {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.explicitClose = false;
    this.setStatus('CONNECTING');

    const wsUrl = API_BASE.replace(/^http/, 'ws') + '/ws/events';

    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        this.setStatus('CONNECTED');
        this.reconnectAttempts = 0;

        // Periodic keepalive ping
        this.startPing();
      };

      this.socket.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          this.listeners.forEach((listener) => {
            try {
              listener(data);
            } catch (err) {
              console.error('Error in WS message listener:', err);
            }
          });
        } catch (err) {
          // If message is raw text ping/pong
          if (event.data === 'pong') {
            return;
          }
          console.warn('Failed to parse WebSocket message frame:', event.data, err);
        }
      };

      this.socket.onerror = (err) => {
        console.warn('WebSocket error:', err);
      };

      this.socket.onclose = () => {
        this.stopPing();
        this.setStatus('DISCONNECTED');
        this.socket = null;

        if (!this.explicitClose && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          const delay = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1), 15000);
          setTimeout(() => this.connect(), delay);
        }
      };
    } catch (err) {
      console.error('WebSocket connection instantiation error:', err);
      this.setStatus('DISCONNECTED');
    }
  }

  public disconnect() {
    this.explicitClose = true;
    this.stopPing();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.setStatus('DISCONNECTED');
  }

  public send(data: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const payload = typeof data === 'string' ? data : JSON.stringify(data);
      this.socket.send(payload);
    }
  }

  private startPing() {
    this.stopPing();
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 25000);
  }

  private stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  public subscribe(listener: MessageListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  public onStatusChange(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    listener(this.status);
    return () => {
      this.statusListeners.delete(listener);
    };
  }
}

export const wsClient = new WebSocketClient();
