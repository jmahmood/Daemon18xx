/**
 * Header component - displays game phase, current player, and player stats
 */

import type { GameState } from '../types';

export class Header {
  private element: HTMLElement | null = null;

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
      const player = gameState.players.find(p => p.id === gameState.current_player);
      if (player) {
        currentPlayerEl.textContent = `Current: ${player.name}`;
        currentPlayerEl.classList.add('active');
      }
    }

    // Update player stats (assumes first player is "you")
    if (gameState.players.length > 0) {
      const player = gameState.players[0]; // TODO: identify actual player

      const cashEl = this.element.querySelector('#player-cash');
      if (cashEl) {
        cashEl.textContent = `$${player.cash}`;
      }

      const certsEl = this.element.querySelector('#player-certs');
      if (certsEl) {
        certsEl.textContent = `${player.certificates || 0}`;
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
