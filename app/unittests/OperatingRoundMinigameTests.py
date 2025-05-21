import unittest
from app.base import GameBoard, Track, Token, Route, PublicCompany, MutableGameState, Player, Train, Color
from app.minigames.operating_round import OperatingRound, OperatingRoundMove


def fake_player(id="A", cash=1000, order=0):
    p = Player()
    p.id = id
    p.cash = cash
    p.order = order
    return p


def fake_company(name="1", cash=1000):
    pc = PublicCompany.initiate(name=f"Company {name}", short_name=f"C{name}", id=name, cash=cash)
    pc.trains = []
    pc._income = 0
    pc.owners = {}
    return pc


class PlayerTurnStub:
    def __init__(self, waiting=True):
        self.waiting = waiting
    def anotherCompanyWaiting(self):
        return self.waiting
    def restart(self):
        pass


class OperatingRoundTrackTests(unittest.TestCase):
    def setUp(self):
        self.board = GameBoard()
        self.state = MutableGameState()
        self.state.players = [fake_player("A")]
        self.company = fake_company("A")
        self.state.public_companies = [self.company]

    def test_valid_track_placement(self):
        move = OperatingRoundMove()
        move.player_id = "A"
        move.construct_track = True
        move.track = Track("1", "1", Color.YELLOW, "A1", 0)
        move.public_company = self.company
        oround = OperatingRound()
        self.assertTrue(oround.run(move, self.state, board=self.board))
        self.assertIn("A1", self.board.board)

    def test_invalid_same_color_upgrade(self):
        self.board.setTrack(Track("1", "1", Color.YELLOW, "A1", 0))
        move = OperatingRoundMove()
        move.player_id = "A"
        move.construct_track = True
        move.track = Track("2", "2", Color.YELLOW, "A1", 0)
        move.public_company = self.company
        oround = OperatingRound()
        self.assertFalse(oround.run(move, self.state, board=self.board))


class OperatingRoundTokenTests(unittest.TestCase):
    def setUp(self):
        self.board = GameBoard()
        self.board.setTrack(Track("1", "1", Color.YELLOW, "A1", 0))
        self.state = MutableGameState()
        self.state.players = [fake_player("A")]
        self.company = fake_company("A")
        self.state.public_companies = [self.company]

    def test_valid_token(self):
        move = OperatingRoundMove()
        move.player_id = "A"
        move.purchase_token = True
        move.token = Token(self.company, "A1", 40)
        move.public_company = self.company
        oround = OperatingRound()
        self.assertTrue(oround.run(move, self.state, board=self.board))
        self.assertEqual(self.company.cash, 1000-40)
        self.assertIn(move.token, self.board.tokens["A1"])

    def test_invalid_token_no_track(self):
        move = OperatingRoundMove()
        move.player_id = "A"
        move.purchase_token = True
        move.token = Token(self.company, "B2", 40)
        move.public_company = self.company
        oround = OperatingRound()
        self.assertFalse(oround.run(move, self.state, board=self.board))


class OperatingRoundRouteTests(unittest.TestCase):
    def setUp(self):
        self.board = GameBoard()
        self.board.setTrack(Track("1", "1", Color.YELLOW, "A1", 0))
        self.state = MutableGameState()
        self.state.players = [fake_player("A")]
        self.company = fake_company("A")
        self.company.trains.append(Train("2", 100))
        self.state.public_companies = [self.company]

    def test_run_route_and_dividend(self):
        token = Token(self.company, "A1", 40)
        self.board.setToken(token)
        move = OperatingRoundMove()
        move.player_id = "A"
        move.run_route = True
        move.pay_dividend = False
        move.routes = [Route(["A1", "A2"])]
        move.public_company = self.company
        oround = OperatingRound()
        oround.run(move, self.state, board=self.board)
        self.assertEqual(self.company.cash, 1000 + 20)  # incomeToCash adds income

    def test_dividend_payout(self):
        token = Token(self.company, "A1", 40)
        self.board.setToken(token)
        self.company.owners = {self.state.players[0]: 100}
        move = OperatingRoundMove()
        move.player_id = "A"
        move.run_route = True
        move.pay_dividend = True
        move.routes = [Route(["A1", "A2"])]
        move.public_company = self.company
        self.company.trains.append(Train("2", 100))
        oround = OperatingRound()
        oround.run(move, self.state, board=self.board)
        self.assertEqual(self.state.players[0].cash, 1000 + 20)


class OperatingRoundTrainPurchaseTests(unittest.TestCase):
    def setUp(self):
        self.board = GameBoard()
        self.state = MutableGameState()
        self.state.players = [fake_player("A")]
        self.company = fake_company("A")
        self.state.public_companies = [self.company]

    def test_purchase_train_and_rust(self):
        move = OperatingRoundMove()
        move.player_id = "A"
        move.buy_train = True
        train = Train("3", 200, rusts_on="2")
        move.train = train
        move.public_company = self.company
        move.available_trains = [train]
        oround = OperatingRound()
        oround.run(move, self.state, board=self.board)
        self.assertIn(train, self.company.trains)
        self.assertEqual(self.company.cash, 1000-200)
        self.assertEqual(oround.rusted_train_type, "2")
        # simulate next round rusting another company's trains
        other = fake_company("B")
        other.trains.append(Train("2", 80))
        other.trains.append(Train("2", 80))
        self.assertEqual(len(other.trains), 2)
        other.removeRustedTrains(oround.rusted_train_type)
        self.assertEqual(len(other.trains), 0)


class OperatingRoundNextTests(unittest.TestCase):
    def test_next_rounds(self):
        oround = OperatingRound()
        state = {
            "public_companies": [],
            "playerTurn": PlayerTurnStub(True),
            "currentOperatingRound": 1,
            "totalOperatingRounds": 2
        }
        self.assertEqual(oround.next(**state), "OperatingRound1")
        state["playerTurn"].waiting = False
        self.assertEqual(oround.next(**state), "OperatingRound2")
        state["currentOperatingRound"] = 2
        self.assertEqual(oround.next(**state), "StockRound")


if __name__ == '__main__':
    unittest.main()
