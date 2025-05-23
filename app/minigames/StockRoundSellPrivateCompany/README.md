Private Company Auction During Stock Round
------------------------------------------

A player may offer one of their private companies for sale instead of buying a share. Each
other player, in turn order, may bid or pass on the company. After everyone has responded,
the owner chooses whether to accept the highest bid or keep the company. This sequence
matches the procedure described in rule `7.1` of the 1830 rulebook.

Technical Explanation
---------------------

The `StockRoundSellPrivateCompany` minigame has two phases: `Auction` and
`AuctionDecision`. `Auction` records bids from the non‑owning players. Once bids or passes
have been collected from all of them, the game moves to `AuctionDecision`.

Auction
-------

During this step each opponent may either pass or submit a bid worth between half and twice
the printed value of the company. Bids and passes are stored on the game state so the seller
can review them later.

AuctionDecision
---------------

The selling player reviews the offers and either accepts one or rejects them all. Accepting a
bid transfers the private company and immediately adjusts both players' cash according to the
bid amount. Rejecting leaves ownership unchanged and no money changes hands.

Transition to Stock Round
-------------------------

After `AuctionDecision` completes – whether a bid was accepted or rejected – control returns to
`StockRound` so the next player may take their turn.
