from enum import Enum
from typing import NamedTuple, List

class StockMarket:
    """This class holds information about different ordering on the stock market itself"""
    pass

class Player:
    def __init__(self):
        self.cash: int = 0
        self.order: int = 0
        self.portfolio = set()

    def addToPortfolio(self, company: "PublicCompany", amount: int, price: int):
        """TODO: Is there a way to avoid cross-linking between Player and Public Company?
        Wouldn't that cause problems when trying to calculate a player's total wealth?"""
        self.portfolio.add(company)
        self.cash = self.cash - amount * price


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


class PublicCompany:
    def __init__(self):
        self._floated = None
        self.president: Player = None
        self.stockPrice = {StockPurchaseSource.IPO: 0, StockPurchaseSource.BANK: 0}
        self.owners = {}
        self.stocks = {StockPurchaseSource.IPO: 10, StockPurchaseSource.BANK: 0}
        self.stock_status = StockStatus.NORMAL

    def buy(self, player: Player, source: StockPurchaseSource, amount: int):
        # TODO: Check if this is the first sale.
        self.stocks[source] -= amount
        self.grantStock(player, amount)
        price = self.stockPrice[source]
        player.addToPortfolio(self, amount, price)

    def grantStock(self, player: Player, amount: int):
        self.owners[player] = self.owners.get(player, 0) + amount

    def sell(self, player: Player, amount: int):
        self.owners[player] = self.owners.get(player, 0) - amount
        self.stocks[StockPurchaseSource.BANK] += amount
        # TODO: Player has to get paid for this.
        self.priceDown(amount)

        pass

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
        """Goes through owners and determines who the president is."""
        # TODO: Should this go into the minigame instead since it affects state?
        # Or keep it here because this is repetitive logic?
        # Ownership can technically change in an operating round (Train rusting = no money = sell stock = less money)
        max_ownership = max(self.owners.values())
        top_owners = [k for k,v in self.owners.items() if v == max_ownership]
        if self.president not in top_owners:
            play_order = self.president.order

            """
            Go through each potential owner and calculate the distance from the previous president based on play order.
            if I am the old president, the person closest to me in turn order would be the next president.  We
            get this by subtracting the president's turn order from the potential president's order and finding
            the person with minimal distance.
           """
            new_president = min([(owner, owner.order - play_order) for owner in top_owners], lambda v: v[1])[0]
            self.president = new_president

    def checkFloated(self):
        if not self._floated and self.stocks[StockPurchaseSource.IPO] < 5:
            self._floated = True
            return True
        return False


class PrivateCompany:
    def __init__(self):
        self.player_bids = None
        self.order = None
        self.name = None
        self.short_name = None
        self.cost = None
        self.actual_cost = None
        self.revenue = None
        self.belongs_to = None
        self.player_bids: List[PlayerBid] = None
        self.passed_by: List[Player] = None
        self.pass_count = None

    @staticmethod
    def allPrivateCompanies() -> List["PrivateCompany"]:
        with open('app/data/private_companies') as f:
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
        pc.cost = cost
        pc.actual_cost = actual_cost if actual_cost is not None else cost
        pc.revenue = revenue
        pc.base = base
        pc.belongs_to = belongs_to
        pc.player_bids = [] if player_bids is None else player_bids
        pc.passed_by = [] if passed_by is None else passed_by
        pc.pass_count = pass_count

        return pc

    def hasOwner(self) -> bool:
        return self.belongs_to is not None

    def hasBids(self) -> bool:
        return len(self.player_bids) > 0

    def passed(self, player: Player):
        self.pass_count += 1

    def reduce_price(self, player_count):
        if self.pass_count % player_count == 0 and self.pass_count > 0:
            self.actual_cost -= 5

    def bid(self, player: Player, amount: int):
        """No security at this level.  If you run this, any bid will be accepted."""
        self.player_bids.append(PlayerBid(player, amount))

    def belongs(self, player: Player):
        """No security at this level.  If you run this, any bid will be accepted."""
        self.belongs_to(player)

    def set_actual_cost(self, actual_cost):
        self.actual_cost = actual_cost


class Move:
    """
    Contains all details of a move that is made, who made that move, and the data that they convey to represent the move.
    """

    def __init__(self) -> None:
        super().__init__()
        self.msg = None

    def backfill(self, **kwargs) -> None:
        """Used to add additional contextual fields (Player instead of Player ID)"""
        raise NotImplementedError

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
