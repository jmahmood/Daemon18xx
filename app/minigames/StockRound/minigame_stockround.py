from functools import reduce
from typing import List

import logging

from app.base import PublicCompany, StockPurchaseSource, Player, err, MutableGameState, STOCK_CERTIFICATE, \
    STOCK_PRESIDENT_CERTIFICATE
from app.minigames.StockRound.const import VALID_CERTIFICATE_COUNT, VALID_IPO_PRICES, ALL_AVAILABLE_STOCK
from app.minigames.StockRound.enums import StockRoundType
from app.minigames.StockRound.move import StockRoundMove
from app.minigames.base import Minigame, MinigameFlow


class StockRound(Minigame):
    """Buy / Sell Public Companies, Private Companies"""

    def __init__(self) -> None:
        super().__init__()
        self.sell_private_company_auction = False   # Used to trigger a phase change.

    def _buyround(self, move: StockRoundMove, state: MutableGameState) -> None:
        if move.public_company_id == None:
            return

        purchase_amount = STOCK_CERTIFICATE

        if self.isFirstPurchase(move):
            purchase_amount = STOCK_PRESIDENT_CERTIFICATE
            move.public_company.setPresident(move.player)
            move.public_company.setInitialPrice(move.ipo_price)

        move.public_company.buy(move.player, move.source, purchase_amount)
        move.public_company.checkPresident()
        move.public_company.checkFloated()

        try:
            all_purchases = state.purchases[state.stock_round_count]
        except IndexError:
            state.purchases.append({})

        purchase_history = state.purchases[state.stock_round_count]
        try:
            purchase_history[move.player].append(move.public_company)
        except KeyError:
            purchase_history[move.player] = [move.public_company]

    def _sellround(self, move: StockRoundMove, kwargs: MutableGameState) -> None:
        sale_history = kwargs.sales[kwargs.stock_round_count]
        for company, amount in move.for_sale:
            company.sell(move.player, amount)
            company.priceDown(amount)
            company.checkPresident()

            try:
                sale_history[move.player].append(company)
            except KeyError:
                sale_history[move.player] = [company]

    def _buysell(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        if not self.validateBuy(move, kwargs) or not self.validateSales(move, kwargs):
            return False
        elif move.public_company_id != None and \
                self.isFirstPurchase(move) and \
                not self.validateFirstPurchase(move):
            return False
        self._buyround(move, kwargs)
        self._sellround(move, kwargs)
        kwargs.stock_round_play += 1
        return True

    def _buy(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        if not self.validateBuy(move, kwargs):
            return False
        elif self.isFirstPurchase(move) and not self.validateFirstPurchase(move):
            return False
        self._buyround(move, kwargs)
        kwargs.stock_round_play += 1
        return True

    def _sell(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        if not self.validateSales(move, kwargs):
            return False
        self._sellround(move, kwargs)
        kwargs.stock_round_play += 1
        return True

    def run(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        move.backfill(kwargs)

        if StockRoundType(move.move_type) == StockRoundType.BUYSELL:
            kwargs.stock_round_passed_in_a_row = 0
            kwargs.stock_round_last_buyer_seller_id = move.player_id
            return self._buysell(move, kwargs)

        elif StockRoundType(move.move_type) == StockRoundType.BUY:
            kwargs.stock_round_passed_in_a_row = 0
            return self._buy(move, kwargs)

        elif StockRoundType(move.move_type) == StockRoundType.SELL:
            kwargs.stock_round_passed_in_a_row = 0
            return self._sell(move, kwargs)

        if StockRoundType.PASS == StockRoundType(move.move_type):
            if self.validatePass(move, kwargs):
                kwargs.stock_round_play += 1
                kwargs.stock_round_passed_in_a_row += 1
                return True

        if StockRoundType.SELL_PRIVATE_COMPANY == StockRoundType(move.move_type):
            # TODO - may choose to move it to a different minigame, since it involves player interaction
            """
            User passes in information about the private company he wants to sell.

            We set a flag that is used to determine the next round?
            """
            if self.validateSellPrivateCompany(move, kwargs):
                self.sell_private_company_auction = True

            raise NotImplementedError

        return False

    def next(self, kwargs: MutableGameState) -> MinigameFlow:
        players: List[Player] = kwargs.players
        if self.sell_private_company_auction:
            kwargs.auction = []
            return MinigameFlow("Auction", False)
        if kwargs.stock_round_passed_in_a_row == len(players):
            # If there are any floated companies, we go into the Operating Round.
            # Otherwise, we start a new Stock Round.
            # Clear these values too btw.
            kwargs.stock_round_count += 1
            kwargs.stock_round_passed_in_a_row = kwargs.stock_round_play = 0

            for company in kwargs.public_companies:
                if company.isFloated():
                    return MinigameFlow("OperatingRound", False)

            logging.warning("No companies floated, so we are going into a new stock round.  "
                            "The player order needs to be reset")
            return MinigameFlow("StockRound", True)

        return MinigameFlow("StockRound", False)

    @staticmethod
    def onStart(kwargs: MutableGameState) -> None:
        super(StockRound, StockRound).onStart(kwargs)

    @staticmethod
    def onComplete(kwargs: MutableGameState) -> None:
        """Transitioning out of the stock round: increment stock values."""
        super(StockRound, StockRound).onComplete(kwargs)

        public_companies: List[PublicCompany] = kwargs.public_companies
        for pc in public_companies:
            pc.checkPriceIncrease()

    @staticmethod
    def onTurnComplete(kwargs: MutableGameState):
        """Transitioning out of the stock round: increment stock values."""
        super(StockRound, StockRound).onTurnComplete(kwargs)

    def validateBuy(self, move: StockRoundMove, state: MutableGameState) -> bool:
        if move.public_company_id == None:
            return True

        number_of_total_players = len(state.players)
        player_certificates = move.player.getCertificateCount()
        cost_of_stock = move.public_company.checkPrice(
            move.source,
            STOCK_CERTIFICATE,
            move.ipo_price)

        try:
            all_sales = state.sales[state.stock_round_count]
        except IndexError:
            state.sales.append({})

        my_sales = state.sales[state.stock_round_count].get(move.player, [])


        return self.validate([
            err(
                move.public_company not in my_sales,
                "You can't buy from a company you sold this round {} {}",
                move.public_company.id, move.public_company.name),
            err(
                player_certificates + 1 <= VALID_CERTIFICATE_COUNT[number_of_total_players],
                "You have too many certificates. There are {} players, and you are allowed a "
                "total of {} certificates.  You own {} certificates and would have too many if you bought more.",
                number_of_total_players,
                VALID_CERTIFICATE_COUNT[number_of_total_players],
                player_certificates),
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
                company.availableStock(StockPurchaseSource.BANK) + amount <= 60,
                "You can't sell that much ({}); the bank can only have 50 shares max.",
                amount
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
                "You can only sell after the first stock round.")
        ]

        return self.validate(validations)

    def validateSales(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        """Used in situations where there are multiple companies that are performing a sale."""

        data = [self._validateSale(move.player, company, amount, kwargs)
                for company, amount in move.for_sale]

        return reduce(
            lambda x, y: x and y,
            data,
            True # If there are no sales, the sale has been validated.
        )

    def validatePass(self, move: StockRoundMove, kwargs: MutableGameState):
        # As long as you are a player, you can pass
        return True

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
