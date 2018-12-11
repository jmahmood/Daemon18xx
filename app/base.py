import json
import logging
import os.path
import uuid
from enum import IntEnum
from functools import reduce
from typing import NamedTuple, List, Set, Dict, Tuple, Union

from app.minigames.StockRound.const import STOCK_MARKET

BASE_DIR = "/home/jawaad/Daemon18xx/"

DATA_DIR = os.path.join(BASE_DIR, "app/data")

# type_id: [type_id....]
UPGRADE: Dict[str, List[str]] = {}
STOCK_PRESIDENT_CERTIFICATE = 20
STOCK_CERTIFICATE = 10


def err(validate: bool, error_msg: str, *format_error_msg_params):
    if not validate:
        return error_msg.format(*format_error_msg_params)


class Color(IntEnum):
    GREY = 1
    YELLOW = 2
    BROWN = 3
    RED = 4


class City:
    """Loads cities and the value they provide when a train passes through them.  Used in setup phase."""
    FILES = ["cities", "double_city"]

    def __str__(self) -> str:
        return "{}: {} ({})".format(self.name, self.value, self.special)

    def __hash__(self) -> int:
        return int("".join(str(ord(char)) for char in self.name))

    def __eq__(self, o: "City") -> bool:
        return isinstance(o, City) and self.name == o.name

    def __init__(self, hex_name, name, value=0, tokens=0, special=None, company=None, private_company=None, **kwargs):
        self.map_hex_name: str = hex_name
        self.name: str = name
        self.value: int = value
        self.special: str = special
        self.company_hq: str = company
        self.private_company_hq: str = private_company
        self.tokens: int = tokens  # TODO: p1: remove The number of stations that can be setup by public companies.
        logging.info("Unused Kwargs: {}".format(
            ",".join(kwargs.keys())
        ))

    def __str__(self) -> str:
        return "{} - {}".format(self.name, self.map_hex_name)

    @classmethod
    def load(cls):
        ret = []
        for f in cls.FILES:
            with open(os.path.join(DATA_DIR, f)) as json_file:
                data = json.load(json_file)
                for d in data:
                    ret.append(cls(**d))
        return ret


class Town(City):
    FILES = ["town", "double_town"]


class Train:
    pass


class Route(NamedTuple):
    # TODO: P1: Is the route passed directly or do we init it with the info passed in the JSON?
    # TODO: P1: This should be something other than a tuple, as we may want to have convenience methods added to it
    # Need to make sure the full city / town info is filled in by the game when the initial info is passed

    start: Union[City, Town]
    end: Union[City, Town]
    full_route: Set[str]


class Token(NamedTuple):
    city: City
    public_company: "PublicCompany"
    location: str


class Position(IntEnum):
    LEFT = 1
    TOP_LEFT = 2
    TOP_RIGHT = 3
    RIGHT = 4
    BOTTOM_RIGHT = 5
    BOTTOM_LEFT = 6
    CITY_1 = 40
    CITY_2 = 50

    def rotate(self, amount) -> "Position":
        if self.value < Position.CITY_1:
            return Position((self.value + amount - 1) % 6 + 1)
        return Position(self.value)

    def edge_name(self, map_hex_name: str) -> str:
        """
        :param map_hex_name: Like "A1" or "B2" or whatever.
        :return:
        """
        return "{}-{}".format(
            map_hex_name, self.value
        )


class TrackType(object):
    DATA_FILE = os.path.join(DATA_DIR, "tracks")

    def __init__(self,
                 type_id: str,
                 connections: List[
                     List[Tuple[Position, Position]]
                 ],
                 copies: int,
                 color: Color = Color.YELLOW,
                 cities: int = 0,
                 towns: int = 0,
                 upgrades: List["TrackType"] = None,
                 city_1_stations: int = 0,
                 city_2_stations: int = 0,
                 **kwargs
                 ) -> None:
        super().__init__()
        self.type_id = type_id
        self.connections: List[List[Tuple[Position, Position]]] = connections
        self.copies = copies
        self.color = color
        self.cities = cities
        self.towns = towns
        self.upgrades = upgrades
        self.city_1_stations = city_1_stations
        self.city_2_stations = city_2_stations
        self.value = int(kwargs.get("value", 0))  # Value for a train to pass through
        self.default_location = kwargs.get("default_location")

        logging.info("Unused Kwargs: {}".format(
            ",".join(kwargs.keys())
        ))

    def __str__(self) -> str:
        return "{} - {}".format(self.type_id, self.color)

    def can_upgrade_to(self, track_type: "TrackType") -> bool:
        return track_type.type_id in UPGRADE.get(self.type_id)

    @classmethod
    def load(cls):
        #TODO: P1: Clarify how we deal with different paths

        with open(cls.DATA_FILE) as f:
            data = json.load(f)
        ret = [cls(**d) for d in data]
        for r in ret:
            # Convert the JSON connections to the correct object type.

              # Some tile types let you have multiple paths, with you only being able to use one of them.
            all_possible_connections = []

            for possible_pairs in r.connections:
                connections =  []



                for pairs in possible_pairs:
                    connections.append((Position(pairs[0]), Position(pairs[1])))
                all_possible_connections.append(connections)
            r.connections = all_possible_connections

        return ret


class Track(NamedTuple):
    id: str  # Unique identifier
    type: TrackType  # type of track identifier(s)
    rotation: int  # A number from 0-5 which is added to all of the connections to rotate the tile.

    def __str__(self) -> str:
        return "{}: {}".format(self.id, self.type.type_id)

    def __hash__(self) -> int:
        return int("".join(str(ord(char)) for char in self.id))

    def __eq__(self, o: "Track") -> bool:
        return isinstance(o, Track) and self.id == o.id

    def connections(self) -> List[List[Tuple[Position, Position]]]:
        connections = []
        for possibilities in self.type.connections:
            rotated_possibilities = []
            for position_1, position_2 in possibilities:
                if not isinstance(position_1, Position):
                    position_1 = Position(position_1)
                if not isinstance(position_2, Position):
                    position_2 = Position(position_2)

                try:
                    rotated_possibilities.append(
                        (position_1.rotate(self.rotation), position_2.rotate(self.rotation))
                    )
                except AttributeError:
                    pass
            connections.append(rotated_possibilities)
        return connections

    def rotate(self, rotation) -> "Track":
        return Track(
            self[0],
            self[1],
            rotation
        )

    @staticmethod
    def GenerateTracks(tt: List[TrackType]) -> List["Track"]:
        ret = []
        for t in tt:
            for i in range(0, t.copies):
                ret.append(Track(
                    "{}-{}".format(t.type_id, i),
                    t,
                    None
                ))
        return ret


class StockMarket:
    """This class holds information about different ordering on the stock market itself"""
    market = (
        ["60A", "53B", "46C", "39D", "32E", "25F", "18G", "10H"],
        ["67A", "60B", "55C", "48D", "41E", "34F", "27G", "20H"],
        ["71A", "66B", "60C", "54D", "48E", "42F", "36G", "30H", "10I"],
        ["76A", "70B", "65C", "60D", "55E", "50F", "45G", "40H", "20I", "10J"],
        ["82A", "76B", "70C", "66D", "62E", "58F", "54G", "50H", "30I", "20J", "10K"],
        ["90A", "82B", "76C", "71D", "67E", "65F", "63G", "60H", "40I", "30J", "20K"],
        ["100A", "90B", "82C", "76D", "71E", "67F", "67G", "67H", "50I", "40J", "30K"],
        ["112A", "100B", "90C", "82D", "76E", "71F", "69G", "68H", "60I", "50J", "40K"],
        ["126A", "112B", "100C", "90D", "82E", "75F", "70G"],
        ["142A", "126B", "111C", "100D", "90E", "80F"],
        ["160A", "142B", "125C", "110D", "100E"],
        ["180A", "160B", "140C", "120D"],
        ["200A", "180B", "155C", "130D"],
        ["225A", "200B", "170C"],
        ["250A", "220B", "185C"],
        ["275A", "240B", "200C"],
        ["300A", "260B"],
        ["325A", "280B"],
        ["350A", "300B"]
    )

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
        self.cash = self.cash - amount / STOCK_CERTIFICATE * price

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


class StockPurchaseSource(IntEnum):
    IPO = 1
    BANK = 2


class StockStatus(IntEnum):
    NORMAL = 1
    YELLOW = 2
    ORANGE = 3
    BROWN = 4


class PublicCompany:
    FILES = ["public_companies",]

    @classmethod
    def load(cls):
        ret = []
        for f in cls.FILES:
            with open(os.path.join(DATA_DIR, f)) as json_file:
                data = json.load(json_file)
                for d in data:
                    ret.append(cls.initiate(**d))
        return ret

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
        self.base: str = None  # Original station/token location
        self.short_name: str = None
        self.president: Player = None
        self.stockPrice = {StockPurchaseSource.IPO: 0, StockPurchaseSource.BANK: 0}
        self.owners = {}
        self.stocks = {StockPurchaseSource.IPO: 100, StockPurchaseSource.BANK: 0}
        self.stock_column = 6  # Used to determine 2d action on the stock market.
        self.stock_row: int = None  # Determined elsewhere
        self.stock_status = StockStatus.NORMAL

        self.token: List[int] = []  # Cost for each subsequent token / station

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
        # Price goes up if there are no stocks left; conversely, the row goes down by one space.
        self.stock_row = max([int(self.stock_row - 1), 0])
        self.stockPrice[StockPurchaseSource.BANK] = int(STOCK_MARKET[self.stock_column][self.stock_row][0:-1])

    def priceDown(self, spaces: int):
        """
        :param spaces:
        :return:
        """
        stock_column = STOCK_MARKET[self.stock_column]
        self.stock_row = min([int(self.stock_row + spaces), len(stock_column)])
        self.stockPrice[StockPurchaseSource.BANK] = int(stock_column[self.stock_row][0:-1])

    def checkPresident(self):
        """Goes through owners and determines who the president is.
        The minimum ownership (20%) is not enforced here."""

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
        self.stock_column = 6  # IPO is all in the 7th stock column
        try:
            self.stock_row = next(i for i, v in enumerate(STOCK_MARKET[self.stock_column]) if int(v[0:-1]) == ipo_price)
        except StopIteration:
            raise IndexError("Can't find an IPO price of {}".format(ipo_price))

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

    @staticmethod
    def allPublicCompanies() -> List["PublicCompany"]:
        content = []
        data_path = os.path.join(DATA_DIR, "public_companies")

        with open(data_path) as f:
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
        self.belongs_to: Union[Player, PublicCompany] = None
        self.player_bids: List[PlayerBid] = None
        self.passed_by: List[Player] = None
        # ^-- This is a list of people who have passed on a private company in a bidding round.
        self.pass_count = None
        self.active: bool = True

    @staticmethod
    def load() -> List["PrivateCompany"]:
        data_path = os.path.join(DATA_DIR, "private_companies")
        with open(data_path) as f:
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
        pc.revenue = int(revenue)
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
        if self.active:
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

        # We may be using a company id instead if we are dealing with a public company.
        # TODO: This could be a security problem, if we are playing with cheaters, is that something worth worrying about?
        # Specifically, they could extract the company id and send moves as the company
        # (Unlike player ids, which are not accessible to everyone)
        # You'd have to be a do-nothing loser to actually do that though.
        self.company_id: str = None
        self.player: Player = None
        self.msg = None

    def backfill(self, state) -> None:
        """We do not have all the context when we receive a move; we are only passed a JSON text file, not the
        objects themselves.  We receive the objects from the game object when executing the Minigame.
        We bind those objects when the minigame is run, keeping ID values to allow us to match them up to the object itself"""

        for player in state.players:
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
