/**
 * Private Company Auction component
 * Displays available private companies and allows players to buy them
 */

export class PrivateCompanyAuction {
  private element: HTMLElement | null = null;
  private gameState: any = null;
  private onBuyCompany?: (companyName: string) => void;

  constructor(options: {
    onBuyCompany?: (companyName: string) => void;
  }) {
    this.onBuyCompany = options.onBuyCompany;
  }

  render(): HTMLElement {
    const container = document.createElement('div');
    container.className = 'auction-container';
    container.id = 'private-auction';

    container.innerHTML = `
      <div class="auction-header">
        <h2>🏢 Private Company Auction</h2>
        <p class="instruction">Purchase private companies. They provide revenue and special abilities.</p>
      </div>

      <div class="auction-companies" id="auction-companies">
        <p style="text-align: center; color: var(--text-secondary);">
          Waiting for game data...
        </p>
      </div>
    `;

    this.element = container;
    return container;
  }

  updateGameState(gameState: any) {
    this.gameState = gameState;
    this.refresh();
  }

  private refresh() {
    if (!this.element || !this.gameState) return;

    const companiesContainer = this.element.querySelector('#auction-companies');
    if (!companiesContainer) return;

    const privateCompanies = this.gameState.private_companies || [];
    const currentPlayer = this.gameState.current_player;
    const players = this.gameState.players || [];

    // Find current player's cash
    let playerCash = 0;
    if (currentPlayer) {
      const player = players.find((p: any) => p.id === currentPlayer.id);
      if (player) {
        playerCash = player.cash;
      }
    }

    if (privateCompanies.length === 0) {
      companiesContainer.innerHTML = '<p style="text-align: center;">No private companies available.</p>';
      return;
    }

    // Group companies by availability
    const available = privateCompanies.filter((pc: any) => !pc.owner);
    const sold = privateCompanies.filter((pc: any) => pc.owner);

    let html = '';

    if (available.length > 0) {
      html += '<div class="company-section">';
      html += '<h3 style="margin-bottom: 15px;">Available</h3>';
      html += '<div class="company-grid">';

      available.forEach((pc: any) => {
        const canAfford = playerCash >= pc.cost;
        html += `
          <div class="company-card ${canAfford ? '' : 'unaffordable'}">
            <div class="company-header">
              <span class="company-short-name">${this.escapeHtml(pc.short_name)}</span>
              <span class="company-cost">$${pc.cost}</span>
            </div>
            <div class="company-name">${this.escapeHtml(pc.name)}</div>
            <div class="company-revenue">Revenue: $${pc.revenue}</div>
            ${currentPlayer ? `
              <button class="buy-company-btn"
                      data-company="${this.escapeHtml(pc.short_name)}"
                      ${!canAfford ? 'disabled' : ''}>
                ${canAfford ? 'Buy' : 'Cannot Afford'}
              </button>
            ` : ''}
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

    // Add event listeners to buy buttons
    this.setupEventListeners();
  }

  private setupEventListeners() {
    if (!this.element) return;

    const buyButtons = this.element.querySelectorAll('.buy-company-btn');
    buyButtons.forEach(button => {
      button.addEventListener('click', () => {
        const companyName = (button as HTMLElement).dataset.company;
        if (companyName && this.onBuyCompany) {
          this.onBuyCompany(companyName);
        }
      });
    });
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
