Stock Round
-----------

The stock round is when players buy and sell certificates of the public
companies.  On your turn you may first sell any number of shares that the
rules allow and then optionally purchase a single certificate.  No sales are
permitted in the first stock round.

When you sell shares, the company's marker moves one space down on the stock
market for each 10% sold.  If all of a company's stock is in players' hands,
its price moves one space up.  These movements follow the stock market rules
in sections `10.0`–`16.0` of the rulebook.

### Priority Deal

Whoever is seated to the left of the last player to successfully buy a
certificate receives Priority Deal for the next stock round.  Players who pass
are skipped until the round ends, but Priority Deal keeps the order for the
following stock round.

Technical Explanation
---------------------

The `StockRound` minigame processes `StockRoundMove` objects.  It validates
purchases, sales and passes, updates company presidents and tracks how many
shares have changed hands in the current round.

BuyPrivateCompany
-----------------

A player may choose to auction one of their private companies instead of
buying a share.  This invokes the `PrivateCompanyStockRoundAuction`
minigame.  The auction process is described in rule `7.1`.

Transition to Operating Round
-----------------------------

Once every player consecutively passes, the game moves to the next operating
round.
