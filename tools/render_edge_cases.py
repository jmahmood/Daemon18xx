"""Render the reviewed engine edge-case inventory using only the stdlib.

Run from any directory: python tools/render_edge_cases.py [--check].
Edit docs/ENGINE_EDGE_CASES.json, then regenerate its readable Markdown view.
"""

import argparse
import ast
import json
from collections import Counter
from pathlib import Path


def render(root, inventory):
    cases = inventory["cases"]
    levels = Counter(case["level"] for case in cases)
    lines = [
        "# 1830 and 1889 edge-case inventory",
        "",
        inventory["scope"],
        "",
        inventory["interpretation"],
        "",
        "**%d cases: %d unit cases and %d HTTP/replay integration cases.**"
        % (len(cases), levels["unit"], levels["integration"]),
        "Every applicable variant has named automated coverage. A dash means a",
        "variant-specific rule; the JSON records why it does not apply.",
        "",
        "The machine-readable source is [ENGINE_EDGE_CASES.json](ENGINE_EDGE_CASES.json).",
        "`test_EngineEdgeCaseInventory.py` checks every reference resolves to a",
        "discoverable test and this document stays current. Test existence is",
        "checked automatically; mapping an assertion to a rule remains a review task.",
        "",
        "Reproduce validation with `python -m unittest discover -q`. Regenerate this",
        "document with `python tools/render_edge_cases.py`; use `--check` for a",
        "read-only consistency check.",
        "",
        "## Fixes and gaps addressed in this review",
        "",
        "- 1830 uses the lowest standing bidder; uploaded 1889 §5.7 uses clockwise",
        "  order after the highest bidder. Shared tests explicitly distinguish them.",
        "- 1889 emergency sales track one block per corporation per operating turn.",
        "  Funding estimates and bankruptcy liquidation use the same restriction.",
        "- Added focused tests for the previously missing auction, emergency, stock,",
        "  route, station, construction, private-power, lifecycle and restore boundaries.",
        "- Shared boundary tests run against both independent Python engines; small",
        "  synthetic rail networks isolate topology rules from full-board recordings.",
        "- The [26-item follow-up backlog](ENGINE_EDGE_CASE_BACKLOG.md) is resolved:",
        "  strict restore ledgers, emergency depot commitment, canonical liquidation,",
        "  private timing, exact route oracles and independent-process persistence.",
        "- Older 1889 saves missing emergency-sale blocks recover them by replaying",
        "  complete accepted history and verifying the entire reconstructed state.",
        "  Incomplete or inconsistent histories are rejected without changing the save.",
        "- Action-discovery train lists are independent of the source state and",
        "  other responses, including during multiple forced discards.",
        "- ROUTE-02 now tests seven stops versus a 6-train; MARKET-04 performs",
        "  actual sales and payout/withhold/zero-revenue decisions before checking par.",
        "- New scenarios cover a cheaper returned emergency train, simultaneous",
        "  discards with midway restoration, and owned 5/6 Diesel trade-ins at the limit.",
        "- The iterative audit adds exact certificate limits for all player counts,",
        "  same-owner ER interrupts, loss of MF power after sale, stale presidential",
        "  consent, strict saved-state metadata, and SQLite commit rollback/retry.",
        "- Complete authored 1889 games cover every supported player count; route",
        "  quotations, skipped route resolution and auction discovery have focused tests.",
        "  See [the rulebook audit](1889_RULEBOOK_AUDIT.md) for rules decisions.",
        "",
        "## Validation limits outside this unit checklist",
        "",
        "- 1889 has one valid independent complete recording, ending in phase 5.",
        "  A complete authored recording covers phases 6/D; an additional independent",
        "  bankruptcy and phase 6/D recording would provide stronger integration evidence.",
        "- Historical game 314 contains a blocked-city route and is a rejection",
        "  regression, not an exact-score acceptance game.",
        "- The uploaded [1889 rulebook](rules1889.pdf) is now the primary authority;",
        "  see [the clause audit](1889_RULEBOOK_AUDIT.md). Pinned G1889 revision",
        "  `46a592e40494368390c9a731978a577ac4ecb1e0` remains a secondary cross-check.",
        "- Browser/frontend integration is separate from these backend checks.",
        "- These tests cover listed rule boundaries, not every possible sequence,",
        "  a mathematically exhaustive proof or load testing. 1889 now provides an",
        "  exact optimal-route allocator separately from bounded route suggestions.",
        "",
    ]
    locations = {}

    def reference(test_id):
        module, cls, method = test_id.rsplit(".", 2)
        path = Path(*module.split(".")).with_suffix(".py")
        if module not in locations:
            tree = ast.parse((root / path).read_text())
            locations[module] = {
                (c.name, f.name): f.lineno
                for c in tree.body
                if isinstance(c, ast.ClassDef)
                for f in c.body
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
        line = locations[module][(cls, method)]
        return "[%s](../%s#L%d)" % (method, path.as_posix(), line)

    for area in dict.fromkeys(case["area"] for case in cases):
        lines.extend(
            [
                "## " + area.title(),
                "",
                "| ID | Boundary / expected behavior | 1830 test | 1889 test |",
                "|---|---|---|---|",
            ]
        )
        for case in cases:
            if case["area"] != area:
                continue
            cells = [case["id"], case["scenario"]]
            for variant in ("1830", "1889"):
                refs = case["tests"][variant]
                cells.append("<br>".join(reference(r) for r in refs) if refs else "—")
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads((root / "docs/ENGINE_EDGE_CASES.json").read_text())
    target = root / "docs/ENGINE_EDGE_CASES.md"
    expected = render(root, inventory)
    if args.check:
        if not target.exists() or target.read_text() != expected:
            parser.exit(1, "Regenerate docs/ENGINE_EDGE_CASES.md with this tool.\n")
        print("Edge-case document matches its inventory.")
    else:
        target.write_text(expected)
        print("Rendered %d edge cases." % len(inventory["cases"]))


if __name__ == "__main__":
    main()
