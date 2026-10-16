# Working on Daemon18xx

Daemon18xx is a backend-only project for standard 1830 and full Shikoku 1889.
Frontends live in separate projects. Read README.md and docs/frontend_integration.md
before changing the public interface. Do not add frontend assets, Node tooling,
Socket.IO gameplay, or another competing quickstart/API guide.
The original implementation, including its original frontend, is preserved in
old/ by the owner's explicit instruction. Keep it there without deleting it;
see old/AGENTS.md for archive handling. Its tests in old/tests/ are deprecated
historical records, excluded from the current test workflow.

## Collaboration and decision boundaries

The existing implementation and tests represent the owner's work and intent.
Exploratory choices, including mutable state objects, may be deliberate steps
toward a final design. Incompleteness is work to finish, not authorization to
discard the implementation. Preserve existing behavior and regression evidence
while improving the system.

The owner has accepted the current direction of stateless Python rules engines
using independent JSON-compatible state snapshots, with HTTP and persistence
outside the core. That acceptance does not authorize deleting the original
implementation or making further major architectural changes without discussion.

- Proceed with routine fixes, tests and local implementation choices within the
  agreed scope. Do not ask for approval again when that specific action is
  already authorized in the conversation.
- Before a substantial rewrite, a parallel implementation, a public API/state
  format change that breaks compatibility, a new runtime engine/service, or
  removal of existing modules, definitions, datasets, tests or documentation,
  explain the proposed change and obtain the owner's agreement. Prepare a
  concrete proposal: affected files/interfaces, reasons, alternatives, retained
  behavior, migration/rollback approach and validation plan. Do this before
  implementing the change; do not present a finished replacement as the first
  opportunity to discuss the decision.
- Instructions such as "finish the rules", "keep going", "simplify" or
  "remove unnecessary material" do not themselves authorize a replacement or
  establish that existing work is unnecessary. Identify proposed removals
  explicitly. Lack of references from a newly written replacement is not, by
  itself, evidence that the original code is disposable.
- Carry existing tests forward as regression evidence. Do not delete tests
  simply because an implementation has changed or to obtain a passing suite.
  Explain proposed retirement or replacement of tests and obtain agreement.
- Report material changes in direction promptly, before editing. Distinguish
  measured behavior, assumptions, validation limits and recommendations.

## Documentation, voice and attribution

- The README is for humans. Preserve the owner's personal introduction,
  motivation and voice. Add useful setup and integration information around it;
  do not replace it with generic product copy or invent opinions in the owner's
  first-person voice. Present substantial editorial rewrites as proposals.
- Existing tile definitions, game data and test cases from external projects
  may be reused when their licenses permit it. Identify the source and scope of
  reuse, retain required notices, and give visible credit in the root README
  with the project, authors, license and links. A notice elsewhere alone is not
  sufficient documentation of attribution. Distinguish imported data/fixtures
  from any reused executable engine, and surface uncertain permissions before
  incorporating the material.
- Keep detailed client/AI instructions in docs/frontend_integration.md. Keep
  source rulebooks, attribution and test/coverage evidence discoverable without
  turning the README into an implementation ledger.

## Implementation and validation

- Keep app/engine1830 and app/engine1889 stateless and standard-library-only:
  input state plus action produces a new independent JSON-compatible state.
  File, database, authentication and network operations belong in backend/.
- Core syntax remains compatible with Python 3.8; the documented server runtime
  is Python 3.12. Do not promise 1846 or optional beginner rules.
- Consult docs/rules1830.rtf or docs/rules1889.pdf for the matching rules. Preserve
  attribution and recorded fixtures. See variant RULE_COVERAGE.md files for
  edition decisions and validation limits.
- Add meaningful regression tests under app/unittests/. Install requirements-dev.txt
  and run python -m unittest discover -q. Report skips or unrun checks accurately.
- Keep the README concise. Document external-client behavior in the integration
  guide and action examples alongside interface changes. If the edge inventory
  changes, run python tools/render_edge_cases.py and its --check mode.
- Preserve unrelated user changes. Do not commit or push without authorization.
