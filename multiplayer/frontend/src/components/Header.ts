/**
 * Header component - displays game phase, current player, and player stats
 */

import type { GameState } from '../types';

export class Header {
  private element: HTMLElement | null = null;
  private myPlayerName: string | null = null;

  render(): HTMLElement {
    const header = document.createElement('div');
    header.className = 'header';
    header.id = 'game-header';

    header.innerHTML = `
      <div class="header-left">
        <div class="game-logo">
          <span style="font-size: 24px;">🚂</span>
          <span style="font-weight: 700; margin-left: 10px;">1889</span>
        </div>
      </div>

      <div class="header-center">
        <div class="game-phase" id="game-phase">Waiting to start...</div>
        <div class="current-player" id="current-player"></div>
      </div>

      <div class="header-right">
        <div class="player-name-display" id="player-name-display">
          <span class="player-label">You:</span>
          <span class="player-name" id="my-player-name">—</span>
        </div>
        <div class="player-stats">
          <div class="stat-item">
            <div class="stat-label">Cash</div>
            <div class="stat-value" id="player-cash">—</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">Certs</div>
            <div class="stat-value" id="player-certs">—</div>
          </div>
        </div>
      </div>
    `;

    this.element = header;
    return header;
  }

  setPlayerName(playerName: string) {
    this.myPlayerName = playerName;

    // Update display immediately
    if (this.element) {
      const nameEl = this.element.querySelector('#my-player-name');
      if (nameEl) {
        nameEl.textContent = playerName;
      }
    }
  }

  update(gameState: GameState) {
    if (!this.element) return;

    // Update game phase
    const phaseEl = this.element.querySelector('#game-phase');
    if (phaseEl) {
      phaseEl.textContent = this.formatPhase(gameState.phase);
    }

    // Update current player
    const currentPlayerEl = this.element.querySelector('#current-player');
    if (currentPlayerEl && gameState.current_player) {
      currentPlayerEl.textContent = `Current: ${gameState.current_player.name}`;
      currentPlayerEl.classList.add('active');
    }

    // Update player stats (find the current user's player)
    if (this.myPlayerName && gameState.players) {
      const myPlayer = gameState.players.find(p => p.name === this.myPlayerName);
      if (myPlayer) {
        const cashEl = this.element.querySelector('#player-cash');
        if (cashEl) {
          cashEl.textContent = `$${myPlayer.cash}`;
        }

        const certsEl = this.element.querySelector('#player-certs');
        if (certsEl) {
          certsEl.textContent = `${myPlayer.certificates || 0}`;
        }
      }
    }
  }

  private formatPhase(phase: string): string {
    // Convert phase class names to readable text
    const phaseMap: Record<string, string> = {
      'BuyPrivateCompany': 'Private Company Auction - Purchase',
      'BiddingForPrivateCompany': 'Private Company Auction - Bidding',
      'StockRound': 'Stock Round',
      'OperatingRound1': 'Operating Round 1',
      'OperatingRound2': 'Operating Round 2',
      'OperatingRound3': 'Operating Round 3',
      'StockRoundSellPrivateCompany': 'Stock Round - Sell Private',
      'TrainsRusted': 'Emergency Train Purchase',
    };

    return phaseMap[phase] || phase;
  }
}
