import unittest
from app.base import GameBoard, Track, Token, Route, PublicCompany, MutableGameState, Player, Train, Color
from app.minigames.operating_round import (
    OperatingRound,
    OperatingRoundMove,
    RustedTrainMove,
    TrainsRusted,
)


def fake_player(id="A", cash=1000, order=0):
    p = Player()
    p.id = id
    p.cash = cash
    p.order = order
    return p


def fake_company(name="1", cash=1000):
    pc = PublicCompany.initiate(
        name=f"Company {name}", short_name=f"C{name}", id=name, cash=cash,
        tokens_available=4, token_costs=[40, 60, 80, 100]
    )
    pc.trains = []
    pc._income = 0
    pc.owners = {}
    return pc


class PlayerTurnStub:
    def __init__(self, waiting=True):
        self.waiting = waiting
        self.restart_called_with = None
    def anotherCompanyWaiting(self):
        return self.waiting
    def restart(self, current_or=None):
        self.restart_called_with = current_or


class OperatingRoundTrackTests(unittest.TestCase):
    def setUp(self):
        self.board = GameBoard()
        self.state = MutableGameState()
        self.state.players = [fake_player("A")]
        self.company = fake_company("A")
        self.state.public_companies = [self.company]

    def test_valid_track_placement(self):
        self.board.setToken(Token(self.company, "A1", 0))
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

    def test_invalid_track_not_connected(self):
        move = OperatingRoundMove()
        move.player_id = "A"
        move.construct_track = True
        move.track = Track("2", "2", Color.YELLOW, "B1", 0)
        move.public_company = self.company
        oround = OperatingRound()
        self.assertFalse(oround.run(move, self.state, board=self.board))

    def test_only_one_tile_per_round(self):
        self.board.setToken(Token(self.company, "A1", 0))
        move1 = OperatingRoundMove()
        move1.player_id = "A"
        move1.construct_track = True
        move1.track = Track("1", "1", Color.YELLOW, "A1", 0)
        move1.public_company = self.company
        oround = OperatingRound()
        self.assertTrue(oround.run(move1, self.state, board=self.board))

        move2 = OperatingRoundMove()
        move2.player_id = "A"
        move2.construct_track = True
        move2.track = Track("2", "2", Color.YELLOW, "A2", 0)
        move2.public_company = self.company
        self.assertFalse(oround.run(move2, self.state, board=self.board))

    def test_track_flag_resets_on_start(self):
        self.board.setToken(Token(self.company, "A1", 0))
        move1 = OperatingRoundMove()
        move1.player_id = "A"
        move1.construct_track = True
        move1.track = Track("1", "1", Color.YELLOW, "A1", 0)
        move1.public_company = self.company
        oround = OperatingRound()
        self.assertTrue(oround.run(move1, self.state, board=self.board))

        OperatingRound.onStart(self.state)

        move2 = OperatingRoundMove()
        move2.player_id = "A"
        move2.construct_track = True
        move2.track = Track("2", "2", Color.YELLOW, "A2", 0)
        move2.public_company = self.company
        self.board.setToken(Token(self.company, "A2", 0))
        self.assertTrue(oround.run(move2, self.state, board=self.board))


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
        self.assertEqual(self.company.tokens_available, 3)
        self.assertIn(move.token, self.board.tokens["A1"])
        self.assertEqual(self.company.token_count, 4)

    def test_second_token_cost(self):
        # place first token
        move = OperatingRoundMove()
        move.player_id = "A"
        move.purchase_token = True
        move.token = Token(self.company, "A1", 0)
        move.public_company = self.company
        oround = OperatingRound()
        self.assertTrue(oround.run(move, self.state, board=self.board))

        # prepare second location
        self.board.setTrack(Track("2", "2", Color.YELLOW, "B1", 0))
        move2 = OperatingRoundMove()
        move2.player_id = "A"
        move2.purchase_token = True
        move2.token = Token(self.company, "B1", 0)
        move2.public_company = self.company
        self.assertTrue(oround.run(move2, self.state, board=self.board))
        self.assertEqual(self.company.cash, 1000 - 40 - 60)
        self.assertEqual(self.company.tokens_available, 2)
        self.assertEqual(self.company.token_count, 4)

    def test_invalid_token_no_track(self):
        move = OperatingRoundMove()
        move.player_id = "A"
        move.purchase_token = True
        move.token = Token(self.company, "B2", 40)
        move.public_company = self.company
        oround = OperatingRound()
        self.assertFalse(oround.run(move, self.state, board=self.board))

    def test_invalid_token_no_tokens_left(self):
        self.company.tokens_available = 0
        move = OperatingRoundMove()
        move.player_id = "A"
        move.purchase_token = True
        move.token = Token(self.company, "A1", 40)
        move.public_company = self.company
        oround = OperatingRound()
        self.assertFalse(oround.run(move, self.state, board=self.board))

    def test_invalid_token_insufficient_cash(self):
        self.company.cash = 10
        move = OperatingRoundMove()
        move.player_id = "A"
        move.purchase_token = True
        move.token = Token(self.company, "A1", 40)
        move.public_company = self.company
        oround = OperatingRound()
        self.assertFalse(oround.run(move, self.state, board=self.board))


class OperatingRoundRouteTests(unittest.TestCase):
    def setUp(self):
        self.board = GameBoard()
        self.board.setTrack(Track("1", "1", Color.YELLOW, "A1", 0))
        self.board.setTrack(Track("2", "2", Color.YELLOW, "A2", 0))
        self.state = MutableGameState()
        self.state.players = [fake_player("A")]
        self.company = fake_company("A")
        self.company.trains.append(Train("2", 100))
        self.state.public_companies = [self.company]

    def test_run_route_and_dividend(self):
        token = Token(self.company, "A1", self.company.token_costs[0])
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
        token = Token(self.company, "A1", self.company.token_costs[0])
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

    def test_invalid_route_no_token(self):
        move = OperatingRoundMove()
        move.player_id = "A"
        move.run_route = True
        move.pay_dividend = False
        move.routes = [Route(["A1", "A2"])]
        move.public_company = self.company
        oround = OperatingRound()
        self.assertFalse(oround.run(move, self.state, board=self.board))

    def test_invalid_route_missing_track(self):
        token = Token(self.company, "A1", self.company.token_costs[0])
        self.board.setToken(token)
        move = OperatingRoundMove()
        move.player_id = "A"
        move.run_route = True
        move.routes = [Route(["A1", "B1"])]
        move.public_company = self.company
        oround = OperatingRound()
        self.assertFalse(oround.run(move, self.state, board=self.board))

    def test_invalid_route_too_many_routes(self):
        token = Token(self.company, "A1", self.company.token_costs[0])
        self.board.setToken(token)
        move = OperatingRoundMove()
        move.player_id = "A"
        move.run_route = True
        move.routes = [Route(["A1", "A2"]), Route(["A1", "A2"])]
        move.public_company = self.company
        oround = OperatingRound()
        self.assertFalse(oround.run(move, self.state, board=self.board))


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

    def test_round_increment_restart(self):
        oround = OperatingRound()
        state = {
            "public_companies": [],
            "playerTurn": PlayerTurnStub(False),
            "currentOperatingRound": 1,
            "totalOperatingRounds": 3,
        }
        nxt = oround.next(**state)
        self.assertEqual(nxt, "OperatingRound2")
        self.assertEqual(state["playerTurn"].restart_called_with, 2)


class TrainsRustedFlowTests(unittest.TestCase):
    def setUp(self):
        self.state = MutableGameState()
        self.state.players = [fake_player("A"), fake_player("B")]
        self.company_a = fake_company("A")
        self.company_b = fake_company("B")
        self.company_b.trains.append(Train("2", 80))
        self.company_b.president = self.state.players[1]
        self.state.public_companies = [self.company_a, self.company_b]

    def test_rusted_train_purchase_and_return(self):
        move = OperatingRoundMove()
        move.player_id = "A"
        move.buy_train = True
        train = Train("3", 200, rusts_on="2")
        move.train = train
        move.public_company = self.company_a
        move.available_trains = [train]
        oround = OperatingRound()
        oround.run(move, self.state)

        nxt = {
            "public_companies": self.state.public_companies,
            "playerTurn": PlayerTurnStub(False),
            "currentOperatingRound": 1,
            "totalOperatingRounds": 2,
        }
        self.assertEqual(oround.next(**nxt), "TrainsRusted")

        rust_move = RustedTrainMove()
        rust_move.player_id = self.company_b.president.id
        rust_move.public_company = self.company_b
        rust_move.train = Train("2", 100)
        tr = TrainsRusted()
        self.assertTrue(tr.run(rust_move, self.state))
        self.assertFalse(self.company_b.bankrupt)
        self.assertEqual(tr.next(currentOperatingRound=1), "OperatingRound1")

    def test_rusted_train_bankruptcy(self):
        self.company_b.cash = 0
        self.company_b.president = self.state.players[1]
        self.company_b.president.cash = 10

        rust_move = RustedTrainMove()
        rust_move.player_id = self.company_b.president.id
        rust_move.public_company = self.company_b
        rust_move.train = Train("2", 100)
        tr = TrainsRusted()
        self.assertTrue(tr.run(rust_move, self.state))
        self.assertTrue(self.company_b.bankrupt)
        self.assertEqual(tr.next(currentOperatingRound=1), "StockRound")


if __name__ == '__main__':
    unittest.main()
