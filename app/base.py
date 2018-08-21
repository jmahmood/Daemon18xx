import json
import uuid
from enum import Enum
from functools import reduce
from typing import NamedTuple, List, Set, Dict, Tuple

import logging

STOCK_PRESIDENT_CERTIFICATE = 20
STOCK_CERTIFICATE = 10


def err(validate: bool, error_msg: str, *format_error_msg_params):
    if not validate:
        return error_msg.format(*format_error_msg_params)


class MutableGameState:
    """This is state that needs to be accessed or modified by the minigames.
    We are initially putting all of that into this one object, but this will be refactored once the
    minigames are ready (and we can distinguish between mutable & non-mutable game state)"""
    def __init__(self):
        """
        players: All the players who are playing the game, from "right to left" (ie: in relative order for the stock round)
        """
        self.auction: List[Tuple[str, int]] = None # All bids on current auction; (player_id, amount)
        self.auctioned_private_company: PrivateCompany = None
        self.sales:List[Dict[Player, List[PublicCompany]]] = [] # Full list of things you sell in each stock round.
        self.purchases: List[Dict[Player, List[PublicCompany]]] = [] # Full list of things you buy in each stock round.
        self.public_companies: List["PublicCompany"] = None
        self.private_companies: List["PrivateCompany"] = None
        self.stock_round_passed_in_a_row: int = 0  # If every player passes during the stock round, the round is over.
        self.stock_round_play:int = 0
        self.stock_round_count: int = 0
        self.stock_round_last_buyer_seller_id: str = None
        self.players: List[Player] = None

    pass


class Color(Enum):
    GRAY = 1
    YELLOW = 2
    BROWN = 3
    RED = 4


class Train:
    pass


class Route(NamedTuple):
    pass


class Token(NamedTuple):
    pass


class Track(NamedTuple):
    id: str
    id_v2: str
    color: Color
    location: str
    rotation: int


class StockMarket:
    """This class holds information about different ordering on the stock market itself"""
    pass


class Player:
    """This is the individual player.
    Warning: There is no authorization at this level.  You do not check emails or passwords.  This is the character in the game."""

    def __hash__(self) -> int:
        return int("".join(str(ord(char)) for char in self.id))

    def __eq__(self, o: "Player") -> bool:
        return isinstance(o, Player) and self.id == o.id

    def __str__(self):
        return "{}:{}({})".format(self.id, self.name, self.cash)

    def __init__(self):
        self.id: str = "1"
        self.name: str = ""
        self.cash: int = 0
        self.order: int = 0
        self.portfolio: Set['PublicCompany'] = set()

    @staticmethod
    def create(name, cash, order) -> "Player":
        ret = Player()
        ret.id = str(uuid.uuid4())
        ret.name = name
        ret.cash = cash
        ret.order = order
        return ret

    def addToPortfolio(self, company: "PublicCompany", amount: int, price: int):
        """TODO: Is there a way to avoid cross-linking between Player and Public Company?
        Wouldn't that cause problems when trying to calculate a player's total wealth?"""
        self.portfolio.add(company)
        self.cash = self.cash - amount  / STOCK_CERTIFICATE * price

    def getCertificateCount(self):
        total_stock_certificates = 0

        for public_company in self.portfolio:
            total_stock_certificates += public_company.owners[self] / 10
            if public_company.president == self:  # President has a 20% stock certificate
                total_stock_certificates -= 1

        return total_stock_certificates

    def hasEnoughMoney(self, cost_of_stock: int):
        return self.cash >= cost_of_stock

    def hasStock(self, public_company: "PublicCompany"):
        return public_company.owners[self] if public_company in self.portfolio else 0


class PlayerBid(NamedTuple):
    player: Player
    bid_amount: int


class StockPurchaseSource(Enum):
    IPO = 1
    BANK = 2


class StockStatus(Enum):
    NORMAL = 1
    YELLOW = 2
    ORANGE = 3
    BROWN = 4


class GameBoard:
    def __init__(self):
        self.board = {}

    def setTrack(self, track: Track):
        self.board[track.location] = track
        pass

    def setToken(self, token: Token):
        # TODO
        pass

    def calculateRoute(self, route) -> int:
        pass


class PublicCompany:

    def __str__(self) -> str:
        return "{}: {} ({})".format(self.id, self.name, self.short_name)

    def __hash__(self) -> int:
        return int("".join(str(ord(char)) for char in self.id))

    def __eq__(self, o: "PublicCompany") -> bool:
        return isinstance(o, PublicCompany) and self.id == o.id

    def __init__(self):
        self.trains: List[Train] = None
        self._income: int = None
        # self._income: Used to store income until we determine whether or not it is given as dividends or retained.
        self.cash: int = None
        self._floated = None
        self.id: str = None
        self.name: str = None
        self.short_name: str = None
        self.president: Player = None
        self.stockPrice = {StockPurchaseSource.IPO: 0, StockPurchaseSource.BANK: 0}
        self.owners = {}
        self.stocks = {StockPurchaseSource.IPO: 100, StockPurchaseSource.BANK: 0}
        self.stock_status = StockStatus.NORMAL

    @staticmethod
    def initiate(**kwargs):
        x = PublicCompany()
        for k, v in kwargs.items():
            x.__dict__[k] = v
        if x.id == None:
            x.id = x.short_name
        return x

    def buy(self, player: Player, source: StockPurchaseSource, amount: int):
        price = self.stockPrice[source]
        if price <= 0:
            raise ValueError("Price of the stock has not yet been set")

        self.stocks[source] -= amount
        self.grantStock(player, amount)
        price = self.stockPrice[source]
        player.addToPortfolio(self, amount, price)

    def grantStock(self, player: Player, amount: int):
        self.owners[player] = self.owners.get(player, 0) + amount

    def sell(self, player: Player, amount: int):
        self.owners[player] = self.owners.get(player, 0) - amount

        # Player has to get paid for this, this is not handled by this class.
        self.stocks[StockPurchaseSource.BANK] += amount

    def checkPriceIncrease(self):
        if self.stocks[StockPurchaseSource.IPO] == 0 and self.stocks[StockPurchaseSource.BANK] == 0:
            self.priceUp(1)
        pass

    def priceUp(self, spaces):
        # TODO: Market goes up if there are no stocks left over..
        pass

    def priceDown(self, spaces):
        # TODO: Market price tanks on news.
        pass

    def checkPresident(self):
        """Goes through owners and determines who the president is.
        The minimum ownership (20%) is not enforced here."""
        # TODO: Should this go into the minigame instead since it affects state?
        # Or keep it here because this is repetitive logic?
        # Ownership can technically change in an operating round (Train rusting = no money = sell stock = less money)
        max_ownership = max(self.owners.values())
        top_owners = [k for k, v in self.owners.items() if v == max_ownership]
        if self.president is None or self.president not in top_owners:
            play_order = -1 if self.president is None else self.president.order

            """
            Go through each potential owner and calculate the distance from the previous president based on play order.
            if I am the old president, the person closest to me in turn order would be the next president.  We
            get this by subtracting the president's turn order from the potential president's order and finding
            the person with minimal distance.
           """
            ordered_list = [(owner, owner.order - play_order) for owner in top_owners]
            new_president = reduce(lambda x, y: x if x[1] < y[1] else y, ordered_list)
            self.president = new_president[0]

    def checkFloated(self):
        if not self._floated and self.stocks[StockPurchaseSource.IPO] < STOCK_CERTIFICATE * 5:
            self._floated = True
            self.cash = self.stockPrice[StockPurchaseSource.IPO] * 100 / STOCK_CERTIFICATE
            return True
        return False

    def availableStock(self, sps: StockPurchaseSource):
        return self.stocks[sps]

    def setPresident(self, player: Player):
        self.president = player

    def setInitialPrice(self, ipo_price: int):
        self.stockPrice[StockPurchaseSource.IPO] = self.stockPrice[StockPurchaseSource.BANK] = ipo_price

    def hasStock(self, sps: StockPurchaseSource, amount: int) -> bool:
        return self.stocks[sps] >= amount

    def checkPrice(self, source: StockPurchaseSource, amount: int, ipo_price: int):
        amount = amount / STOCK_CERTIFICATE
        if source == StockPurchaseSource.IPO and self.stockPrice[StockPurchaseSource.IPO] == 0:
            return amount * ipo_price

        return amount * self.stockPrice[source]

    def potentialPresidents(self) -> Set[Player]:
        """People with more than 20% stock are potential presidents"""
        return set([owner for owner, amount in self.owners.items() if amount >= 20])

    def payDividends(self):
        for owner in self.owners.keys():
            player: Player = owner
            player.cash += int(self._income * self.owners.get(player) / 100.0)

    def incomeToCash(self):
        self.cash += self._income

    def addIncome(self, amount: int) -> None:
        self._income += amount

    def removeRustedTrains(self, rusted_train_type: str):
        self.trains = [train for train in self.trains if train.type != rusted_train_type]

    def isFloated(self) -> bool:
        return self._floated

    def hasNoTrains(self) -> bool:
        return len(self.trains) > 0

    def hasValidRoute(self) -> bool:
        # TODO You need to have a train if you have a valid route
        raise NotImplementedError

    @staticmethod
    def allPublicCompanies() -> List["PublicCompany"]:
        content = []
        with open('/Users/jawaad/PycharmProjects/Daemon1830/app/data/public_companies') as f:
            content = json.load(f)
        return [PublicCompany.initiate(**private_company_dict) for private_company_dict in content]


class PrivateCompany:
    def __eq__(self, o: "PrivateCompany") -> bool:
        """Allows duck typed comparisons between objects"""
        return isinstance(o, PrivateCompany) and self.order == o.order

    def __init__(self):
        self.belongs_to_company: "PublicCompany" = None
        self.player_bids: List[PlayerBid] = None
        self.order: int = None
        self.name: str = None
        self.short_name: str = None
        self.cost: int = None
        self.actual_cost: int = None
        self.revenue: int = None
        self.belongs_to: Player = None
        self.player_bids: List[PlayerBid] = None
        self.passed_by: List[Player] = None
        # ^-- This is a list of people who have passed on a private company in a bidding round.
        self.pass_count = None

    @staticmethod
    def allPrivateCompanies() -> List["PrivateCompany"]:
        with open('/Users/jawaad/PycharmProjects/Daemon1830/app/data/private_companies') as f:
            content = f.readlines()
        return [PrivateCompany.initiate(*c.strip().split("|")) for c in content]

    @staticmethod
    def initiate(order: int,
                 name: str,
                 short_name: str,
                 cost: int,
                 revenue: int,
                 base: str,
                 belongs_to: "Player" = None,
                 actual_cost: int = None,
                 player_bids: List[PlayerBid] = None,
                 passed_by: List[Player] = None,
                 pass_count: int = 0) -> "PrivateCompany":
        pc = PrivateCompany()
        pc.order = order
        pc.name = name
        pc.short_name = short_name
        pc.cost = int(cost)
        pc.actual_cost = int(actual_cost) if actual_cost is not None else int(cost)
        pc.revenue = revenue
        pc.base = base
        pc.belongs_to = belongs_to
        pc.player_bids = [] if player_bids is None else player_bids
        pc.passed_by = [] if passed_by is None else passed_by
        pc.pass_count = pass_count

        return pc

    def hasOwner(self) -> bool:
        return self.belongs_to is not None

    def hasNoOwner(self) -> bool:
        return self.belongs_to is None

    def hasBids(self) -> bool:
        return len(self.player_bids) > 0

    def passed(self, player: Player):
        self.pass_count += 1

    def reduce_price(self, players: List[Player]):
        if self.pass_count % len(players) == 0 and self.pass_count > 0:
            self.actual_cost -= 5

    def bid(self, player: Player, amount: int):
        """No security at this level.  If you run this, any bid will be accepted."""
        self.player_bids.append(PlayerBid(player, amount))
        player.cash -= amount  # Cash will be returned if they lose the auction.

    def acceptHighestBid(self):
        selected_bid: PlayerBid = reduce(
            lambda x, y: x if x.bid_amount > y.bid_amount else y,
            self.player_bids
        )

        for bid in self.player_bids:
            bid.player.cash += bid.bid_amount  # Return cash before taking the top bid.

        self.setActualCost(selected_bid.bid_amount)
        self.setBelongs(selected_bid.player)
        return True


    def setBelongs(self, player: Player):
        """No security at this level.  If you run this, any bid will be accepted."""
        self.belongs_to = player
        self.belongs_to.cash -= self.actual_cost

    def setActualCost(self, actual_cost):
        self.actual_cost = actual_cost

    def distributeRevenue(self):
        if self.belongs_to:
            self.belongs_to.cash += self.revenue
        if self.belongs_to_company:
            self.belongs_to_company.addIncome(self.revenue)


class Move:
    """
    Contains all details of a move that is made, who made that move, and the data that they convey to represent the move.
    """

    def __init__(self) -> None:
        super().__init__()
        self.player_id: str = None
        self.player: Player = None
        self.msg = None

    def backfill(self, kwargs: MutableGameState) -> None:
        """We do not have all the context when we receive a move; we are only passed a JSON text file, not the
        objects themselves.  We receive the objects from the game object when executing the Minigame.
        We bind those objects when the minigame is run, keeping ID values to allow us to match them up to the object itself"""

        for player in kwargs.players:
            if player.id == self.player_id:
                self.player = player
                return

        raise ValueError("Player not found when instantiating move")

    @staticmethod
    def fromMove(move: "Move") -> "Move":
        raise NotImplementedError

    @staticmethod
    def fromMessage(msg) -> "Move":
        """
        Required fields:
            Player
        :param msg:
        :return:
        """
        ret = Move()
        ret.msg = msg
        return ret
