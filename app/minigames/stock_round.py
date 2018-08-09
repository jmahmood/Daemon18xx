import json
from enum import Enum
from typing import List

from app.base import Move, PublicCompany, StockPurchaseSource, Player, err, MutableGameState
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
    SELL_PRIVATE_COMPANY = 4


class StockRoundMove(Move):
    def __init__(self) -> None:
        super().__init__()
        self.public_company_id: str = None
        self.public_company: PublicCompany = None
        self.ipo_price: int = None
        self.source: StockPurchaseSource = None
        self.private_company_order: int = None
        self.amount: int = None  # Only used for sale.
        self.move_type: StockRoundType = None

    def backfill(self, kwargs: MutableGameState) -> None:
        super().backfill(kwargs)
        self.public_company = next(pc for pc in kwargs.public_companies if pc.id == self.public_company_id)

    @staticmethod
    def fromMove(move: "Move") -> "Move":
        ret = StockRoundMove()

        msg: dict = json.loads(move.msg)
        ret.private_company_order = msg.get('private_company')
        ret.player_id = msg.get("player_id")

        ret.move_type = StockRoundType(msg.get('move_type'))
        ret.ipo_price = int(msg.get("ipo_price", 0))
        ret.source = StockPurchaseSource(msg.get("stock_source"))
        ret.amount = int(msg.get("amount", 0))

        return ret


class StockRound(Minigame):
    """Buy / Sell Public Companies, Private Companies"""

    def run(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        move.backfill(kwargs)

        if StockRoundType.BUY == StockRoundType(move.move_type):
            if self.validateBuy(move, kwargs):
                purchase_amount = STOCK_CERTIFICATE

                if self.isFirstPurchase(move):
                    if not self.validateFirstPurchase(move):
                        return False

                    purchase_amount = STOCK_PRESIDENT_CERTIFICATE
                    move.public_company.setPresident(move.player)
                    move.public_company.setInitialPrice(move.ipo_price)

                kwargs.stock_round_play += 1

                move.public_company.buy(move.player, move.source, purchase_amount)
                move.public_company.checkPresident()
                move.public_company.checkFloated()
                return True

        if StockRoundType.SELL == StockRoundType(move.move_type):
            if self.validateSell(move, kwargs):
                kwargs.stock_round_play += 1
                move.public_company.sell(move.player, move.amount)
                move.public_company.priceDown(move.amount)
                move.public_company.checkPresident()
                return True

        if StockRoundType.PASS == StockRoundType(move.move_type):
            if self.validatePass(move):
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

        return self.validate([
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
                cost_of_stock, move.player.cash
            ),
        ]
        )

    def validateSell(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
        return self.validate([
            err(
                move.player.hasStock(move.public_company) > move.amount,
                "You must have more stock than you are trying to sell {}",
                move.amount
            ),
            err(
                move.public_company.availableStock(StockPurchaseSource.BANK) + move.amount <= 60,
                "You can't sell that much ({}); the bank can only have 50 shares max.",
                move.amount
            ),
            err(
                len(move.public_company.potentialPresidents() - {move.player}) > 0,
                "There are no other potential presidents, so you can't sell your shares.",
            ),
            err(move.amount % STOCK_CERTIFICATE == 0,
                "You can only sell in units of 10 stocks ({})".format(move.amount),
                ),
            err(kwargs.stock_round_count > 1,
                "You can only sell after the first stock round.")
        ])

    def validatePass(self, move: StockRoundMove):
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
                "You need to purchase stock from the IPO as this is an initial purchase",),
            err(move.player.hasEnoughMoney(cost_of_stock),
                "You cannot afford to be president poorboi. {} (You have: {})",
                cost_of_stock, move.player.cash,)]
        )

    def isFirstPurchase(self, move: StockRoundMove) -> bool:
        # When a company is first purchased, all 100% of the stock is owned by the IPO pile.
        return move.public_company.availableStock(StockPurchaseSource.IPO) == ALL_AVAILABLE_STOCK
