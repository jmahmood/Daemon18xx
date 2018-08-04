from enum import Enum
from typing import List

from functools import reduce

from app.base import Move, PublicCompany, StockPurchaseSource, Player
from app.minigames.base import Minigame

ALL_AVAILABLE_STOCK = 100
STOCK_PRESIDENT_CERTIFICATE = 20
STOCK_CERTIFICATE = 10

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
    SELL_PRIVATE_COMPANY = 4  # TODO - may choose to move it to a different minigame, since it involves player interaction


class StockRoundMove(Move):
    def __init__(self):
        super().__init__()
        self.ipo_price: int = 0
        self.player: Player = None
        self.source: StockPurchaseSource = None
        self.public_company: PublicCompany = None
        self.amount: int = None  # Only used for sale.
        self.move_type: StockRoundType = None

    def backfill(self, **kwargs) -> None:
        # TODO
        pass

    @staticmethod
    def fromMove(move: "Move") -> "Move":
        ret = StockRoundMove()
        return ret


class StockRound(Minigame):
    """Buy / Sell Public Companies, Private Companies"""

    def run(self, move: StockRoundMove, **kwargs) -> bool:
        move.backfill(**kwargs)

        if StockRoundType.BUY == StockRoundType(move.move_type):
            if self.validateBuy(move, **kwargs):
                purchase_amount = STOCK_CERTIFICATE

                if self.isFirstPurchase(move):
                    if not self.validateFirstPurchase(move):
                        return False

                    purchase_amount = STOCK_PRESIDENT_CERTIFICATE
                    move.public_company.setPresident(move.player)
                    move.public_company.setInitialPrice(move.ipo_price)

                kwargs['stock_round_play'] = kwargs['stock_round_play'] + 1

                move.public_company.buy(move.player, move.source, purchase_amount)
                move.public_company.checkPresident()
                move.public_company.checkFloated()
                return True

        if StockRoundType.SELL == StockRoundType(move.move_type):
            if self.validateSell(move):
                kwargs['stock_round_play'] = kwargs['stock_round_play'] + 1
                move.public_company.sell(move.player, move.amount)
                move.public_company.priceDown(move.amount)
                move.public_company.checkPresident()
                return True

        if StockRoundType.PASS == StockRoundType(move.move_type):
            if self.validatePass(move):
                kwargs['stock_round_play'] = kwargs['stock_round_play'] + 1
                kwargs['stock_round_passed'] = kwargs['stock_round_passed'] + 1
                # If every player passes during the stock round, the round is over.
                return True

    def next(self, **kwargs) -> str:
        players: List[Player] = kwargs.get('players')
        if kwargs['stock_round_play'] % len(players) == 0 \
                and kwargs['stock_round_play'] > 0 \
                and kwargs['stock_round_passed'] == len(players):
            public_companies: List[PublicCompany] = kwargs.get('public_companies')
            for public_company in public_companies:
                public_company.checkPriceIncrease()
                return "OperatingRound"
        return "StockRound"

    def validateBuy(self, move: StockRoundMove, **kwargs) -> bool:
        number_of_total_players = len(kwargs.get('players'))
        player_certificates = move.player.getCertificateCount()
        cost_of_stock = move.public_company.checkPrice(move.source, STOCK_CERTIFICATE, move.ipo_price)

        return self.validate(
            [("You have too many certificates. There are {} players, and you are allowed a total of {} certificates."
             "You own {} certificates and would have one more if you bought."
                .format(number_of_total_players,
                        VALID_CERTIFICATE_COUNT[number_of_total_players],
                        player_certificates),
                 player_certificates + 1 <= VALID_CERTIFICATE_COUNT[number_of_total_players]),

             ("The company does not have enough stock in category {}".format(move.source),
                 move.public_company.hasStock(move.source, 10)),

             ("You cannot afford poorboi. {} (You have: {})".format(cost_of_stock, move.player.cash),
                 move.player.hasEnoughMoney(cost_of_stock))
             ]
        )

    def validateSell(self, move: StockRoundMove, **kwargs) -> bool:
        return self.validate([
            ("You must have more stock than you are trying to sell {}".format(move.amount),
                 move.player.hasStock(move.public_company) > move.amount),
            ("You can't sell that much ({}); the bank can only have 50 shares max.".format(move.amount),
                 move.public_company.availableStock(StockPurchaseSource.BANK) + move.amount <= 60),
            ("There are no other potential presidents, so you can't sell your shares.",
                 len(move.public_company.potentialPresidents() - {move.player}) > 0),
            ("You can only sell in units of 10 stocks ({})".format(move.amount),
                 move.amount % STOCK_CERTIFICATE == 0),
            ("You can only sell after the first stock round.",
                 kwargs.get('stock_round_count') > 1)
             ]
        )

    def validatePass(self, move: StockRoundMove):
        # As long as you are a player, you can pass
        return True

    def validateFirstPurchase(self, move: StockRoundMove) -> bool:
        cost_of_stock = move.public_company.checkPrice(move.source, STOCK_PRESIDENT_CERTIFICATE, move.ipo_price)
        valid_ipo_prices = ",".join([str(p) for p in VALID_IPO_PRICES])

        return self.validate([
            ("Invalid IPO Price ({}).  Valid prices are {}.".format(move.ipo_price, valid_ipo_prices),
                 move.ipo_price in VALID_IPO_PRICES),
             ("You need to purchase stock from the IPO as this is an initial purchase",
                 move.source == StockPurchaseSource.IPO),
             ("You cannot afford to be president poorboi. {} (You have: {})".format(cost_of_stock, move.player.cash),
                 move.player.hasEnoughMoney(cost_of_stock))]
        )

    def isFirstPurchase(self, move: StockRoundMove) -> bool:
        # When a company is first purchased, all 100% of the stock is owned by the IPO pile.
        return move.public_company.availableStock(StockPurchaseSource.IPO) == ALL_AVAILABLE_STOCK
