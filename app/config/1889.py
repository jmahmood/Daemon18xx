from app.base import PrivateCompany, PublicCompany, Train, Color


def starting_cash(num_players: int) -> int:
    return int(2500 / num_players)


PRIVATE_COMPANIES = [
    PrivateCompany.initiate(1, "Shinano Railway", "SR", 20, 5, "Z1"),
    PrivateCompany.initiate(2, "Iyo Railway", "IR", 40, 10, "Z2"),
    PrivateCompany.initiate(3, "Osaka Railway", "OR", 80, 15, "Z3"),
    PrivateCompany.initiate(4, "Kyushu Steamship", "KS", 160, 20, "Z4"),
    PrivateCompany.initiate(5, "Hokkaido Coal", "HC", 200, 25, "Z5"),
]

TOKEN_COUNTS = {
    "SR": 4,
    "UR": 3,
}

TRACK_LAYING_COSTS = {
    Color.YELLOW: 0,
    Color.GREEN: 0,
    Color.BROWN: 100,
    Color.RED: 200,
}

SPECIAL_HEX_RULES = {
    "Z1": "SR home hex",
}

PUBLIC_COMPANIES = [
    PublicCompany.initiate(id="SR", name="Sanyo Railway", short_name="SR",
                           tokens_available=4, token_costs=[40, 60, 80, 100]),
    PublicCompany.initiate(id="UR", name="Ueda Railway", short_name="UR",
                           tokens_available=4, token_costs=[40, 60, 80, 100]),
]

STOCK_MARKET = []
TRAINS = [Train("2", 90, rusts_on="4"), Train("3", 180, rusts_on="6")]
OPERATING_ROUNDS = 2

