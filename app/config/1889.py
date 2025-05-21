from app.base import PrivateCompany, PublicCompany, Train


def starting_cash(num_players: int) -> int:
    return int(2500 / num_players)


PRIVATE_COMPANIES = [
    PrivateCompany.initiate(1, "Shinano Railway", "SR", 20, 5, "Z1"),
    PrivateCompany.initiate(2, "Iyo Railway", "IR", 40, 10, "Z2"),
    PrivateCompany.initiate(3, "Osaka Railway", "OR", 80, 15, "Z3"),
    PrivateCompany.initiate(4, "Kyushu Steamship", "KS", 160, 20, "Z4"),
    PrivateCompany.initiate(5, "Hokkaido Coal", "HC", 200, 25, "Z5"),
]

PUBLIC_COMPANIES = [
    PublicCompany.initiate(id="SR", name="Sanyo Railway", short_name="SR"),
    PublicCompany.initiate(id="UR", name="Ueda Railway", short_name="UR"),
]

STOCK_MARKET = []
TRAINS = [Train("2", 90, rusts_on="4"), Train("3", 180, rusts_on="6")]
OPERATING_ROUNDS = 2

