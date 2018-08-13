import json
from enum import Enum
from functools import reduce
from typing import List, Tuple

import logging

from app.base import Move, PublicCompany, StockPurchaseSource, Player, err, MutableGameState, STOCK_CERTIFICATE, \
    STOCK_PRESIDENT_CERTIFICATE
from app.minigames.base import Minigame

ALL_AVAILABLE_STOCK = 100

VALID_IPO_PRICES = [
    100,
    90,
    82,
    76,
    71,
    67
]

# player: # of certs they can hold.
VALID_CERTIFICATE_COUNT = {
    2: 28,
    3: 20,
    4: 16,
    5: 13,
    6: 11
}


class StockRoundType(Enum):
    BUY = 1
    SELL = 2
    PASS = 3
    SELL_PRIVATE_COMPANY = 4
    BUYSELL = 5

class StockRoundMove(Move):
    def __init__(self) -> None:
        super().__init__()

        # Sale  Fields
        self.for_sale_raw: List[List] = None
        self.for_sale: List[Tuple[PublicCompany, int]] = None  # A list of stocks you are selling this round.

        # Purchase fields
        self.public_company_id: str = None  # Used for purchase action only.
        self.public_company: PublicCompany = None  # Used for purchase actions only.
        self.source: StockPurchaseSource = None  # Used for purchase actions only
        self.ipo_price: int = None  # Used to set initial price for a stock. (First purchase only)
        self.move_type: StockRoundType = None

    def find_public_company(self, public_company_id: str,  kwargs: MutableGameState):
        return next(pc for pc in kwargs.public_companies if pc.id == public_company_id)

    def backfill(self, kwargs: MutableGameState) -> None:
        super().backfill(kwargs)
        self.public_company = self.find_public_company(self.public_company_id, kwargs)

        self.for_sale = []
        if self.for_sale_raw is not None:
            for company_id, amount in self.for_sale_raw:
                self.for_sale.append((self.find_public_company(company_id, kwargs), amount))


    @staticmethod
    def fromMove(move: "Move") -> "StockRoundMove":
        ret = StockRoundMove()

        msg: dict = json.loads(move.msg)
        ret.public_company_id = msg.get('public_company_id')
        ret.player_id = msg.get("player_id")

        ret.move_type = StockRoundType[msg.get('move_type')]
        ret.ipo_price = int(msg.get("ipo_price", 0))
        ret.source = StockPurchaseSource[msg.get("source")]
        ret.for_sale_raw = msg.get("for_sale_raw")


        return ret


class StockRound(Minigame):
    """Buy / Sell Public Companies, Private Companies"""

    def run(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        move.backfill(kwargs)
        buy_sell_validation = True

        if StockRoundType(move.move_type) in (StockRoundType.BUY, StockRoundType.BUYSELL):
            if self.validateBuy(move, kwargs):
                purchase_amount = STOCK_CERTIFICATE

                if self.isFirstPurchase(move):
                    if not self.validateFirstPurchase(move):
                        buy_sell_validation = False
                        logging.warning("Fail first purchase attempt")
                        if StockRoundType(move.move_type) == StockRoundType.BUY:
                            return False

                    purchase_amount = STOCK_PRESIDENT_CERTIFICATE
                    move.public_company.setPresident(move.player)
                    move.public_company.setInitialPrice(move.ipo_price)

                kwargs.stock_round_play += 1

                move.public_company.buy(move.player, move.source, purchase_amount)
                move.public_company.checkPresident()
                move.public_company.checkFloated()

                if StockRoundType(move.move_type) == StockRoundType.BUY:
                    return True

        if StockRoundType(move.move_type) in (StockRoundType.SELL, StockRoundType.BUYSELL):
            if self.validateSales(move, kwargs) and self.validateBuy(move, kwargs):
                kwargs.stock_round_play += 1
                for company, amount in move.for_sale:
                    company.sell(move.player, amount)
                    company.priceDown(amount)
                    company.checkPresident()

                if StockRoundType(move.move_type) == StockRoundType.SELL:
                    return True
            else:
                buy_sell_validation = False

        if StockRoundType(move.move_type) == StockRoundType.BUYSELL:
            return buy_sell_validation

        if StockRoundType.PASS == StockRoundType(move.move_type):
            if self.validatePass(move, kwargs):
                kwargs.stock_round_play += 1
                kwargs.stock_round_passed += 1
                return True

        if StockRoundType.SELL_PRIVATE_COMPANY == StockRoundType(move.move_type):
            # TODO - may choose to move it to a different minigame, since it involves player interaction
            # Two implementation possibilities
            # Interrupt the current player order, ask all players to submit a price they are willing to pay,
            # Player can then select from between them.  He does not have to select the highest price.
            # This kind of bidding dynamic would be cool if it was not turn-based but could happen in real time,
            # like it would happen in the game itself..

            # Alternative easy and non-entertaining method would be to allow the player to submit the other player id
            # and the amount they have agreed on selling for.  There would be no validation involved, and it would
            # be an obvious cheating vector.
            raise NotImplementedError

        return False

    def next(self, kwargs: MutableGameState) -> str:
        players: List[Player] = kwargs.players
        if kwargs.stock_round_play % len(players) == 0 \
                and kwargs.stock_round_play > 0 \
                and kwargs.stock_round_passed == len(players):
            return "OperatingRound1"
        return "StockRound"

    @staticmethod
    def onStart(kwargs: MutableGameState) -> None:
        pass

    @staticmethod
    def onComplete(kwargs: MutableGameState) -> None:
        """Transitioning out of the stock round: increment stock values."""
        super().onComplete(kwargs)

        public_companies: List[PublicCompany] = kwargs.public_companies
        for pc in public_companies:
            pc.checkPriceIncrease()

    @staticmethod
    def onTurnComplete(kwargs: MutableGameState):
        """Transitioning out of the stock round: increment stock values."""
        super().onTurnComplete(kwargs)

    def validateBuy(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        number_of_total_players = len(kwargs.players)
        player_certificates = move.player.getCertificateCount()
        cost_of_stock = move.public_company.checkPrice(move.source, STOCK_CERTIFICATE, move.ipo_price)

        my_sales = kwargs.sales[kwargs.stock_round_count].get(move.player, [])

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

            err(kwargs.stock_round_count > 1,
                "You can only sell after the first stock round.")
        ]

        return self.validate(validations)

    def validateSales(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        """Used in situations where there are multiple companies that are performing a sale."""

        everything = [self._validateSale(move.player, company, amount, kwargs)
             for company, amount in move.for_sale]

        return reduce(
            lambda x, y: x and y,
            [self._validateSale(move.player, company, amount, kwargs)
             for company, amount in move.for_sale]
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
