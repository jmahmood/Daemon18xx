import unittest
from app.minigames.base import Minigame
from app.base import Move, MutableGameState, err

class DummyMinigame(Minigame):
    def run(self, move: Move, state: MutableGameState) -> bool:
        return self.validate([err(False, "dummy error")])

    def next(self, state: MutableGameState) -> str:
        return ""

class MinigameErrorIsolationTests(unittest.TestCase):
    def test_errors_do_not_persist_across_instances(self):
        state = MutableGameState()
        m1 = DummyMinigame()
        m1.run(Move(), state)
        self.assertEqual(m1.errors(), ["dummy error"])

        m2 = DummyMinigame()
        m2.run(Move(), state)
        self.assertEqual(m2.errors(), ["dummy error"])
        # ensure first instance errors remain unchanged
        self.assertEqual(m1.errors(), ["dummy error"])

    def test_validate_clears_previous_errors(self):
        state = MutableGameState()
        m = DummyMinigame()
        m.run(Move(), state)
        self.assertEqual(m.errors(), ["dummy error"])

        # Subsequent validation with no errors should clear previous ones
        m.validate([err(True, "")])
        self.assertEqual(m.errors(), [])

if __name__ == '__main__':
    unittest.main()

