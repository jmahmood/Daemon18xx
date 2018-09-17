from functools import reduce
from typing import List

import logging

from app.base import PublicCompany, StockPurchaseSource, Player, err, STOCK_CERTIFICATE, STOCK_PRESIDENT_CERTIFICATE
from app.minigames.StockRound.const import VALID_CERTIFICATE_COUNT, VALID_IPO_PRICES, ALL_AVAILABLE_STOCK
from app.minigames.StockRound.enums import StockRoundType
from app.minigames.StockRound.move import StockRoundMove
from app.minigames.base import Minigame, MinigameFlow
from app.state import MutableGameState


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

    def _sellround(self, move: StockRoundMove, state: MutableGameState) -> None:
        sale_history = state.sales[state.stock_round_count]
        for company, amount in move.for_sale:
            if amount > 0:
                company.sell(move.player, amount)
                company.priceDown(amount / STOCK_CERTIFICATE)
                company.checkPresident()

                try:
                    sale_history[move.player].append(company)
                except KeyError:
                    sale_history[move.player] = [company]

    def _buysell(self, move: StockRoundMove, state: MutableGameState) -> bool:
        if not self.validateBuy(move, state) or not self.validateSales(move, state):
            return False
        elif move.public_company_id != None and \
                self.isFirstPurchase(move) and \
                not self.validateFirstPurchase(move):
            return False
        self._buyround(move, state)
        self._sellround(move, state)
        state.stock_round_play += 1
        return True

    def _buy(self, move: StockRoundMove, state: MutableGameState) -> bool:
        if not self.validateBuy(move, state):
            return False
        elif self.isFirstPurchase(move) and not self.validateFirstPurchase(move):
            return False
        self._buyround(move, state)
        state.stock_round_play += 1
        return True

    def _sell(self, move: StockRoundMove, state: MutableGameState) -> bool:
        if not self.validateSales(move, state):
            return False
        self._sellround(move, state)
        state.stock_round_play += 1
        return True

    def run(self, move: StockRoundMove, state: MutableGameState) -> bool:
        move.backfill(state)

        if StockRoundType(move.move_type) == StockRoundType.BUYSELL:
            state.stock_round_passed_in_a_row = 0
            state.stock_round_last_buyer_seller_id = move.player_id
            return self._buysell(move, state)

        elif StockRoundType(move.move_type) == StockRoundType.BUY:
            state.stock_round_passed_in_a_row = 0
            return self._buy(move, state)

        elif StockRoundType(move.move_type) == StockRoundType.SELL:
            state.stock_round_passed_in_a_row = 0
            return self._sell(move, state)

        if StockRoundType.PASS == StockRoundType(move.move_type):
            if self.validatePass(move, state):
                state.stock_round_play += 1
                state.stock_round_passed_in_a_row += 1
                return True

        if StockRoundType.SELL_PRIVATE_COMPANY == StockRoundType(move.move_type):
            """
            User passes in information about the private company he wants to sell.

            We set a flag that is used to determine a shift to "Auction" mode.
            """
            if self.validateSellPrivateCompany(move, state):
                self.sell_private_company_auction = True
                state.auction = []
                state.auctioned_private_company = move.private_company
            return True

        return False

    def next(self, state: MutableGameState) -> MinigameFlow:
        players: List[Player] = state.players
        if self.sell_private_company_auction:
            return MinigameFlow("StockRoundSellPrivateCompany", False)
        if state.stock_round_passed_in_a_row == len(players):
            # If there are any floated companies, we go into the Operating Round.
            # Otherwise, we start a new Stock Round.
            # Clear these values too btw.
            state.stock_round_count += 1
            state.stock_round_passed_in_a_row = state.stock_round_play = 0

            for company in state.public_companies:
                if company.isFloated():
                    return MinigameFlow("OperatingRound", False)

            logging.warning("No companies floated, so we are going into a new stock round.  "
                            "The player order needs to be reset")
            # We need to pay off the income from the private companies.

            for pc in state.private_companies:
                pc.distributeRevenue()

            return MinigameFlow("StockRound", True)

        return MinigameFlow("StockRound", False)

    @staticmethod
    def onStart(state: MutableGameState) -> None:
        super(StockRound, StockRound).onStart(state)

    @staticmethod
    def onComplete(state: MutableGameState) -> None:
        """Transitioning out of the stock round: increment stock values."""
        super(StockRound, StockRound).onComplete(state)

        public_companies: List[PublicCompany] = state.public_companies
        for pc in public_companies:
            pc.checkPriceIncrease()

    @staticmethod
    def onTurnComplete(state: MutableGameState):
        """Transitioning out of the stock round: increment stock values."""
        super(StockRound, StockRound).onTurnComplete(state)

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
                move.source.name),
            err(
                move.player.hasEnoughMoney(cost_of_stock),
                "You cannot afford poorboi. {} (You have: {})",
                cost_of_stock, move.player.cash),
        ])

    def _validateSale(self, player: Player, company: PublicCompany, amount: int, state: MutableGameState):
        """You can't sell stocks you bought in previous rounds."""
        my_purchases = state.purchases[state.stock_round_count].get(player, [])

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

            err(state.stock_round_count >= 1,
                "You can only sell after the first stock round.")
        ]

        return self.validate(validations)

    def validateSales(self, move: StockRoundMove, state: MutableGameState) -> bool:
        """Used in situations where there are multiple companies that are performing a sale."""

        data = [self._validateSale(move.player, company, amount, state)
                for company, amount in move.for_sale]

        return reduce(
            lambda x, y: x and y,
            data,
            True # If there are no sales, the sale has been validated.
        )

    def validatePass(self, move: StockRoundMove, state: MutableGameState):
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

    def validateSellPrivateCompany(self, move, state):
        return True
