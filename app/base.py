import os
import uuid
from enum import Enum
from functools import reduce
from typing import NamedTuple, List, Set, Dict, Tuple, Optional
from dataclasses import dataclass, field

import logging

STOCK_PRESIDENT_CERTIFICATE = 20
STOCK_CERTIFICATE = 10


@dataclass
class PriceHistoryEntry:
    """Records a single stock price change event.

    Used for historical tracking, debugging, and frontend visualization.
    Enables price charts, audit trails, and game replay.
    """
    round_number: int  # Which game round this occurred
    old_price: int  # Price before change
    new_price: int  # Price after change
    reason: str  # Why the price changed (e.g., "Stock sold", "Dividend paid", "Withheld")
    player_id: Optional[str] = None  # Player who triggered the change (if applicable)
    timestamp: Optional[str] = None  # ISO timestamp for audit trail


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
        self.stock_round_passed: int = 0  # If every player passes during the stock round, the round is over.
        self.stock_round_play:int = 0
        self.stock_round_count: int = 0
        self.players: List[Player] = None
        self.priority_deal_player: Player = None
        # Track which public companies have laid track during the current
        # operating round. Keys are company ids.
        self.track_laid: Set[str] = set()

    pass


class Color(Enum):
    GRAY = 1
    YELLOW = 2
    GREEN = 3
    BROWN = 4
    RED = 5


class TerrainType(Enum):
    """Terrain types that affect track laying costs."""
    NORMAL = 1
    MOUNTAIN = 2
    BRIDGE = 3
    TUNNEL = 4


class PowerType(Enum):
    """Types of special powers that private companies can grant."""
    EXTRA_TOKEN = 1        # Additional token placement
    REVENUE_BONUS = 2      # Bonus revenue on routes
    FREE_TRACK = 3         # Free or discounted track laying
    TERRAIN_DISCOUNT = 4   # Ignore or reduce terrain costs
    TRAIN_DISCOUNT = 5     # Discount on train purchases


@dataclass
class SpecialPower:
    """Base class for private company special powers."""
    power_type: PowerType
    description: str
    active: bool = True
    expires_on_use: bool = False  # Power consumed after one use
    uses_remaining: int = None    # None = unlimited uses

    def can_use(self) -> bool:
        """Check if this power can still be used."""
        if not self.active:
            return False
        if self.uses_remaining is not None:
            return self.uses_remaining > 0
        return True

    def use(self) -> bool:
        """Use the power. Returns True if successful."""
        if not self.can_use():
            return False

        if self.uses_remaining is not None:
            self.uses_remaining -= 1

        if self.expires_on_use:
            self.active = False

        return True

    def deactivate(self) -> None:
        """Permanently deactivate this power."""
        self.active = False


@dataclass
class ExtraTokenPower(SpecialPower):
    """Grants additional token placement(s)."""
    token_count: int = 1  # Number of extra tokens

    def __post_init__(self):
        if self.power_type is None:
            self.power_type = PowerType.EXTRA_TOKEN


@dataclass
class RevenueBonusPower(SpecialPower):
    """Adds bonus revenue to routes."""
    bonus_amount: int = 0  # Fixed bonus per route
    bonus_multiplier: float = 1.0  # Multiplier (e.g., 1.2 for +20%)

    def __post_init__(self):
        if self.power_type is None:
            self.power_type = PowerType.REVENUE_BONUS

    def apply_bonus(self, base_revenue: int) -> int:
        """Calculate total revenue with bonus applied."""
        return int(base_revenue * self.bonus_multiplier) + self.bonus_amount


@dataclass
class FreeTrackPower(SpecialPower):
    """Grants free or discounted track laying."""
    discount_percent: float = 1.0  # 1.0 = free, 0.5 = half price
    tile_colors: List[Color] = None  # None = all colors

    def __post_init__(self):
        if self.power_type is None:
            self.power_type = PowerType.FREE_TRACK

    def get_discount_multiplier(self, tile_color: Color = None) -> float:
        """Get the discount multiplier for a given tile color."""
        if self.tile_colors is None or tile_color in self.tile_colors:
            return 1.0 - self.discount_percent
        return 1.0  # No discount


@dataclass
class TerrainDiscountPower(SpecialPower):
    """Reduces or eliminates terrain costs."""
    terrain_types: List[TerrainType] = None  # None = all terrain
    discount_percent: float = 1.0  # 1.0 = ignore terrain, 0.5 = half cost

    def __post_init__(self):
        if self.power_type is None:
            self.power_type = PowerType.TERRAIN_DISCOUNT

    def applies_to_terrain(self, terrain: TerrainType) -> bool:
        """Check if this power applies to the given terrain type."""
        if self.terrain_types is None:
            return True
        return terrain in self.terrain_types


@dataclass
class TrainDiscountPower(SpecialPower):
    """Provides discount on train purchases."""
    discount_amount: int = 0  # Fixed discount
    discount_percent: float = 0.0  # Percentage discount (0.2 = 20% off)

    def __post_init__(self):
        if self.power_type is None:
            self.power_type = PowerType.TRAIN_DISCOUNT

    def apply_discount(self, train_cost: int) -> int:
        """Calculate discounted train cost."""
        discounted = int(train_cost * (1.0 - self.discount_percent))
        discounted -= self.discount_amount
        return max(0, discounted)


class Train:
    def __init__(self, train_type: str, cost: int, rusts_on: str = None):
        self.type = train_type
        self.cost = cost
        self.rusts_on = rusts_on


class Route(NamedTuple):
    stops: List[str]


class Token(NamedTuple):
    company: 'PublicCompany'
    location: str
    cost: int = 0


@dataclass
class Tile:
    id: str
    id_v2: str
    color: Color
    location: str
    rotation: int
    slots: int = 1
    tokens: List[str] = field(default_factory=list)
    extra_slots_cost: Optional[int] = None
    terrain: 'TerrainType' = None  # Terrain type affecting placement cost

    def __post_init__(self):
        """Ensure terrain defaults to NORMAL if not specified."""
        if self.terrain is None:
            from app.base import TerrainType
            self.terrain = TerrainType.NORMAL


@dataclass
class Loan:
    """Represents a loan taken by a company from its president or the bank.

    Loans accrue interest each operating round and must be repaid. If a company
    defaults on its loans, consequences include forced share sales, presidency
    transfer, and potentially receivership.
    """
    id: str
    principal: int  # Original loan amount
    balance: int  # Current outstanding balance
    interest_rate: float  # Interest rate per operating round (e.g., 0.05 for 5%)
    lender: 'Player'  # Who provided the loan (usually president)
    round_taken: int  # Which operating round the loan was taken

    def accrue_interest(self) -> None:
        """Apply interest to the loan balance."""
        self.balance = int(self.balance * (1 + self.interest_rate))

    def make_payment(self, amount: int) -> int:
        """Make a payment towards the loan. Returns actual amount paid."""
        actual_payment = min(amount, self.balance)
        self.balance -= actual_payment
        return actual_payment

    def is_paid_off(self) -> bool:
        """Check if loan is fully repaid."""
        return self.balance <= 0


class Direction(Enum):
    LEFT = 1
    RIGHT = 2
    UP = 3
    DOWN = 4
    UP_RIGHT = 5
    DOWN_LEFT = 6


class Band(Enum):
    WHITE = 1
    YELLOW = 2
    BROWN = 3


class Cell(NamedTuple):
    price: int
    band: Band
    arrow: Direction = None


class StockMarket:
    """Represents the 12×5 stock market grid."""

    def __init__(self, grid: List[List[Cell]]):
        self.grid = grid

    def cell(self, row: int, col: int) -> Cell:
        return self.grid[row][col]

    def max_col(self) -> int:
        return len(self.grid[0]) - 1

    def max_row(self) -> int:
        return len(self.grid) - 1

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row <= self.max_row() and 0 <= col <= self.max_col()

    def next_coord(self, row: int, col: int, direction: Direction) -> Tuple[int, int]:
        if direction == Direction.UP:
            return row - 1, col
        if direction == Direction.DOWN:
            return row + 1, col
        if direction == Direction.LEFT:
            return row, col - 1
        if direction == Direction.RIGHT:
            return row, col + 1
        if direction == Direction.UP_RIGHT:
            return row - 1, col + 1
        if direction == Direction.DOWN_LEFT:
            return row + 1, col - 1
        return row, col

    def move_marker(self, company: "PublicCompany", direction: Direction, steps: int = 1, reason: str = "Market movement") -> None:
        row, col = company.stock_pos
        for _ in range(steps):
            nr, nc = self.next_coord(row, col, direction)
            if not self.in_bounds(nr, nc):
                break
            row, col = nr, nc
        company.stock_pos = (row, col)
        company.update_price_from_pos(reason)

    def on_sale(self, company: "PublicCompany", percentage: int) -> None:
        steps = percentage // 10
        if steps > 0:
            shares_sold = percentage // 10
            self.move_marker(company, Direction.DOWN, steps, f"Stock sold ({shares_sold}% of company)")

    def on_withhold(self, company: "PublicCompany") -> None:
        cell = self.cell(*company.stock_pos)
        direction = cell.arrow if cell.arrow == Direction.DOWN_LEFT else Direction.LEFT
        self.move_marker(company, direction, 1, "Revenue withheld")

    def move(self, company: "PublicCompany", direction: Direction) -> None:
        """Move ``company`` one step in ``direction`` respecting board edges."""
        self.move_marker(company, direction, 1, "Manual market movement")

    def on_payout(self, company: "PublicCompany") -> None:
        cell = self.cell(*company.stock_pos)
        if cell.arrow:
            direction = cell.arrow
        else:
            if cell.band == Band.YELLOW:
                return
            direction = Direction.UP_RIGHT if cell.band == Band.BROWN else Direction.RIGHT
        self.move_marker(company, direction, 1, "Dividend paid")

    def on_sold_out(self, company: "PublicCompany") -> None:
        if company.stock_pos[0] > 0:
            self.move_marker(company, Direction.UP, 1, "Stock sold out")

    def sort_companies(self, companies: List["PublicCompany"]) -> List["PublicCompany"]:
        return sorted(
            companies,
            key=lambda c: (
                -self.cell(*c.stock_pos).price,
                c.stock_pos[0]
            ),
        )


class Player:
    """Individual player in the game.

    OBJECT RELATIONSHIPS (PR #11 - Cross-Linking Patterns):
    -------------------------------------------------------
    Players have bidirectional relationships with game entities. This is intentional
    and enables efficient queries without complex joins or searches.

    PLAYER ←→ PUBLICCOMPANY:
    - Player.portfolio: Set[PublicCompany] - Companies player owns shares in
    - PublicCompany.owners: Dict[Player, int] - % ownership per player
    - PublicCompany.president: Player - Current president

    PLAYER ←→ PRIVATECOMPANY:
    - Player.private_companies: Set[PrivateCompany] - Private companies owned
    - PrivateCompany.belongs_to: Player - Owner of the private company

    RATIONALE FOR BIDIRECTIONAL REFERENCES:
    ---------------------------------------
    1. **Performance**: O(1) access to related entities without searching
    2. **Convenience**: Easy to query "which companies does player own?" and
       "who owns this company?"
    3. **Consistency**: Updates must maintain both sides of relationship

    MANAGING RELATIONSHIPS:
    ----------------------
    Use helper methods to maintain consistency:
    - PublicCompany.buy() / sell() - Update both owners dict and player portfolio
    - PublicCompany.grantStock() - Add to owners dict
    - PrivateCompany.setBelongs() - Update both belongs_to and player.private_companies
    - PublicCompany.checkPresident() - Update president reference

    ALTERNATIVE APPROACHES CONSIDERED:
    ---------------------------------
    - **Unidirectional (owners only)**: Simpler but requires O(n) searches for
      "what does player own?"
    - **Separate ownership table**: More database-like but overhead for simple game
    - **Weak references**: Complex lifetime management, not worth the complexity

    LIFECYCLE NOTES:
    ---------------
    - Objects created via factory methods (Player.create(), PublicCompany.initiate())
    - Relationships established via game logic (stock purchases, sales)
    - No explicit cleanup needed - Python GC handles it
    - For serialization, use object IDs and reconstruct relationships on load

    TODO RESOLVED (was line 385):
    ----------------------------
    Cross-linking is intentional and beneficial. Key pattern:
    - Use helper methods to update both sides atomically
    - Document ownership semantics clearly
    - Test relationship consistency in edge cases

    Example of proper relationship management:
        >>> company.buy(player, StockPurchaseSource.IPO, 20)
        # This updates:
        # - company.owners[player] += 20
        # - player.portfolio.add(company)
        # - player.cash -= cost
        # All in one atomic operation

    SECURITY NOTE:
    -------------
    There is no authorization at this level. Authentication/permissions should be
    handled at the API/frontend layer. This class represents the game character.
    """

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
        # Track private companies owned by this player for certificate limits
        self.private_companies: Set['PrivateCompany'] = set()
        # Corporations this player sold stock in during the current stock round
        self.sold_this_round: Set['PublicCompany'] = set()

    @staticmethod
    def create(name, cash, order) -> "Player":
        ret = Player()
        ret.id = str(uuid.uuid4())
        ret.name = name
        ret.cash = cash
        ret.order = order
        ret.private_companies = set()
        ret.sold_this_round = set()
        return ret

    def addToPortfolio(self, company: "PublicCompany", amount: int, price: int):
        """Add company to player's portfolio and deduct cost.

        This maintains the bidirectional Player ←→ PublicCompany relationship.
        See class docstring for relationship management patterns.

        Args:
            company: PublicCompany to add to portfolio
            amount: Percentage of company being purchased (10, 20, etc.)
            price: Price per share

        Note:
            This should typically be called via PublicCompany.buy() which updates
            both sides of the relationship atomically.
        """
        self.portfolio.add(company)
        self.cash = self.cash - amount  / STOCK_CERTIFICATE * price

    def getCertificateCount(self):
        total_stock_certificates = 0

        for public_company in self.portfolio:
            total_stock_certificates += public_company.owners[self] / 10
            if public_company.president == self:  # President has a 20% stock certificate
                total_stock_certificates -= 1

        total_private = len(self.private_companies)
        return total_stock_certificates + total_private

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
        self.tokens = {}

    def setTrack(self, track: Tile):
        self.board[track.location] = track

    def place_token(self, corp: 'PublicCompany', hex_id: str) -> bool:
        tile = self.board.get(hex_id)
        if tile is None:
            return False
        occupied = len(tile.tokens)
        if occupied < tile.slots:
            tile.tokens.append(corp.id)
            return True
        if occupied >= tile.slots and tile.extra_slots_cost is not None:
            tile.tokens.append(corp.id)
            return True
        return False

    def setToken(self, token: Token):
        self.tokens.setdefault(token.location, []).append(token)
        if hasattr(token.company, "tokens"):
            token.company.tokens.append(token)
        tile = self.board.get(token.location)
        if tile is not None and token.company.id not in tile.tokens:
            tile.tokens.append(token.company.id)

    def calculateRoute(self, route) -> int:
        return len(route.stops) * 10


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
        self.tokens_available: int = 0
        self.token_costs: List[int] = []
        self.president: Player = None
        self.stockPrice = {StockPurchaseSource.IPO: 0, StockPurchaseSource.BANK: 0}
        self.owners = {}
        self.stocks = {StockPurchaseSource.IPO: 100, StockPurchaseSource.BANK: 0}
        self.stock_status = StockStatus.NORMAL
        self.bankrupt = False
        self.tokens: List[Token] = []
        self.token_count: int = 0
        self.token_placed: bool = False
        self.stock_market: StockMarket = None
        self.stock_pos: Tuple[int, int] = (0, 0)
        self.loans: List[Loan] = []  # Outstanding loans
        self.price_history: List[PriceHistoryEntry] = []  # Historical price changes

    @staticmethod
    def initiate(**kwargs):
        x = PublicCompany()
        for k, v in kwargs.items():
            x.__dict__[k] = v
        if 'token_costs' not in kwargs:
            x.token_costs = []
        if 'token_count' not in kwargs:
            x.token_count = len(x.token_costs)
        if 'tokens_available' not in kwargs:
            x.tokens_available = x.token_count
        x.token_placed = False
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

    def attach_market(self, market: StockMarket, row: int = 0, col: int = 0) -> None:
        self.stock_market = market
        self.stock_pos = (row, col)
        self.update_price_from_pos("Initial market price")

    def update_price_from_pos(self, reason: str = "Market movement") -> None:
        if self.stock_market:
            old_price = self.stockPrice[StockPurchaseSource.BANK]
            value = self.stock_market.cell(*self.stock_pos).price
            self.stockPrice[StockPurchaseSource.BANK] = value
            self.stockPrice[StockPurchaseSource.IPO] = value

            # Record price change if it actually changed
            if old_price != value:
                self.record_price_change(old_price, value, reason)

    def checkPriceIncrease(self):
        if self.stocks[StockPurchaseSource.IPO] == 0 and self.stocks[StockPurchaseSource.BANK] == 0:
            if self.stock_market:
                self.stock_market.on_sold_out(self)
            else:
                self.priceUp(1)

    def priceUp(self, spaces, reason: str = "Price increase"):
        if self.stock_market:
            for _ in range(spaces):
                self.stock_market.move_marker(self, Direction.RIGHT, 1, reason)
        else:
            old_price = self.stockPrice[StockPurchaseSource.BANK]
            increment = spaces * 10
            self.stockPrice[StockPurchaseSource.BANK] += increment
            new_price = self.stockPrice[StockPurchaseSource.BANK]
            self.record_price_change(old_price, new_price, f"{reason} ({spaces} spaces)")

    def priceDown(self, amount):
        if self.stock_market:
            self.stock_market.on_sale(self, amount)
        else:
            old_price = self.stockPrice[StockPurchaseSource.BANK]
            decrement = (amount // STOCK_CERTIFICATE) * 10
            self.stockPrice[StockPurchaseSource.BANK] = max(
                0, self.stockPrice[StockPurchaseSource.BANK] - decrement
            )
            new_price = self.stockPrice[StockPurchaseSource.BANK]
            if old_price != new_price:
                shares_sold = amount // STOCK_CERTIFICATE
                self.record_price_change(old_price, new_price, f"Stock sold ({shares_sold} shares)")

    def checkPresident(self):
        """Determine if control of the company should change hands.

        The new president must own more shares than the current one and hold at
        least 20% of the company. If multiple players tie for the highest
        qualifying share count, the one closest to the outgoing president in
        turn order becomes the new president."""

        if not self.owners:
            return

        current_share = self.owners.get(self.president, 0) if self.president else 0
        max_ownership = max(self.owners.values())

        # No eligible replacement if nobody holds at least 20% or the current
        # president is tied for the lead.
        if (max_ownership <= current_share or
                max_ownership < STOCK_PRESIDENT_CERTIFICATE):
            return

        # Collect all players with the largest share count.
        top_owners = [p for p, v in self.owners.items() if v == max_ownership]

        if len(top_owners) == 1 or self.president is None:
            self.president = top_owners[0]
            return

        play_order = self.president.order
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
        """Distribute ``_income`` according to share ownership."""
        for owner, percent in self.owners.items():
            player: Player = owner
            player.cash += int(self._income * percent / 100.0)

        # Unsold IPO shares pay into the company's treasury
        self.cash += int(self._income * self.stocks[StockPurchaseSource.IPO] / 100.0)

        receiverless = self.outstanding_shares == 0

        self._income = 0
        if self.stock_market:
            if receiverless:
                self.stock_market.on_withhold(self)
            else:
                self.stock_market.on_payout(self)

    def incomeToCash(self):
        self.cash += self._income
        self._income = 0
        if self.stock_market:
            self.stock_market.on_withhold(self)

    def addIncome(self, amount: int) -> None:
        self._income += amount

    def next_token_cost(self) -> int:
        index = len(self.token_costs) - self.tokens_available
        if 0 <= index < len(self.token_costs):
            return self.token_costs[index]
        return 0

    def removeRustedTrains(self, rusted_train_type: str):
        self.trains = [train for train in self.trains if train.type != rusted_train_type]

    def isFloated(self) -> bool:
        return self._floated

    def hasNoTrains(self) -> bool:
        return len(self.trains) == 0

    @property
    def outstanding_shares(self) -> int:
        """Total shares held by all players."""
        return sum(self.owners.values())

    def hasValidRoute(self, board: 'GameBoard' = None) -> bool:
        """Return ``True`` if this company can currently operate a route.

        The check is intentionally lightweight but verifies more than simply
        owning a train.  A company must have at least one station token placed
        on the board and there must exist a continuous path starting from one
        of its stations.  The implementation only approximates route
        validation; track orientation and complex board rules are ignored.
        """

        if not self.tokens:
            return False

        if self.hasNoTrains():
            return False

        return True

    def take_loan(self, amount: int, lender: Player, interest_rate: float, current_round: int) -> Loan:
        """Take a loan from a player (usually president) or the bank."""
        import uuid
        loan = Loan(
            id=str(uuid.uuid4()),
            principal=amount,
            balance=amount,
            interest_rate=interest_rate,
            lender=lender,
            round_taken=current_round
        )
        self.loans.append(loan)
        self.cash += amount
        lender.cash -= amount
        return loan

    def repay_loan(self, loan: Loan, amount: int) -> int:
        """Repay a loan (or part of it). Returns the actual amount repaid."""
        if loan not in self.loans:
            return 0

        actual_payment = loan.make_payment(amount)
        self.cash -= actual_payment
        loan.lender.cash += actual_payment

        # Remove loan if fully paid off
        if loan.is_paid_off():
            self.loans.remove(loan)

        return actual_payment

    def accrue_loan_interest(self) -> None:
        """Apply interest to all outstanding loans."""
        for loan in self.loans:
            loan.accrue_interest()

    def total_debt(self) -> int:
        """Calculate total outstanding debt."""
        return sum(loan.balance for loan in self.loans)

    def can_service_debt(self) -> bool:
        """Check if company has enough cash to cover minimum debt payments."""
        # Minimum payment is typically 10% of total debt per round
        min_payment = int(self.total_debt() * 0.1)
        return self.cash >= min_payment

    def record_price_change(
        self,
        old_price: int,
        new_price: int,
        reason: str,
        round_number: int = 0,
        player_id: Optional[str] = None
    ) -> None:
        """Record a stock price change in the history.

        Args:
            old_price: Price before the change
            new_price: Price after the change
            reason: Why the price changed (e.g., "Stock sold", "Dividend paid")
            round_number: Which game round this occurred (default 0 if not tracked)
            player_id: Player who triggered the change (optional)
        """
        from datetime import datetime
        entry = PriceHistoryEntry(
            round_number=round_number,
            old_price=old_price,
            new_price=new_price,
            reason=reason,
            player_id=player_id,
            timestamp=datetime.now().isoformat()
        )
        self.price_history.append(entry)

    def get_price_history(
        self,
        limit: Optional[int] = None,
        since_round: Optional[int] = None
    ) -> List[PriceHistoryEntry]:
        """Query the price history with optional filtering.

        Args:
            limit: Maximum number of entries to return (most recent first)
            since_round: Only return entries from this round onwards

        Returns:
            List of PriceHistoryEntry objects
        """
        history = self.price_history

        if since_round is not None:
            history = [e for e in history if e.round_number >= since_round]

        if limit is not None:
            history = history[-limit:]

        return history

    def get_current_price(self) -> int:
        """Get the current stock price (from BANK source)."""
        return self.stockPrice[StockPurchaseSource.BANK]


class PrivateCompany:
    def __eq__(self, o: "PrivateCompany") -> bool:
        """Allows duck typed comparisons between objects"""
        return isinstance(o, PrivateCompany) and self.order == o.order

    def __hash__(self) -> int:
        return hash(self.order)

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
        self.special_powers: List[SpecialPower] = []  # Special powers granted by this private company

    @staticmethod
    def allPrivateCompanies() -> List["PrivateCompany"]:
        data_path = os.path.join(os.path.dirname(__file__), 'data', 'private_companies')
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
                 pass_count: int = 0,
                 special_powers: List[SpecialPower] = None) -> "PrivateCompany":
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
        pc.special_powers = special_powers if special_powers is not None else []

        return pc

    def get_powers_by_type(self, power_type: PowerType) -> List[SpecialPower]:
        """Get all active powers of a specific type."""
        return [p for p in self.special_powers if p.power_type == power_type and p.can_use()]

    def has_active_power(self, power_type: PowerType) -> bool:
        """Check if this private company has any active powers of the given type."""
        return len(self.get_powers_by_type(power_type)) > 0

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
        if self.belongs_to and hasattr(self.belongs_to, "private_companies"):
            self.belongs_to.private_companies.discard(self)
        self.belongs_to = player
        if player:
            if not hasattr(player, "private_companies"):
                player.private_companies = set()
            player.private_companies.add(self)
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

    def backfill(self, game_state: MutableGameState) -> None:
        """We do not have all the context when we receive a move; we are only passed a JSON text file, not the
        objects themselves.  We receive the objects from the game object when executing the Minigame.
        We bind those objects when the minigame is run, keeping ID values to allow us to match them up to the object itself"""

        for player in game_state.players:
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
