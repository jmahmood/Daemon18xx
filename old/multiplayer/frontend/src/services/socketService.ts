/**
 * WebSocket service using Socket.IO client
 * Handles all real-time communication with the server
 */

import { io, Socket } from 'socket.io-client';

export type EventCallback = (data: any) => void;

class SocketService {
  private socket: Socket | null = null;
  private eventHandlers: Map<string, EventCallback[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor() {
    // Initialize socket connection
    this.connect();
  }

  connect() {
    // Connect to the server (proxy handles routing to port 8000)
    this.socket = io({
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });

    this.setupDefaultHandlers();
  }

  private setupDefaultHandlers() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('✅ Connected to server');
      this.reconnectAttempts = 0;
      this.emit('internal:connected', {});
    });

    this.socket.on('disconnect', (reason) => {
      console.log('🔌 Disconnected:', reason);
      this.emit('internal:disconnected', { reason });
    });

    this.socket.on('connect_error', (error) => {
      console.error('❌ Connection error:', error);
      this.reconnectAttempts++;
      this.emit('internal:connection_error', { error, attempts: this.reconnectAttempts });
    });

    this.socket.on('error', (error) => {
      console.error('❌ Server error:', error);
      this.emit('error', error);
    });

    // Game-specific events
    this.socket.on('authenticated', (data) => {
      console.log('✅ Authenticated:', data);
      this.emit('authenticated', data);
    });

    this.socket.on('game_started', (data) => {
      console.log('🎮 Game started');
      this.emit('game_started', data);
    });

    this.socket.on('game_state_update', (data) => {
      this.emit('game_state_update', data);
    });

    this.socket.on('player_action', (data: any) => {
      this.emit('player_action', data);
    });

    this.socket.on('player_connected', (data) => {
      console.log('👤 Player connected:', data);
      this.emit('player_connected', data);
    });

    this.socket.on('player_joined', (data) => {
      console.log('👤 Player joined:', data);
      this.emit('player_joined', data);
    });
  }

  /**
   * Register an event handler
   */
  on(event: string, callback: EventCallback) {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)!.push(callback);
  }

  /**
   * Unregister an event handler
   */
  off(event: string, callback: EventCallback) {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      const index = handlers.indexOf(callback);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  /**
   * Emit an event to registered handlers
   */
  private emit(event: string, data: any) {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach(callback => callback(data));
    }
  }

  /**
   * Authenticate with the server
   */
  authenticate(roomCode: string, token: string) {
    if (!this.socket) {
      throw new Error('Socket not connected');
    }
    this.socket.emit('authenticate', { room_code: roomCode, token });
  }

  /**
   * Join a game as a player
   */
  joinGame(playerName: string) {
    if (!this.socket) {
      throw new Error('Socket not connected');
    }
    this.socket.emit('join_game', { player_name: playerName });
  }

  /**
   * Start the game (creator only)
   */
  startGame(playerNames: string[]) {
    if (!this.socket) {
      throw new Error('Socket not connected');
    }
    this.socket.emit('start_game', { player_names: playerNames });
  }

  /**
   * Make a game move
   */
  makeMove(moveType: string, moveData: any) {
    if (!this.socket) {
      throw new Error('Socket not connected');
    }
    this.socket.emit('make_move', {
      move_type: moveType,
      move_data: moveData
    });
  }

  /**
   * Request current game state
   */
  requestGameState() {
    if (!this.socket) {
      throw new Error('Socket not connected');
    }
    this.socket.emit('request_game_state');
  }

  /**
   * Disconnect from server
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }
}

// Singleton instance
export const socketService = new SocketService();
