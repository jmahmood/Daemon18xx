import logging
from typing import List, Union

from app.base import err, Player, Move, PrivateCompany, PublicCompany
from app.minigames.OperatingRound.minigame_operatinground import OperatingRound
from app.minigames.OperatingRound.turnorder import CorporateTurnOrder
from app.minigames.PrivateCompanyInitialAuction.minigame_auction import BiddingForPrivateCompany
from app.minigames.PrivateCompanyInitialAuction.minigame_buy import BuyPrivateCompany
from app.minigames.PrivateCompanyInitialAuction.turnorder import PrivateCompanyInitialAuctionTurnOrder
from app.minigames.PrivateCompanyStockRoundAuction.minigame_auction import StockRoundSellPrivateCompany
from app.minigames.PrivateCompanyStockRoundAuction.minigame_decision import StockRoundSellPrivateCompanyDecision
from app.minigames.StockRound.minigame_stockround import StockRound
from app.minigames.StockRound.turnorder import StockRoundTurnOrder, StockRoundSellPrivateCompanyTurnOrder, \
    StockRoundPrivateCompanyDecisionTurnOrder
from app.minigames.base import Minigame, MinigameFlow
from app.state import MutableGameState
from app.turnorder import PlayerTurnOrder


class Game:
    """Primary purpose is to hold the player order and the minigame being played"""
    @staticmethod
    def start(players: List[str]) -> "Game":
        total_players = len(players)
        cash = int(2400 / total_players)
        player_objects = []
        for order, player_name in enumerate(players):
            player_objects.append(
                Player.create(player_name, cash, order)
            )
        game = Game.initialize(player_objects)
        game.setMinigame(MinigameFlow("BuyPrivateCompany", False))
        return game

    @staticmethod
    def initialize(players: List[Player], saved_game: dict = None) -> "Game":
        """

        :param players:
        :param saved_game: Used to load data, if any.  If empty, everything defaults to a new game.
        :return:
        """
        game = Game()
        game.state = MutableGameState()
        game.state.players = players
        game.state.private_companies = PrivateCompany.allPrivateCompanies()
        game.state.public_companies = PublicCompany.allPublicCompanies()

        return game

    def __init__(self):
        self.state: "MutableGameState" = None
        self.current_player: Union[Player, PublicCompany] = None
        self.player_order_generators = []
        self.errors_list = []

    def isOngoing(self) -> bool:
        """Is the game still ongoing or has it ended?"""
        return True

    def isValidMove(self, move: Move) -> bool:
        """Determines whether or not the type of move submitted is of the type that is supposed to run this round.
        IE: You normally can't sell stock during an Operating Round"""
        minigame_move_classes = {
            "BuyPrivateCompany": "BuyPrivateCompanyMove",
            "BiddingForPrivateCompany":  "BuyPrivateCompanyMove",
            "StockRound": "StockRoundMove",
            "StockRoundSellPrivateCompany": "AuctionBidMove",
            "StockRoundSellPrivateCompanyDecision": "AuctionDecisionMove",
        }
        return minigame_move_classes.get(self.minigame_class) == move.__class__.__name__

    def isValidPlayer(self, move: Move) -> bool:
        """The person who submitted the move must be the current player.

        Warning: The player object is only set in the move once the "Backfill" function is executed (to load info from state)
        To avoid that, we are only comparing the player ids, which are always present in moves."""
        errors = err(
            move.player_id == self.current_player.id or move.company_id == self.current_player.id,
            "Wrong player; {} is not {}",
            move.player_id, self.current_player.id
        )
        if errors == None:
            return True
        self.errors_list = [errors]
        return False

    def getState(self) -> MutableGameState:
        return self.state

    def setPlayerOrder(self):
        """Initializes a function that inherits from PlayerTurnOrder"""
        # TODO: What happens if we have something (like an operating round) where there are no player turns?

        player_order_generator_from_minigame = {
            "BuyPrivateCompany": PlayerTurnOrder,
            "BiddingForPrivateCompany": PrivateCompanyInitialAuctionTurnOrder,
            "StockRound": StockRoundTurnOrder,
            "StockRoundSellPrivateCompany": StockRoundSellPrivateCompanyTurnOrder,
            "StockRoundSellPrivateCompanyDecision": StockRoundPrivateCompanyDecisionTurnOrder,
            "OperatingRound": CorporateTurnOrder
        }

        try:
            player_order_generator = player_order_generator_from_minigame.get(self.minigame_class)(self.getState())
        except TypeError:
            raise TypeError("Cannot find turn generator for {}".format(self.minigame_class))

        if player_order_generator.stacking_type:
            self.player_order_generators.append(player_order_generator)

        if player_order_generator.replacement_type:
            self.player_order_generators.pop()
            self.player_order_generators.append(player_order_generator)

        if player_order_generator.overwrite_type:
            # An overwrite type function usually clears the full stack of player order functions.
            # The only case in which we don't is if we are "resuming" a player stack.
            try:
                self.player_order_generators.pop()
            except IndexError:
                logging.warning("No old player order function available")

            if len(self.player_order_generators) > 0 and \
                            self.getPlayerOrderClass().__class__.__name__ == player_order_generator.__class__.__name__:
                logging.warning("keeping old player order generator")
            else:
                self.player_order_generators = [player_order_generator]

    def getPlayerOrderClass(self) -> PlayerTurnOrder:
        return self.player_order_generators[len(self.player_order_generators) - 1]

    def setCurrentPlayer(self):
        """
        Sets the player by incrementing the newest player_order_fn
        """
        self.current_player = next(self.getPlayerOrderClass())

    def getMinigame(self) -> Minigame:
        """Creates a NEW INSTANCE of a mini game and passes it"""
        classes = {
            "BiddingForPrivateCompany": BiddingForPrivateCompany,
            "BuyPrivateCompany": BuyPrivateCompany,
            "StockRound": StockRound,
            "StockRoundSellPrivateCompany": StockRoundSellPrivateCompany, #TODO
            "StockRoundSellPrivateCompanyDecision": StockRoundSellPrivateCompanyDecision,
            "OperatingRound": OperatingRound,  # TODO
        }

        cls: type(Minigame) = classes[self.minigame_class]
        return cls()

    def performedMove(self, move: Move) -> bool:
        """
        Performs a move and mutate the Minigame / Player Order states
        :param move:
        :return:
        """
        self.errors_list = [] # game errors only last from when a move is made until a new move is performed.

        minigame = self.getMinigame()
        minigame.onTurnStart(self.getState())
        success = minigame.run(move, self.getState())

        if success:
            next_minigame = minigame.next(self.getState())

            if self.minigame_class != next_minigame.minigame_class or next_minigame.force_player_reorder:
                """When the minigame changes, you need to switch the player order usually."""
                minigame.onComplete(self.getState())
                self.setMinigame(next_minigame)
                self.setPlayerOrder()
                self.getMinigame().onStart(self.getState())
            else:
                minigame.onTurnComplete(self.getState())

            if next_minigame.do_not_increment_player:
                logging.warning("Do not increment the player for whatever reason.")
                pass
            else:
                self.setCurrentPlayer()

        else:
            self.setError(minigame.errors())

        return success

    def setError(self, error_list: List[str]) -> None:
        self.errors_list = error_list

    def errors(self):
        return self.errors_list

    def setMinigame(self, next_minigame: MinigameFlow) -> None:
        """A Minigame is a specific game state that evaluates more complex game rules.
        Bidding during private bidding, etc..."""
        self.minigame_class = next_minigame.minigame_class

    def saveState(self) -> None:
        # TODO: Saves State
        """This saves the current state to a data store.  Pickle or SQL?
        This is not necessary if you will run all the logic on the running process without quitting"""
        pass

    def notifyPlayers(self) -> None:
        # TODO: Used for external communication to a front-end module.
        """Sends a message to all players indicating that the state has been updated.
        Also sends error messages if any.

        This is not necessary if we are testing the application, and can be overridden where necessary"""
        pass
