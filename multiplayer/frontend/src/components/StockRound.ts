/**
 * Stock Round component
 * Handles BUY, SELL, BUYSELL, and PASS moves for the stock round phase
 */

export class StockRound {
  private element: HTMLElement | null = null;
  private gameState: any = null;
  private currentPlayerId: string | null = null;
  private onMakeMove?: (moveData: any) => void;

  constructor(options: { onMakeMove?: (moveData: any) => void }) {
    this.onMakeMove = options.onMakeMove;
  }

  render(): HTMLElement {
    const container = document.createElement('div');
    container.className = 'stock-round-container';
    container.id = 'stock-round';

    container.innerHTML = `
      <div class="stock-round-header">
        <h2>📈 Stock Round</h2>
        <p class="instruction">Buy or sell shares of public companies. Each player may take one action per turn.</p>
      </div>

      <div class="turn-indicator" id="stock-turn-indicator" style="margin-bottom: 20px;">
        <p style="text-align: center; color: var(--text-secondary);">
          Waiting for game data...
        </p>
      </div>

      <div id="stock-holdings-panel" style="margin-bottom: 20px;"></div>

      <div id="stock-companies-grid"></div>

      <div id="stock-action-area" style="margin-top: 20px;"></div>
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
    this.updateHoldingsPanel();
    this.updateCompaniesGrid();
    this.updateActionArea();
  }

  private updateTurnIndicator() {
    const indicator = this.element?.querySelector('#stock-turn-indicator');
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

  private updateHoldingsPanel() {
    const panel = this.element?.querySelector('#stock-holdings-panel');
    if (!panel || !this.gameState) return;

    const players = this.gameState.players || [];
    const currentPlayer = players.find((p: any) => p.id === this.currentPlayerId);

    if (!currentPlayer) {
      panel.innerHTML = '';
      return;
    }

    const holdings = currentPlayer.holdings || {};
    const publicCompanies = this.gameState.public_companies || [];

    let html = '<div class="holdings-panel">';
    html += '<h3 style="margin-bottom: 15px;">💼 Your Stock Holdings</h3>';

    const holdingEntries = Object.entries(holdings);
    if (holdingEntries.length === 0) {
      html += '<p style="color: var(--text-secondary); font-size: 14px;">You don\'t own any shares yet.</p>';
    } else {
      holdingEntries.forEach(([companyShortName, amount]: [string, any]) => {
        const company = publicCompanies.find((c: any) => c.short_name === companyShortName);
        const isPresident = company && company.president_id === this.currentPlayerId;

        html += `
          <div class="holding-item">
            <div>
              <strong>${this.escapeHtml(companyShortName)}</strong>: ${amount}%
              ${isPresident ? '<span class="president-badge">PRESIDENT</span>' : ''}
            </div>
            <div style="color: var(--text-secondary); font-size: 12px;">
              ${company ? company.name : ''}
            </div>
          </div>
        `;
      });
    }

    html += `
      <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--border-color);">
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
          <span>Certificates:</span>
          <strong>${currentPlayer.certificates || 0} / 20</strong>
        </div>
        <div style="display: flex; justify-content: space-between;">
          <span>Cash:</span>
          <strong style="color: var(--success-color);">$${currentPlayer.cash || 0}</strong>
        </div>
      </div>
    `;

    html += '</div>';
    panel.innerHTML = html;
  }

  private updateCompaniesGrid() {
    const grid = this.element?.querySelector('#stock-companies-grid');
    if (!grid || !this.gameState) return;

    const publicCompanies = this.gameState.public_companies || [];
    const players = this.gameState.players || [];
    const currentPlayer = players.find((p: any) => p.id === this.currentPlayerId);
    const playerCash = currentPlayer?.cash || 0;

    let html = '<div class="companies-section">';
    html += '<h3 style="margin-bottom: 15px;">🏢 Public Companies</h3>';
    html += '<div class="companies-grid">';

    publicCompanies.forEach((company: any) => {
      const isFloated = company.floated;
      const isStarted = company.ipo_price > 0;

      html += `
        <div class="company-card ${!isStarted ? 'not-started' : ''} ${isFloated ? 'floated' : ''}">
          <div class="company-header">
            <span class="company-short-name">${this.escapeHtml(company.short_name)}</span>
            ${isFloated ? '<span style="font-size: 12px; color: var(--success-color);">✓ Floated</span>' : ''}
          </div>

          <div class="company-name">${this.escapeHtml(company.name)}</div>

          ${this.renderCompanyInfo(company)}

          <div style="margin-top: 10px; font-size: 12px; color: var(--text-secondary);">
            ${company.president ? `President: ${this.escapeHtml(company.president)}` : 'No President'}
          </div>

          ${this.renderShareholderInfo(company)}

          <div class="stock-actions" id="stock-actions-${company.id}">
            ${this.renderCompanyActions(company, playerCash)}
          </div>
        </div>
      `;
    });

    html += '</div></div>';
    grid.innerHTML = html;
    this.setupCompanyEventListeners();
  }

  private renderCompanyInfo(company: any): string {
    const isStarted = company.ipo_price > 0;
    const ipoShares = company.ipo_shares || 0;
    const bankShares = company.bank_shares || 0;
    const ipoPrice = company.ipo_price || 0;
    const marketPrice = company.market_price || 0;

    if (!isStarted) {
      return `
        <div style="margin: 10px 0; padding: 10px; background: var(--background-secondary); border-radius: 6px;">
          <div style="font-size: 13px; color: var(--text-secondary);">Not yet started</div>
          <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
            President's certificate: 20%
          </div>
        </div>
      `;
    }

    const ipoCerts = ipoShares / 10;
    const bankCerts = bankShares / 10;
    const outstandingShares = company.outstanding_shares || 0;
    const floatPercent = outstandingShares;

    return `
      <div style="margin: 10px 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; padding: 8px; background: var(--background-secondary); border-radius: 6px;">
          <div>
            <div style="font-size: 11px; color: var(--text-secondary);">IPO</div>
            <div style="font-size: 14px; font-weight: 600; color: var(--success-color);">$${ipoPrice}</div>
            <div style="font-size: 11px; color: var(--text-secondary);">${ipoCerts} certs (${ipoShares}%)</div>
          </div>
          <div>
            <div style="font-size: 11px; color: var(--text-secondary);">Bank Pool</div>
            <div style="font-size: 14px; font-weight: 600; color: var(--warning-color);">$${marketPrice}</div>
            <div style="font-size: 11px; color: var(--text-secondary);">${bankCerts} certs (${bankShares}%)</div>
          </div>
        </div>
        <div style="padding: 8px; background: var(--background-tertiary); border-radius: 6px; margin-bottom: 8px;">
          <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">Status:</div>
          <div style="font-size: 13px;">
            <strong>${floatPercent}% sold</strong>
            ${company.floated ?
              '<span style="color: var(--success-color); margin-left: 8px;">✓ Floated</span>' :
              `<span style="color: var(--text-secondary); margin-left: 8px;">(${50 - floatPercent}% needed to float)</span>`
            }
          </div>
        </div>
        ${company.cash !== undefined ? `
          <div style="font-size: 12px; color: var(--text-secondary);">
            Treasury: $${company.cash}
          </div>
        ` : ''}
      </div>
    `;
  }

  private renderShareholderInfo(company: any): string {
    if (!company.shareholders || Object.keys(company.shareholders).length === 0) {
      return '';
    }

    let html = '<div style="margin-top: 8px; padding: 8px; background: var(--background-secondary); border-radius: 6px;">';
    html += '<div style="font-size: 11px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">SHAREHOLDERS:</div>';

    Object.entries(company.shareholders).forEach(([playerName, amount]: [string, any]) => {
      html += `
        <div style="font-size: 12px; color: var(--text-primary);">
          ${this.escapeHtml(playerName)}: ${amount}%
        </div>
      `;
    });

    html += '</div>';
    return html;
  }

  private renderCompanyActions(company: any, playerCash: number): string {
    const currentPlayer = this.gameState.current_player;
    const isMyTurn = currentPlayer && currentPlayer.id === this.currentPlayerId;

    if (!isMyTurn) {
      return '';
    }

    const isStarted = company.ipo_price > 0;
    const ipoShares = company.ipo_shares || 0;
    const bankShares = company.bank_shares || 0;
    const ipoPrice = company.ipo_price || 0;
    const marketPrice = company.market_price || 0;

    if (!isStarted) {
      // Not started - can only start as president
      return `
        <button class="stock-btn start-company-btn"
                data-company-id="${company.id}">
          🚀 Start Company
        </button>
      `;
    }

    let html = '';

    // Can buy from IPO if shares available
    if (ipoShares > 0) {
      const canAfford = playerCash >= ipoPrice;
      html += `
        <button class="stock-btn buy-stock-btn"
                data-company-id="${company.id}"
                data-source="IPO"
                data-price="${ipoPrice}"
                ${!canAfford ? 'disabled' : ''}>
          ${canAfford ? `Buy IPO $${ipoPrice}` : 'Cannot Afford'}
        </button>
      `;
    }

    // Can buy from Bank if shares available
    if (bankShares > 0) {
      const canAfford = playerCash >= marketPrice;
      html += `
        <button class="stock-btn buy-stock-btn"
                data-company-id="${company.id}"
                data-source="BANK"
                data-price="${marketPrice}"
                ${!canAfford ? 'disabled' : ''}>
          ${canAfford ? `Buy Bank $${marketPrice}` : 'Cannot Afford'}
        </button>
      `;
    }

    if (!html) {
      html = '<div style="font-size: 12px; color: var(--text-secondary); text-align: center;">No shares available</div>';
    }

    return html;
  }

  private updateActionArea() {
    const actionArea = this.element?.querySelector('#stock-action-area');
    if (!actionArea || !this.gameState) return;

    const currentPlayer = this.gameState.current_player;
    const isMyTurn = currentPlayer && currentPlayer.id === this.currentPlayerId;

    if (!isMyTurn) {
      actionArea.innerHTML = '';
      return;
    }

    const players = this.gameState.players || [];
    const myPlayer = players.find((p: any) => p.id === this.currentPlayerId);
    const myHoldings = myPlayer?.holdings || {};
    const hasStocks = Object.keys(myHoldings).length > 0;

    let html = '<div class="action-panel">';
    html += '<h3 style="margin-bottom: 15px;">⚡ Actions</h3>';
    html += '<div class="action-buttons-grid">';

    if (hasStocks) {
      html += `
        <button class="action-btn-large sell-stock-btn" id="sell-action-btn">
          📉 Sell Stock
        </button>
      `;
    }

    html += `
      <button class="action-btn-large pass-action-btn" id="pass-action-btn">
        ⏭️ Pass
      </button>
    `;

    html += '</div></div>';
    actionArea.innerHTML = html;
    this.setupActionEventListeners();
  }

  private setupCompanyEventListeners() {
    if (!this.element) return;

    // Start company buttons
    this.element.querySelectorAll('.start-company-btn').forEach(button => {
      button.addEventListener('click', () => {
        const companyId = (button as HTMLElement).dataset.companyId;
        if (companyId) {
          this.showStartCompanyModal(companyId);
        }
      });
    });

    // Buy stock buttons
    this.element.querySelectorAll('.buy-stock-btn').forEach(button => {
      button.addEventListener('click', () => {
        const companyId = (button as HTMLElement).dataset.companyId;
        const source = (button as HTMLElement).dataset.source;
        const price = parseInt((button as HTMLElement).dataset.price || '0');

        if (companyId && source) {
          this.showBuyStockModal(companyId, source, price);
        }
      });
    });
  }

  private setupActionEventListeners() {
    if (!this.element) return;

    // Sell button
    const sellBtn = this.element.querySelector('#sell-action-btn');
    if (sellBtn) {
      sellBtn.addEventListener('click', () => {
        this.showSellStockModal();
      });
    }

    // Pass button
    const passBtn = this.element.querySelector('#pass-action-btn');
    if (passBtn) {
      passBtn.addEventListener('click', () => {
        this.confirmPass();
      });
    }
  }

  private showStartCompanyModal(companyId: string) {
    const publicCompanies = this.gameState.public_companies || [];
    const company = publicCompanies.find((c: any) => c.id === companyId);

    if (!company) return;

    // Available IPO prices based on stock market (simplified for now)
    const availablePrices = [100, 90, 82, 76, 71, 67];

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal">
        <div class="modal-header">
          <h2 class="modal-title">🚀 Start ${this.escapeHtml(company.name)}</h2>
        </div>
        <div class="modal-body">
          <p style="margin-bottom: 20px;">
            You will become President and receive the President's certificate (20% ownership).
          </p>

          <div class="form-group">
            <label class="form-label">Select IPO Price:</label>
            <select id="ipo-price-select" class="form-input">
              ${availablePrices.map(price => `
                <option value="${price}">$${price}</option>
              `).join('')}
            </select>
          </div>

          <div style="margin-top: 15px; padding: 15px; background: var(--background-tertiary); border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <span>President's Certificate:</span>
              <strong>20%</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span>Total Cost:</span>
              <strong id="total-cost" style="color: var(--success-color);">$200</strong>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button id="confirm-start-btn">Confirm Start</button>
          <button id="cancel-start-btn" style="background: var(--text-secondary);">Cancel</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const priceSelect = modal.querySelector('#ipo-price-select') as HTMLSelectElement;
    const totalCostEl = modal.querySelector('#total-cost');

    priceSelect.addEventListener('change', () => {
      const price = parseInt(priceSelect.value);
      const totalCost = price * 2; // President cert is 20% = 2 shares at 10% each
      if (totalCostEl) {
        totalCostEl.textContent = `$${totalCost}`;
      }
    });

    modal.querySelector('#confirm-start-btn')?.addEventListener('click', () => {
      const ipoPrice = parseInt(priceSelect.value);
      this.makeMove({
        move_type: 'BUY',
        player_id: this.currentPlayerId,
        public_company_id: companyId,
        source: 'IPO',
        ipo_price: ipoPrice
      });
      modal.remove();
    });

    modal.querySelector('#cancel-start-btn')?.addEventListener('click', () => {
      modal.remove();
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });
  }

  private showBuyStockModal(companyId: string, source: string, price: number) {
    const publicCompanies = this.gameState.public_companies || [];
    const company = publicCompanies.find((c: any) => c.id === companyId);

    if (!company) return;

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal">
        <div class="modal-header">
          <h2 class="modal-title">📈 Buy Stock - ${this.escapeHtml(company.name)}</h2>
        </div>
        <div class="modal-body">
          <div style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <span>Company:</span>
              <strong>${this.escapeHtml(company.short_name)}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <span>Source:</span>
              <strong>${source}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <span>Amount:</span>
              <strong>10% (1 certificate)</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span>Price per share:</span>
              <strong style="color: var(--success-color);">$${price}</strong>
            </div>
          </div>

          <div style="padding: 15px; background: var(--background-tertiary); border-radius: 8px;">
            <div style="display: flex; justify-content: space-between;">
              <span style="font-size: 16px;">Total Cost:</span>
              <strong style="font-size: 18px; color: var(--success-color);">$${price}</strong>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button id="confirm-buy-btn">Confirm Purchase</button>
          <button id="cancel-buy-btn" style="background: var(--text-secondary);">Cancel</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('#confirm-buy-btn')?.addEventListener('click', () => {
      this.makeMove({
        move_type: 'BUY',
        player_id: this.currentPlayerId,
        public_company_id: companyId,
        source: source
      });
      modal.remove();
    });

    modal.querySelector('#cancel-buy-btn')?.addEventListener('click', () => {
      modal.remove();
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });
  }

  private showSellStockModal() {
    const players = this.gameState.players || [];
    const currentPlayer = players.find((p: any) => p.id === this.currentPlayerId);
    const holdings = currentPlayer?.holdings || {};
    const publicCompanies = this.gameState.public_companies || [];

    if (Object.keys(holdings).length === 0) {
      alert('You don\'t own any shares to sell.');
      return;
    }

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';

    let companiesHtml = '';
    Object.entries(holdings).forEach(([companyShortName, amount]: [string, any]) => {
      const company = publicCompanies.find((c: any) => c.short_name === companyShortName);
      const isPresident = company && company.president_id === this.currentPlayerId;
      const marketPrice = company?.market_price || 0;

      // Can only sell if not president OR if president with more than 20%
      const canSell = !isPresident || amount > 20;

      companiesHtml += `
        <div style="padding: 12px; background: var(--background-tertiary); border-radius: 8px; margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div>
              <strong>${this.escapeHtml(companyShortName)}</strong>
              ${isPresident ? ' <span class="president-badge">PRESIDENT</span>' : ''}
            </div>
            <div style="color: var(--text-secondary);">You own: ${amount}%</div>
          </div>
          ${canSell ? `
            <div>
              <label style="display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" class="sell-checkbox" data-company="${companyShortName}" data-price="${marketPrice}">
                <span>Sell 10% @ $${marketPrice} = $${marketPrice}</span>
              </label>
            </div>
          ` : `
            <div style="font-size: 12px; color: var(--danger-color);">
              Cannot sell President's certificate
            </div>
          `}
        </div>
      `;
    });

    modal.innerHTML = `
      <div class="modal">
        <div class="modal-header">
          <h2 class="modal-title">📉 Sell Stock</h2>
        </div>
        <div class="modal-body">
          <p style="margin-bottom: 15px; color: var(--text-secondary);">
            Select shares to sell:
          </p>

          ${companiesHtml}

          <div style="margin-top: 15px; padding: 15px; background: var(--background-secondary); border-radius: 8px;">
            <div style="display: flex; justify-content: space-between;">
              <span style="font-size: 16px;">Total Proceeds:</span>
              <strong id="total-proceeds" style="font-size: 18px; color: var(--success-color);">$0</strong>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button id="confirm-sell-btn">Confirm Sale</button>
          <button id="cancel-sell-btn" style="background: var(--text-secondary);">Cancel</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const updateTotal = () => {
      const checkboxes = modal.querySelectorAll('.sell-checkbox:checked');
      let total = 0;
      checkboxes.forEach((checkbox) => {
        const price = parseInt((checkbox as HTMLInputElement).dataset.price || '0');
        total += price;
      });
      const totalEl = modal.querySelector('#total-proceeds');
      if (totalEl) {
        totalEl.textContent = `$${total}`;
      }
    };

    modal.querySelectorAll('.sell-checkbox').forEach(checkbox => {
      checkbox.addEventListener('change', updateTotal);
    });

    modal.querySelector('#confirm-sell-btn')?.addEventListener('click', () => {
      const checkboxes = modal.querySelectorAll('.sell-checkbox:checked');
      if (checkboxes.length === 0) {
        alert('Please select at least one stock to sell.');
        return;
      }

      const forSaleRaw: [string, number][] = [];
      checkboxes.forEach((checkbox) => {
        const company = (checkbox as HTMLInputElement).dataset.company;
        if (company) {
          forSaleRaw.push([company, 10]); // Selling 10% at a time
        }
      });

      this.makeMove({
        move_type: 'SELL',
        player_id: this.currentPlayerId,
        for_sale_raw: forSaleRaw
      });
      modal.remove();
    });

    modal.querySelector('#cancel-sell-btn')?.addEventListener('click', () => {
      modal.remove();
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });
  }

  private confirmPass() {
    if (confirm('Are you sure you want to pass your turn?')) {
      this.makeMove({
        move_type: 'PASS',
        player_id: this.currentPlayerId
      });
    }
  }

  private makeMove(moveData: any) {
    console.log('Making stock round move:', moveData);

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
