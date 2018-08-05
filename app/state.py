from typing import List

from app.base import Player, Move, PrivateCompany
from app.minigames.base import Minigame
from app.minigames.private_companies import BiddingForPrivateCompany, BuyPrivateCompany
from app.minigames.stock_round import StockRound

def BidOnPrivateCompany(players: List[Player], company: PrivateCompany):
    """The player giving up the company for a bid lets the next x players make a bid for as long as
    necessary for him to approve it."""
    starting_player = company.belongs_to.order
    player_order_doubled = players.append(players)
    return PlayerOrder(player_order_doubled[starting_player + 1:starting_player + len(players)])


def PrivateCompanyBidPlayerOrder(company: PrivateCompany):
    players = [pb.player for pb in company.player_bids]
    return PlayerOrder(players)


def PlayerOrder(players: List[Player]):
    while True:
        for p in players:
            yield p


class Game:
    """Holds state for the full ongoing game"""
    @staticmethod
    def initialize(players: List[Player], saved_game: dict = None) -> "Game":
        """

        :param players:
        :param saved_game: Used to load data, if any.  If empty, everything defaults to a new game.
        :return:
        """
        game = Game()
        game.players = players
        game.private_companies = PrivateCompany.allPrivateCompanies()
        return game

    def isOngoing(self) -> bool:
        return True

    def isValidMove(self, move: Move) -> bool:
        """Determines whether or not the type of move submitted is of the type that is supposed to run this round.
        IE: You normally can't sell stock during an Operating Round"""
        pass

    def isValidPlayer(self, player: Player) -> bool:
        """The person who submitted the move must be the current player.
        This is more difficult than it seems, especially if we want to try to avoid holding unnecessary state.
        -> Player order is fixed until phases end
        -> Player order changes between different stock rounds
        -> There can be temporary player orders
            -> Private Company bid-offs
            -> Requesting bids for one's private company (This is quite complicated if we want to do it correctly)
                -> You make the request, everyone can submit a bid until you either accept one or cancel and do something else.
                -> IE: Everyone can make a "Move" (submit a bid) or you can revert the state
        -> Company operating rounds have different
        """
        pass

    def getState(self) -> dict:
        return {}

    def getMinigamePlayerOrder(self):
        """
        You can either replace the current player order,
        or temporarily replace this until the generator comes to an end.

        def player_order_fn(players, initial_player):
            def inner_fn():
                i = 0
                while players.length > 0 and is valid:
                    player_position = i % len(players)
                    yield players[i]
                    should_continue = yield

                    if should_continue is of type player:
                        players.remove(should_continue)

                    if should_continue is of type boolean and not should_continue:
                        is_valid = False
                        break

                    i+=1

            return inner_fn

        def bidding_on_private_company
            blah blah
            if is a pass:
                current_player.send(current_player) # Current player should no longer come up.


        def transitioning_to_stock_round
            ...
            current_player.send(False) # You need to stop this player order and start a brand new one
            ...

        def selling_a_private_company
            ...
            current_player.send("Stack") # You need to pause this? And start a new function?





        x = player_order_fn()




        while Game Is Not Finished
        :
            For player in player_order_fn:
                current_player = player
                await_command

                if temporary_player_order_required:
                    for player in temporary_player_order_fn:
                        ...

                elif transition:
                    player_order_fn = new player_order_fn
                    break

        :return:
        """
        """
        functions = {
            "BuyPrivateCompany": (buy_company_player_order_fn(initial_player=), overwrites_previous_player_order=True)
            "BiddingForPrivateCompany": (bid_for_private_company(initial_player=""), stack_player_order=True),
            "StockRound": play_stock_round(initial_player=...), overwrites_previous_player_order=True
            "StockRoundSellPrivateCompany": bid_for_private_company(initial_player=""), stack_player_order=True, #TODO
            "OperatingRound": run_companies(company_order=[]), overwrites_previous_player_order=True  # TODO
        }
        """
    def getMinigame(self) -> Minigame:
        """Creates a NEW INSTANCE of a mini game and passes it"""
        classes = {
            "BiddingForPrivateCompany": BiddingForPrivateCompany,
            "BuyPrivateCompany": BuyPrivateCompany,
            "StockRound": StockRound,
            "StockRoundSellPrivateCompany": None, #TODO
            "OperatingRound": None  # TODO
        }

        cls: type(Minigame) = classes.get(self.minigame_class)
        return cls()

    def performedMove(self, move: Move) -> bool:
        """
        Performs a move and mutate the Minigame / Player Order states
        :param move:
        :return:
        """
        minigame = self.getMinigame()
        success = minigame.run(move, **self.getState())

        self.setMinigame(minigame.next()) if success else self.setError(minigame.errors())

        return success

    def setError(self, error_list: List[str]) -> None:
        """A Minigame is a specific game state that evaluates more complex game rules.
        Bidding during private bidding, etc..."""
        pass

    def setMinigame(self, minigame_class: str) -> None:
        """A Minigame is a specific game state that evaluates more complex game rules.
        Bidding during private bidding, etc..."""
        self.minigame_class = minigame_class

    def saveState(self) -> None:
        """This saves the current state to a data store.  Pickle or SQL?
        This is not necessary if you will run all the logic on the running process without quitting"""
        pass

    def notifyPlayers(self) -> None:
        """Sends a message to all players indicating that the state has been updated.
        Also sends error messages if any.

        This is not necessary if we are testing the application, and can be overridden where necessary"""
        pass
