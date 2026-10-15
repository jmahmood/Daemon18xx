# Working on Daemon18xx

Daemon18xx is a backend-only project for standard 1830 and full Shikoku 1889.
Frontends live in separate projects. Read README.md and docs/frontend_integration.md
before changing the public interface. Do not add frontend assets, Node tooling,
Socket.IO gameplay, or another competing quickstart/API guide.

- Keep app/engine1830 and app/engine1889 stateless and standard-library-only:
  input state plus action produces a new independent JSON-compatible state.
  File, database, authentication and network operations belong in backend/.
- Core syntax remains compatible with Python 3.8; the documented server runtime
  is Python 3.12. Do not promise 1846 or optional beginner rules.
- Consult docs/rules1830.rtf or docs/rules1889.pdf for the matching rules. Preserve
  attribution and recorded fixtures. See variant RULE_COVERAGE.md files for
  edition decisions and validation limits.
- Add meaningful regression tests under app/unittests/. Install requirements.txt
  and run python -m unittest discover -q. Report skips or unrun checks accurately.
- Keep the README concise. Document external-client behavior in the integration
  guide and action examples alongside interface changes. If the edge inventory
  changes, run python tools/render_edge_cases.py and its --check mode.
- Preserve unrelated user changes. Do not commit or push without authorization.
