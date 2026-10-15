"""Standard Shikoku 1889 component and phase definitions (no beginner options)."""

from .board_data import DATA as BOARD_DATA

PAR_PRICES = (65, 70, 75, 80, 90, 100)
CERT_LIMITS = {2: 25, 3: 19, 4: 14, 5: 12, 6: 11}
CORPORATIONS = {
    "AR": ("Awa Railroad", "K8", 2),
    "IR": ("Iyo Railway", "E2", 2),
    "SR": ("Sanuki Railway", "I2", 2),
    "KO": ("Takamatsu & Kotohira Electric Railway", "K4", 2),
    "TR": ("Tosa Electric Railway", "F9", 3),
    "KU": ("Tosa Kuroshio Railway", "C10", 1),
    "UR": ("Uwajima Railway", "B7", 3),
}
PRIVATES = {
    "TR": ("Takamatsu E-Railroad", 20, 5, ["K4"]),
    "MF": ("Mitsubishi Ferry", 30, 5, []),
    "ER": ("Ehime Railway", 40, 10, ["C4"]),
    "SMR": ("Sumitomo Mines Railway", 50, 15, []),
    "DR": ("Dougo Railway", 60, 15, []),
    "SIR": ("South Iyo Railway", 80, 20, []),
    "UTF": ("Uno-Takamatsu Ferry", 150, 30, []),
}
TRAIN_TYPES = {
    "2": (6, 80, 2),
    "3": (5, 180, 3),
    "4": (4, 300, 4),
    "5": (3, 450, 5),
    "6": (2, 630, 6),
    "D": (1, 1100, 999),
}
PHASES = {
    "2": (4, ["yellow"], 1),
    "3": (4, ["yellow", "green"], 2),
    "4": (3, ["yellow", "green"], 2),
    "5": (2, ["yellow", "green", "brown"], 3),
    "6": (2, ["yellow", "green", "brown"], 3),
    "D": (2, ["yellow", "green", "brown"], 3),
}
RUSTS = {"4": "2", "6": "3", "D": "4"}
# Geometric upgrades additionally preserve node types, labels, track and tokens.
UPGRADES = {
    tid: [
        n
        for n, t in BOARD_DATA["tiles"].items()
        if ["yellow", "green", "brown"].index(t["color"])
        == ["yellow", "green", "brown"].index(old["color"]) + 1
    ]
    for tid, old in BOARD_DATA["tiles"].items()
    if old["color"] != "brown" and tid != "437"
}
MARKET_TEXT = [
    "75 80 90 100p 110 125 140 155 175 200 225 255 285 315 350",
    "70 75 80 90p 100 110 125 140 155 175 200 225 255 285 315",
    "65 70 75 80p 90 100 110 125 140 155 175 200",
    "60 65 70 75p 80 90 100 110 125 140",
    "55 60 65 70p 75 80 90 100",
    "50y 55 60 65p 70 75 80",
    "45y 50y 55 60 65 70",
    "40y 45y 50y 55 60",
    "30o 40y 45y 50y",
    "20o 30o 40y 45y",
    "10o 20o 30o 40y",
]
MARKET = [
    [
        {
            "price": int(c.rstrip("yop")),
            "zone": c[-1] if c[-1] in "yo" else "white",
            "par": c.endswith("p"),
        }
        for c in row.split()
    ]
    for row in MARKET_TEXT
]
PAR_POSITIONS = {
    cell["price"]: [r, c]
    for r, row in enumerate(MARKET)
    for c, cell in enumerate(row)
    if cell["par"]
}
