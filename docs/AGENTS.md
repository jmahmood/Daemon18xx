# AGENT Guidelines for Implementing 1830 Rules

This directory contains the original 1830 rulebook (`rules1830.rtf`).
When adding game logic or tests, consult the rulebook so behaviour matches
the official rules.

## Core Sequence
1. **Private Company Auction** – See rule `7.1`.
2. **Stock Round** – Players may buy one certificate and optionally sell
   permitted shares (no sales in the first Stock Round).
3. **Operating Round** – Private companies pay revenue first, then each
   railroad may construct track, optionally place a station token, run trains
   and buy trains. Follow tile colour progression and token placement rules.

## Key Rules to Observe
- **Track Construction** (`18.0`): only one tile per OR, observing colour
  order (yellow → green → brown → red) and connectivity requirements.
- **Tokens** (`19.0`): one token may be placed per OR, costs escalate and a
  route must include at least one of the company's tokens.
- **Running Trains** (`20.0`): routes must be legal and each requires an
  available train. Train purchases may rust older trains (`22.0`).
- **Stock Market** (`10.0`–`16.0`): tokens move down when shares are sold into
  the bank pool and up when all shares are player-owned. No stock sales are
  allowed in the first Stock Round.

## Implementation Notes
- Use the variant configuration modules in `app/config` to define starting
  cash, token counts and train rosters.
- Keep the engine stateless as directed in the repository root `AGENTS.md`.
- Expand README files when implementing new sections of the rules.
- Cover new behaviour with tests under `app/unittests/`.
