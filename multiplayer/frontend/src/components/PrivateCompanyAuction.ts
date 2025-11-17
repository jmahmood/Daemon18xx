/**
 * Private Company Auction component with full bidding support
 * Handles BUY, BID, and PASS moves for the private company auction phase
 */

export class PrivateCompanyAuction {
  private element: HTMLElement | null = null;
  private gameState: any = null;
  private onMakeMove?: (moveData: any) => void;
  private currentPlayerId: string | null = null;

  constructor(options: {
    onMakeMove?: (moveData: any) => void;
  }) {
    this.onMakeMove = options.onMakeMove;
  }

  render(): HTMLElement {
    const container = document.createElement('div');
    container.className = 'auction-container';
    container.id = 'private-auction';

    container.innerHTML = `
      <div class="auction-header">
        <h2>🏢 Private Company Auction</h2>
        <p class="instruction">Purchase or bid on private companies. Companies must be bought in order.</p>
      </div>

      <div class="turn-indicator" id="turn-indicator" style="margin-bottom: 20px;">
        <p style="text-align: center; color: var(--text-secondary);">
          Waiting for game data...
        </p>
      </div>

      <div class="auction-companies" id="auction-companies">
        <p style="text-align: center; color: var(--text-secondary);">
          Loading...
        </p>
      </div>
    `;

    this.element = container;
    return container;
  }

  setCurrentPlayer(playerId: string) {
    this.currentPlayerId = playerId;
    this.refresh();
  }

  updateGameState(gameState: any) {
    this.gameState = gameState;
    this.refresh();
  }

  private refresh() {
    if (!this.element || !this.gameState) return;

    this.updateTurnIndicator();
    this.updateCompanies();
  }

  private updateTurnIndicator() {
    const indicator = this.element?.querySelector('#turn-indicator');
    if (!indicator || !this.gameState) return;

    const currentPlayer = this.gameState.current_player;
    const isMyTurn = currentPlayer && currentPlayer.id === this.currentPlayerId;

    let html = '';
    if (currentPlayer) {
      if (isMyTurn) {
        html = `
          <div style="background: var(--success-color); color: white; padding: 15px; border-radius: 8px; text-align: center;">
            <strong>🎯 YOUR TURN</strong> - Choose an action below
          </div>
        `;
      } else {
        html = `
          <div style="background: var(--background-tertiary); padding: 15px; border-radius: 8px; text-align: center;">
            Waiting for <strong>${this.escapeHtml(currentPlayer.name)}</strong> to make a move...
          </div>
        `;
      }
    }

    indicator.innerHTML = html;
  }

  private updateCompanies() {
    const companiesContainer = this.element?.querySelector('#auction-companies');
    if (!companiesContainer || !this.gameState) return;

    const privateCompanies = this.gameState.private_companies || [];
    const currentPlayer = this.gameState.current_player;
    const players = this.gameState.players || [];
    const isMyTurn = currentPlayer && currentPlayer.id === this.currentPlayerId;

    // Find current player's cash
    let playerCash = 0;
    if (currentPlayer) {
      const player = players.find((p: any) => p.id === currentPlayer.id);
      if (player) {
        playerCash = player.cash;
      }
    }

    // Find the current company for sale (first one without an owner)
    const currentCompany = privateCompanies.find((pc: any) => !pc.owner);

    // Separate companies
    const available = privateCompanies.filter((pc: any) => !pc.owner);
    const sold = privateCompanies.filter((pc: any) => pc.owner);

    let html = '';

    if (available.length > 0) {
      html += '<div class="company-section">';
      html += '<h3 style="margin-bottom: 15px;">Available for Purchase</h3>';
      html += '<div class="company-grid">';

      available.forEach((pc: any) => {
        const isCurrent = currentCompany && currentCompany.order === pc.order;
        const canAfford = playerCash >= pc.cost;

        html += `
          <div class="company-card ${isCurrent ? 'current-company' : ''} ${!canAfford ? 'unaffordable' : ''}">
            <div class="company-header">
              <span class="company-short-name">${this.escapeHtml(pc.short_name)}</span>
              <span class="company-cost">$${pc.cost}</span>
            </div>

            ${isCurrent ? '<div class="current-badge">▶ FOR SALE NOW</div>' : ''}

            <div class="company-name">${this.escapeHtml(pc.name)}</div>
            <div class="company-revenue">Revenue: $${pc.revenue}</div>

            ${isMyTurn ? this.renderActions(pc, isCurrent, canAfford) : ''}
          </div>
        `;
      });

      html += '</div></div>';
    }

    if (sold.length > 0) {
      html += '<div class="company-section" style="margin-top: 30px;">';
      html += '<h3 style="margin-bottom: 15px;">Sold</h3>';
      html += '<div class="company-grid">';

      sold.forEach((pc: any) => {
        html += `
          <div class="company-card sold">
            <div class="company-header">
              <span class="company-short-name">${this.escapeHtml(pc.short_name)}</span>
              <span class="company-cost">$${pc.cost}</span>
            </div>
            <div class="company-name">${this.escapeHtml(pc.name)}</div>
            <div class="company-revenue">Revenue: $${pc.revenue}</div>
            <div class="company-owner">Owner: ${this.escapeHtml(pc.owner)}</div>
          </div>
        `;
      });

      html += '</div></div>';
    }

    companiesContainer.innerHTML = html;
    this.setupEventListeners();
  }

  private renderActions(company: any, isCurrent: boolean, canAfford: boolean): string {
    if (isCurrent) {
      // Current company: BUY or PASS
      return `
        <div class="action-buttons">
          <button class="action-btn buy-btn"
                  data-action="buy"
                  data-company-order="${company.order}"
                  ${!canAfford ? 'disabled' : ''}>
            ${canAfford ? `💰 Buy for $${company.cost}` : 'Cannot Afford'}
          </button>
          <button class="action-btn pass-btn"
                  data-action="pass"
                  data-company-order="${company.order}">
            ⏭️ Pass
          </button>
        </div>
      `;
    } else {
      // Future company: BID (requires bidding $5 above cost minimum)
      const minBid = company.cost + 5;
      const canBid = this.currentPlayerId && canAfford && minBid <= (this.gameState.players.find((p: any) => p.id === this.currentPlayerId)?.cash || 0);

      return `
        <div class="action-buttons">
          <button class="action-btn bid-btn"
                  data-action="bid"
                  data-company-order="${company.order}"
                  data-min-bid="${minBid}"
                  ${!canBid ? 'disabled' : ''}>
            ${canBid ? `📢 Bid (min $${minBid})` : 'Cannot Bid'}
          </button>
        </div>
      `;
    }
  }

  private setupEventListeners() {
    if (!this.element) return;

    // Buy buttons
    this.element.querySelectorAll('.buy-btn').forEach(button => {
      button.addEventListener('click', () => {
        const order = parseInt((button as HTMLElement).dataset.companyOrder || '0');
        this.makeMove('BUY', order, 0);
      });
    });

    // Pass buttons
    this.element.querySelectorAll('.pass-btn').forEach(button => {
      button.addEventListener('click', () => {
        const order = parseInt((button as HTMLElement).dataset.companyOrder || '0');
        this.makeMove('PASS', order, 0);
      });
    });

    // Bid buttons
    this.element.querySelectorAll('.bid-btn').forEach(button => {
      button.addEventListener('click', () => {
        const order = parseInt((button as HTMLElement).dataset.companyOrder || '0');
        const minBid = parseInt((button as HTMLElement).dataset.minBid || '0');

        // Prompt for bid amount
        const bidAmount = prompt(`Enter your bid amount (minimum $${minBid}):`);
        if (bidAmount) {
          const amount = parseInt(bidAmount);
          if (amount >= minBid) {
            this.makeMove('BID', order, amount);
          } else {
            alert(`Bid must be at least $${minBid}`);
          }
        }
      });
    });
  }

  private makeMove(moveType: string, companyOrder: number, bidAmount: number) {
    if (!this.currentPlayerId) {
      alert('You are not a player in this game');
      return;
    }

    const moveData = {
      move_type: moveType,
      private_company_order: companyOrder,
      player_id: this.currentPlayerId,
      bid_amount: bidAmount
    };

    console.log('Making move:', moveData);

    if (this.onMakeMove) {
      this.onMakeMove(moveData);
    }
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
