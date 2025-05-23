Private Company Sale to Another Player
-------------------------------------

Rule `4.1` of the 1830 rulebook states that a player may sell one of their
private companies to another player during either participant's stock-round
turn for any mutually agreed price. Such sales are not permitted in the first
stock round. Selling a private company into a corporation occurs during an
operating round after a 3-train is purchased and is outside the scope of this
minigame.

This implementation handles the player-to-player transaction as a short auction.
The seller offers a company and each opponent may bid or pass. Once everyone has
responded the seller can accept one bid or reject them all. Bids may be for any
amount; this follows rule `4.1` allowing the two players to agree on any price.

Technical Explanation
---------------------

The `StockRoundSellPrivateCompany` minigame has two phases. `Auction` collects
bids from the other players and stores them on the game state. When all have
acted, `AuctionDecision` lets the selling player accept one bid or reject them
all. Cash is exchanged and ownership updated if a bid is accepted.

Auction
-------

Handles the bidding step. Each opponent may either bid any non-negative amount
or pass. When all have acted the minigame proceeds to `AuctionDecision`.

AuctionDecision
---------------

The owner reviews the offers and either accepts one or rejects them all. If a
bid is accepted the funds transfer immediately and play returns to the stock
round.

Transition to Stock Round
-------------------------

After `AuctionDecision` resolves, control returns to `StockRound` so the next
player may act.
