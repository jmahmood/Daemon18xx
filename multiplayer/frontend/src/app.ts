/**
 * Main application class
 * Manages UI state, WebSocket connection, and game flow
 */

import { socketService } from './services/socketService';
import { soundEffects } from './utils/soundEffects';
import { parseGameURL } from './utils/urlParser';
import type { GameState, PlayerAction, AuthState } from './types';
import { Header } from './components/Header';
import { StockMarket } from './components/StockMarket';
import { HexMap } from './components/HexMap';
import { ActionTicker } from './components/ActionTicker';
import { PlayerList } from './components/PlayerList';
import { LobbyModal } from './components/LobbyModal';

export class App {
  private appContainer: HTMLElement;
  private authState: AuthState = { authenticated: false };
  private gameState: GameState | null = null;
  private currentTab: string = 'map';

  // UI Components
  private header: Header;
  private stockMarket: StockMarket;
  private hexMap: HexMap;
  private actionTicker: ActionTicker;
  private playerList: PlayerList;
  private lobbyModal: LobbyModal | null = null;

  constructor() {
    this.appContainer = document.getElementById('app')!;

    // Initialize components
    this.header = new Header();
    this.stockMarket = new StockMarket();
    this.hexMap = new HexMap();
    this.actionTicker = new ActionTicker();
    this.playerList = new PlayerList();
  }

  async initialize() {
    console.log('🎮 Initializing Daemon18xx Multiplayer...');

    // Parse URL for room code and token
    const urlParams = parseGameURL();

    if (urlParams.roomCode && urlParams.token) {
      // We have a direct game link
      await this.joinExistingGame(urlParams.roomCode, urlParams.token, urlParams.isSpectator);
    } else {
      // Show lobby/create game UI
      this.showLobbyUI();
    }

    // Setup WebSocket event handlers
    this.setupSocketHandlers();

    // Setup UI event handlers
    this.setupUIHandlers();
  }

  private async joinExistingGame(roomCode: string, token: string, isSpectator: boolean) {
    console.log(`🎮 Joining game: ${roomCode} (${isSpectator ? 'spectator' : 'player'})`);

    this.authState = {
      authenticated: false,
      roomCode,
      token,
    };

    // Authenticate with server
    socketService.authenticate(roomCode, token);

    // Show loading message
    this.showLoading('Connecting to game...');
  }

  private showLobbyUI() {
    // Clear loading
    this.appContainer.innerHTML = '';

    // Show lobby modal
    this.lobbyModal = new LobbyModal({
      onCreateGame: async (maxPlayers: number) => {
        await this.createNewGame(maxPlayers);
      },
      onJoinGame: (roomCode: string) => {
        // Redirect to game URL (will need token)
        window.location.href = `/game/${roomCode}/join`;
      }
    });

    this.appContainer.appendChild(this.lobbyModal.render());
  }

  private async createNewGame(maxPlayers: number) {
    try {
      const response = await fetch('/api/games/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_players: maxPlayers })
      });

      const data = await response.json();

      if (data.success) {
        // Show URLs to share
        this.showGameURLs(data);
      }
    } catch (error) {
      console.error('Failed to create game:', error);
      alert('Failed to create game. Please try again.');
    }
  }

  private showGameURLs(data: any) {
    // Create a modal showing all the URLs
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal">
        <div class="modal-header">
          <h2 class="modal-title">Game Created!</h2>
        </div>
        <div class="modal-body">
          <p style="margin-bottom: 20px;">Share these links with players:</p>

          <div class="form-group">
            <label class="form-label">Room Code:</label>
            <input class="form-input" readonly value="${data.room_code}" onclick="this.select()">
          </div>

          <div class="form-group">
            <label class="form-label">Your Link (Creator):</label>
            <input class="form-input" readonly value="${window.location.origin}${data.creator_url}" onclick="this.select()">
          </div>

          <div class="form-group">
            <label class="form-label">Player Links:</label>
            ${data.player_urls.map((url: string, i: number) => `
              <input class="form-input" style="margin-bottom: 10px;" readonly
                value="${window.location.origin}${url}" onclick="this.select()"
                placeholder="Player ${i + 1}">
            `).join('')}
          </div>

          <div class="form-group">
            <label class="form-label">Spectator Link:</label>
            <input class="form-input" readonly value="${window.location.origin}${data.spectator_url}" onclick="this.select()">
          </div>
        </div>
        <div class="modal-footer">
          <button onclick="window.location.href='${data.creator_url}'">Go to Game</button>
        </div>
      </div>
    `;

    this.appContainer.appendChild(modal);
  }

  private setupSocketHandlers() {
    // Connection events
    socketService.on('internal:connected', () => {
      console.log('✅ Connected to server');
    });

    socketService.on('internal:disconnected', (data) => {
      console.log('🔌 Disconnected:', data.reason);
      this.showError('Disconnected from server. Attempting to reconnect...');
    });

    socketService.on('internal:connection_error', (data) => {
      console.error('❌ Connection error:', data);
      if (data.attempts >= 5) {
        this.showError('Failed to connect to server. Please refresh the page.');
      }
    });

    // Authentication
    socketService.on('authenticated', (data) => {
      console.log('✅ Authenticated:', data);
      this.authState.authenticated = true;
      this.authState.authType = data.auth_type;

      // Build main UI
      this.buildMainUI();

      // Request current game state
      socketService.requestGameState();
    });

    // Game events
    socketService.on('game_started', (data) => {
      console.log('🎮 Game started');
      soundEffects.playSuccess();
      this.gameState = data.game_state;
      this.updateUI();
    });

    socketService.on('game_state_update', (data) => {
      console.log('📊 Game state updated');
      this.gameState = data.game_state;
      this.updateUI();
    });

    socketService.on('player_action', (action: PlayerAction) => {
      console.log('🎬 Player action:', action);
      this.actionTicker.addAction(action);
      soundEffects.playChime();
    });

    socketService.on('player_joined', (data) => {
      console.log('👤 Player joined:', data);
      this.updatePlayerList(data.players);
    });

    // Errors
    socketService.on('error', (error) => {
      console.error('❌ Error:', error);
      this.showError(error.message || 'An error occurred');
    });
  }

  private setupUIHandlers() {
    // Tab switching
    document.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;

      if (target.classList.contains('tab')) {
        const tabName = target.dataset.tab;
        if (tabName) {
          this.switchTab(tabName);
        }
      }
    });

    // Sound toggle
    document.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;

      if (target.id === 'sound-toggle') {
        const enabled = !soundEffects.isEnabled();
        soundEffects.setEnabled(enabled);
        target.textContent = enabled ? '🔊 Sound On' : '🔇 Sound Off';
      }
    });
  }

  private buildMainUI() {
    this.appContainer.innerHTML = '';

    const container = document.createElement('div');
    container.className = 'app-container';

    // Header
    container.appendChild(this.header.render());

    // Main content with tabs
    const mainContent = document.createElement('div');
    mainContent.className = 'main-content';

    // Tabs navigation
    const tabsNav = document.createElement('div');
    tabsNav.className = 'tabs';
    tabsNav.innerHTML = `
      <div class="tab active" data-tab="map">Map</div>
      <div class="tab" data-tab="market">Stock Market</div>
      <div class="tab" data-tab="companies">Companies</div>
    `;

    mainContent.appendChild(tabsNav);

    // Tab content
    const tabContent = document.createElement('div');
    tabContent.className = 'tab-content';

    // Map tab
    const mapPanel = document.createElement('div');
    mapPanel.className = 'tab-panel active';
    mapPanel.dataset.tab = 'map';
    mapPanel.appendChild(this.hexMap.render());

    // Market tab
    const marketPanel = document.createElement('div');
    marketPanel.className = 'tab-panel';
    marketPanel.dataset.tab = 'market';
    marketPanel.appendChild(this.stockMarket.render());

    // Companies tab
    const companiesPanel = document.createElement('div');
    companiesPanel.className = 'tab-panel';
    companiesPanel.dataset.tab = 'companies';
    companiesPanel.innerHTML = '<div class="company-grid" id="company-grid"></div>';

    tabContent.appendChild(mapPanel);
    tabContent.appendChild(marketPanel);
    tabContent.appendChild(companiesPanel);

    mainContent.appendChild(tabContent);
    container.appendChild(mainContent);

    // Footer (ticker)
    container.appendChild(this.actionTicker.render());

    // Sidebar (player list)
    container.appendChild(this.playerList.render());

    this.appContainer.appendChild(container);
  }

  private switchTab(tabName: string) {
    this.currentTab = tabName;

    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
      tab.classList.toggle('active', (tab as HTMLElement).dataset.tab === tabName);
    });

    // Update tab panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
      panel.classList.toggle('active', (panel as HTMLElement).dataset.tab === tabName);
    });

    soundEffects.playClick();
  }

  private updateUI() {
    if (!this.gameState) return;

    // Update header
    this.header.update(this.gameState);

    // Update stock market
    if (this.gameState.stock_market) {
      this.stockMarket.update(this.gameState.stock_market);
    }

    // Update player list
    if (this.gameState.players) {
      this.playerList.update(this.gameState.players);
    }

    // Update hex map (if companies have placed tokens, etc.)
    this.hexMap.update(this.gameState);
  }

  private updatePlayerList(players: any[]) {
    this.playerList.update(players);
  }

  private showLoading(message: string) {
    this.appContainer.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; height: 100vh; flex-direction: column; gap: 20px;">
        <div style="font-size: 24px;">🚂</div>
        <p style="font-size: 18px;">${message}</p>
      </div>
    `;
  }

  private showError(message: string) {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: var(--danger-color);
      color: white;
      padding: 15px 20px;
      border-radius: 8px;
      box-shadow: var(--shadow);
      z-index: 10000;
      animation: slideIn 0.3s;
    `;
    errorDiv.textContent = message;

    this.appContainer.appendChild(errorDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      errorDiv.remove();
    }, 5000);
  }
}
