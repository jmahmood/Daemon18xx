from typing import NamedTuple, List


class Player:
    pass


class PlayerBid(NamedTuple):
    player: Player
    bid_amount: int


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



