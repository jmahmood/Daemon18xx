from typing import List

from app.base import PublicCompany
from app.state import MutableGameState
from app.turnorder import NonRepeatingPlayerTurnOrder


class CorporateTurnOrder(NonRepeatingPlayerTurnOrder):
    def __init__(self, state: MutableGameState):
        super().__init__(state)
        # TODO: You should be ordering the companies by stock price, and the order at which they reached that stock
        # price.
        # TODO: What happens if no public companies have gone public?  It seems to result in an indexerror
        self.companies: List[PublicCompany] = [company for company in state.public_companies if company.isFloated()]
        self.players = [pc.president for pc in self.companies]

    def __next__(self) -> PublicCompany:
        super().__next__()
        return self.companies[self.iteration - 1]

    def removeCompany(self, company: PublicCompany):
        raise Exception("You should never actually have to remove a company from the player order during the"
                        "Operating Round.  The code / logic needs to be cleared up if you want to do this.")
