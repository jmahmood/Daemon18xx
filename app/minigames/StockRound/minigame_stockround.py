from functools import reduce
from typing import List, Optional

from app.base import PublicCompany, StockPurchaseSource, Player, err, MutableGameState, STOCK_CERTIFICATE, \
    STOCK_PRESIDENT_CERTIFICATE
from app.logging_config import get_logger
from app.minigames.StockRound.const import (
    VALID_CERTIFICATE_COUNT,
    VALID_IPO_PRICES,
    ALL_AVAILABLE_STOCK,
    BANK_POOL_LIMIT,
)
from app.minigames.StockRound.enums import StockRoundType
from app.minigames.StockRound.move import StockRoundMove
from app.minigames.base import Minigame

logger = get_logger(__name__)


class StockRound(Minigame):
    """Buy / Sell Public Companies, Private Companies"""

    def __init__(self) -> None:
        super().__init__()
        self.sell_private_company_auction = False
        self.last_deal_player: Optional[Player] = None

    def _buyround(self, move: StockRoundMove, kwargs: MutableGameState) -> None:
        purchase_amount = STOCK_CERTIFICATE

        if self.isFirstPurchase(move):
            purchase_amount = STOCK_PRESIDENT_CERTIFICATE
            move.public_company.setPresident(move.player)
            move.public_company.setInitialPrice(move.ipo_price)

        move.public_company.buy(move.player, move.source, purchase_amount)
        move.public_company.checkPresident()
        move.public_company.checkFloated()

        purchase_history = kwargs.purchases[kwargs.stock_round_count]
        try:
            purchase_history[move.player].append(move.public_company)
        except KeyError:
            purchase_history[move.player] = [move.public_company]

    def _sellround(self, move: StockRoundMove, kwargs: MutableGameState) -> None:
        """Execute stock sales and pay the player.

        CRITICAL: Player must be paid BEFORE price drops, since payment
        is based on current market price.
        """
        sale_history = kwargs.sales[kwargs.stock_round_count]
        for company, amount in move.for_sale:
            # Calculate payment BEFORE selling (price may drop)
            price_per_share = company.stockPrice[StockPurchaseSource.BANK]
            # amount is in percentage (10, 20, etc.), divide by 10 to get number of shares
            num_shares = amount // STOCK_CERTIFICATE
            payment = num_shares * price_per_share

            logger.debug(
                f"💰 Selling {amount}% of {company.short_name}",
                extra={
                    'company': company.short_name,
                    'amount': amount,
                    'price_per_share': price_per_share,
                    'num_shares': num_shares,
                    'payment': payment,
                    'player_cash_before': move.player.cash
                }
            )

            # Update ownership and bank pool
            company.sell(move.player, amount)

            # PAY THE PLAYER (critical fix!)
            move.player.cash += payment

            # Price drops after sale
            company.priceDown(amount)

            # Check for president change
            company.checkPresident()

            # Track that player sold this company this round
            move.player.sold_this_round.add(company)

            logger.debug(
                f"💰 Sale completed",
                extra={
                    'player_cash_after': move.player.cash,
                    'cash_gained': payment
                }
            )

            try:
                sale_history[move.player].append(company)
            except KeyError:
                sale_history[move.player] = [company]

    def _buysell(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        """Execute sell-then-buy action.

        CRITICAL: Must SELL FIRST, then BUY, so player can use sale proceeds
        to fund the purchase. This is standard 18xx rules.
        """
        if not self.validateBuy(move, kwargs) or not self.validateSales(move, kwargs):
            return False
        elif self.isFirstPurchase(move) and not self.validateFirstPurchase(move):
            return False

        logger.debug(
            f"🔄 BUYSELL: Selling first, then buying",
            extra={'player_cash_before': move.player.cash}
        )

        # SELL FIRST (so player gets cash)
        self._sellround(move, kwargs)

        logger.debug(
            f"🔄 BUYSELL: After sell, before buy",
            extra={'player_cash_after_sell': move.player.cash}
        )

        # BUY SECOND (using proceeds from sale)
        self._buyround(move, kwargs)

        logger.debug(
            f"🔄 BUYSELL: Completed",
            extra={'player_cash_final': move.player.cash}
        )

        kwargs.stock_round_play += 1
        self.last_deal_player = move.player
        return True

    def _buy(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        logger.debug(
            f"🎲 _buy() called",
            extra={
                'player_id': move.player_id,
                'company_id': move.public_company_id,
                'source': move.source,
                'ipo_price': move.ipo_price
            }
        )

        if not self.validateBuy(move, kwargs):
            logger.debug(f"🎲 validateBuy failed: {self.errors()}")
            return False
        elif self.isFirstPurchase(move) and not self.validateFirstPurchase(move):
            logger.debug(f"🎲 validateFirstPurchase failed: {self.errors()}")
            return False

        logger.debug(f"🎲 Validation passed, executing _buyround()")
        self._buyround(move, kwargs)
        kwargs.stock_round_play += 1
        self.last_deal_player = move.player

        logger.debug(
            f"🎲 _buy() completed successfully",
            extra={
                'stock_round_play': kwargs.stock_round_play,
                'player_cash': move.player.cash
            }
        )
        return True

    def _sell(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        if not self.validateSales(move, kwargs):
            return False
        self._sellround(move, kwargs)
        kwargs.stock_round_play += 1
        self.last_deal_player = move.player
        return True

    def run(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        logger.debug(
            f"🎲 StockRound.run() called",
            extra={
                'move_type': move.move_type,
                'player_id': move.player_id,
                'stock_round_count': getattr(kwargs, 'stock_round_count', 'NOT_SET'),
                'stock_round_play': getattr(kwargs, 'stock_round_play', 'NOT_SET')
            }
        )

        move.backfill(kwargs)

        if StockRoundType(move.move_type) == StockRoundType.BUYSELL:
            result = self._buysell(move, kwargs)
            logger.debug(f"🎲 BUYSELL result: {result}")
            return result

        elif StockRoundType(move.move_type) == StockRoundType.BUY:
            result = self._buy(move, kwargs)
            logger.debug(f"🎲 BUY result: {result}")
            return result

        elif StockRoundType(move.move_type) == StockRoundType.SELL:
            result = self._sell(move, kwargs)
            logger.debug(f"🎲 SELL result: {result}")
            return result

        if StockRoundType.PASS == StockRoundType(move.move_type):
            if self.validatePass(move, kwargs):
                kwargs.stock_round_play += 1
                kwargs.stock_round_passed += 1
                logger.debug(f"🎲 PASS successful - play: {kwargs.stock_round_play}, passed: {kwargs.stock_round_passed}")
                return True
            logger.debug(f"🎲 PASS validation failed")
            return False

        if StockRoundType.SELL_PRIVATE_COMPANY == StockRoundType(move.move_type):
            if not self.validateSellPrivateCompany(move, kwargs):
                logger.debug(f"🎲 SELL_PRIVATE_COMPANY validation failed")
                return False

            # Initialize the auction state for the private company sale
            kwargs.auctioned_private_company = move.private_company
            kwargs.auction = []
            self.sell_private_company_auction = True
            # Note: stock_round_play is NOT incremented here; the auction decision will increment it
            logger.debug(f"🎲 SELL_PRIVATE_COMPANY successful")
            return True

        logger.debug(f"🎲 Unknown move_type: {move.move_type}")
        return False

    def next(self, kwargs: MutableGameState) -> str:
        players: List[Player] = kwargs.players
        if self.sell_private_company_auction:
            kwargs.auction = []
            return "Auction"
        if kwargs.stock_round_play % len(players) == 0 \
                and kwargs.stock_round_play > 0 \
                and kwargs.stock_round_passed == len(players):
            if self.last_deal_player:
                idx = players.index(self.last_deal_player)
                kwargs.priority_deal_player = players[(idx + 1) % len(players)]
            return "OperatingRound1"
        return "StockRound"

    @staticmethod
    def onStart(kwargs: MutableGameState) -> None:
        """Initialize the Stock Round state.

        NOTE: stock_round_count is 0-indexed (first round = 0)
        This allows direct array indexing: purchases[stock_round_count]
        """
        logger.info(
            f"🎲 Stock Round starting",
            extra={
                'stock_round_count': kwargs.stock_round_count,
                'stock_round_play': kwargs.stock_round_play
            }
        )

        # Initialize purchases and sales tracking for this round
        # NOTE: We use 0-indexing, so first round (stock_round_count=0) uses index 0
        kwargs.purchases.append({})
        kwargs.sales.append({})

        # Reset round state
        kwargs.stock_round_passed = 0
        kwargs.stock_round_play = 0

        logger.info(
            f"🎲 Stock Round initialized",
            extra={
                'stock_round_count': kwargs.stock_round_count,
                'round_number_display': kwargs.stock_round_count + 1,  # Display as 1, 2, 3...
                'purchases_length': len(kwargs.purchases),
                'sales_length': len(kwargs.sales)
            }
        )

    @staticmethod
    def onComplete(kwargs: MutableGameState) -> None:
        """Transitioning out of the stock round: increment stock values."""
        Minigame.onComplete(kwargs)

        public_companies: List[PublicCompany] = kwargs.public_companies
        for pc in public_companies:
            pc.checkPriceIncrease()

        # Reset sell restrictions for next stock round
        for player in kwargs.players:
            player.sold_this_round = set()

        # Increment stock round count for next round
        kwargs.stock_round_count += 1
        logger.info(
            f"🎲 Stock Round completed, advancing to round {kwargs.stock_round_count + 1}",
            extra={'stock_round_count': kwargs.stock_round_count}
        )

    @staticmethod
    def onTurnComplete(kwargs: MutableGameState):
        """Called after each turn completes (not the whole round)."""
        Minigame.onTurnComplete(kwargs)

    def validateBuy(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        number_of_total_players = len(kwargs.players)
        player_certificates = move.player.getCertificateCount()
        cost_of_stock = move.public_company.checkPrice(
            move.source,
            STOCK_CERTIFICATE,
            move.ipo_price)

        certs_needed = 2 if self.isFirstPurchase(move) else 1
        my_sales = kwargs.sales[kwargs.stock_round_count].get(move.player, [])

        return self.validate([
            err(
                move.public_company not in move.player.sold_this_round,
                "You can't buy from a company you sold this round {} {}",
                move.public_company.id, move.public_company.name),
            err(
                player_certificates + certs_needed <= VALID_CERTIFICATE_COUNT[number_of_total_players],
                "You have too many certificates. There are {} players, and you are allowed a "
                "total of {} certificates.  You own {} certificates and would have too many if you bought more.",
                number_of_total_players,
                VALID_CERTIFICATE_COUNT[number_of_total_players],
                player_certificates),
            err(
                move.player.hasStock(move.public_company) +
                (STOCK_PRESIDENT_CERTIFICATE if self.isFirstPurchase(move) else STOCK_CERTIFICATE)
                <= 60,
                "You can't own more than 60% of a company {} {}",
                move.public_company.id, move.public_company.name),
            err(
                move.public_company.hasStock(move.source, STOCK_CERTIFICATE),
                "The company does not have enough stock in category {}",
                move.source),
            err(
                move.player.hasEnoughMoney(cost_of_stock),
                "You cannot afford poorboi. {} (You have: {})",
                cost_of_stock, move.player.cash),
        ])

    def _validateSale(self, player: Player, company: PublicCompany, amount: int, kwargs: MutableGameState):
        """You can't sell stocks you bought in previous rounds."""
        my_purchases = kwargs.purchases[kwargs.stock_round_count].get(player, [])

        my_stock = player.hasStock(company)
        potential_owners = company.potentialPresidents()

        validations = [
            err(company not in my_purchases,
                "You can't sell something you already bought: {} {}",
                company.id, company.short_name),

            err(
                my_stock >= amount,
                "You must have as much stock than you are trying to sell {}",
                amount
            ),

            err(
                company.availableStock(StockPurchaseSource.BANK) + amount
                <= BANK_POOL_LIMIT,
                "You can't sell that much ({}); the bank can only have {} shares max.",
                amount,
                BANK_POOL_LIMIT,
            ),

            err(
                len(company.potentialPresidents() - {player}) > 0 or my_stock - amount >= 20,
                "There are no other potential presidents, so you can't sell your shares. {} / {} (original stock: {})",
                ",".join([p.id for p in company.potentialPresidents()]),
                company.name,
                str(company.owners.get(player))

            ),

            err(amount % STOCK_CERTIFICATE == 0,
                "You can only sell in units of 10 stocks ({})".format(amount),
                ),

            err(kwargs.stock_round_count >= 1,
                "You can only sell after the first stock round. (Currently in round {})".format(kwargs.stock_round_count + 1))
        ]

        return self.validate(validations)

    def validateSales(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        """Used in situations where there are multiple companies that are performing a sale."""
        data = [self._validateSale(move.player, company, amount, kwargs)
                for company, amount in move.for_sale]

        return reduce(
            lambda x, y: x and y,
            data
        )

    def validatePass(self, move: StockRoundMove, kwargs: MutableGameState):
        # As long as you are a player, you can pass
        return True

    def validateSellPrivateCompany(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        """Validate that a player can initiate a private company auction."""
        return self.validate([
            err(
                kwargs.stock_round_count >= 1,
                "You can't sell a private company in the first stock round. (Currently in round {})".format(kwargs.stock_round_count + 1)
            ),
            err(
                move.private_company is not None,
                "Invalid private company specified."
            ),
            err(
                move.private_company.belongs_to == move.player,
                "You can't sell a private company you don't own. Company {} belongs to {}.",
                move.private_company.name if move.private_company else "Unknown",
                move.private_company.belongs_to.name if move.private_company and move.private_company.belongs_to else "nobody"
            ),
        ])

    def validateFirstPurchase(self, move: StockRoundMove) -> bool:
        cost_of_stock = move.public_company.checkPrice(move.source, STOCK_PRESIDENT_CERTIFICATE, move.ipo_price)
        valid_ipo_prices = ",".join([str(p) for p in VALID_IPO_PRICES])

        return self.validate([
            err(move.ipo_price in VALID_IPO_PRICES,
                "Invalid IPO Price ({}).  Valid prices are {}.",
                move.ipo_price, valid_ipo_prices
                ),
            err(move.source == StockPurchaseSource.IPO,
                "You need to purchase stock from the IPO as this is an initial purchase", ),
            err(move.player.hasEnoughMoney(cost_of_stock),
                "You cannot afford to be president poorboi. {} (You have: {})",
                cost_of_stock, move.player.cash, )]
        )

    def isFirstPurchase(self, move: StockRoundMove) -> bool:
        # When a company is first purchased, all 100% of the stock is owned by the IPO pile.
        return move.public_company.availableStock(StockPurchaseSource.IPO) == ALL_AVAILABLE_STOCK
