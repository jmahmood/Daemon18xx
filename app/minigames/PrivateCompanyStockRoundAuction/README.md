Private Company Auction During Stock Round
------------------------------------------

Players may offer one of their private companies for sale instead of buying a
share.  Each other player, in turn order, may bid or pass on the company.
When all have responded, the owner chooses whether to accept the highest bid.
If no bid is accepted the company remains with its original owner.  This
procedure follows rule `7.1`.

Technical Explanation
---------------------

The `PrivateCompanyStockRoundAuction` minigame has two phases.  `Auction`
collects bids from the other players and stores them on the game state.  Once
everyone has acted, `AuctionDecision` lets the selling player accept a bid or
reject them all.  Cash is exchanged and the private's ownership updated if a
bid is accepted.

Auction
-------

Handles the bidding step.  Bids must be between half and twice the printed
value of the company.  A player may also pass.  When all opponents have either
bid or passed the minigame proceeds to `AuctionDecision`.

AuctionDecision
---------------

The owner reviews the offers and either accepts one or rejects them all.  If a
bid is accepted the funds transfer immediately and play returns to the stock
round.

Transition to Stock Round
-------------------------

After `AuctionDecision` resolves, control returns to `StockRound` so the next
player may act.
