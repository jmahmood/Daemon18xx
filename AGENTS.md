# AGENT Instructions for Daemon18xx

This repository aims to implement a stateless 18xx engine in Python that can power online games of 1830, 1846 and 1889. The engine should be usable as a library; persistence and networking layers will be handled separately.

## Guidelines

- Keep the engine **stateless**. Functions should accept a game state and a move, returning the updated state without side effects.
- Avoid file, database, or network operations in the core code. Any saving or player notification logic belongs outside this repo.
- Implement missing rules starting with the operating round of 1830. Structure the code so variants (1846, 1889) can swap in their own configurations.
- Expand documentation (README files) when you add or change functionality.
- Add or update unit tests under `app/unittests/` to cover new behaviors.

## Pull Requests

- Summarize code changes and reference impacted files.
- Include the results of running unit tests. If tests cannot run because dependencies are missing or the environment lacks network access, note this in the PR description.
- Ensure the working tree is clean (`git status`) before opening a PR.


# 18xx Library Development — **AGENT Guide**

*This file tells the assistant **how to think and respond** while it helps build a reusable rules engine for **1830** and other 18xx titles.*  
The rules summarised below are derived from the official **1830 Rules of Play**

---

## 1 · Mission & Success Criteria

1. **Primary goal:** deliver a tested, deterministic rules engine that exactly reproduces 1830 gameplay and can be parameterised for other 18xx variants.
2. **A pull‑request is “done” when:**

   * All unit & property‑based tests pass.
   * Game states are serialisable & reproducible from an action log.
   * Benchmarks remain within 10 % of the previous tag.
3. **Secondary goals:** clean API design, clear documentation, straightforward AI‑bot hooks, and minimal third‑party dependencies.

---

## 2 · Core Concepts the AI Must Internalise

| Domain object      | Canonical source | Key responsibilities                                                     |
| ------------------ |------------------| ------------------------------------------------------------------------ |
| **GameState**      | §3, §§16‑22      | Immutable snapshot containing bank, map, corps, players, round data.     |
| **Round**          | §§4‑5, §22       | Discrete phase — *Stock* or *Operating* — with its own valid action set. |
| **Corporation**    | §§8‑15           | Capital, share register, trains, tokens, president PID.                  |
| **Tile**           | §18, Tables 6‑7  | Hex orientation, upgrade path, revenue, token slots.                     |
| **Train**          | §20‑22, Table 4  | Length, phase triggers, rusting schedule.                                |
| **PrivateCompany** | §6‑7, §23        | Owner, revenue, special ability, close conditions.                       |
| **Action**         | ‑‑ (engine)      | Command issued by an agent. Must validate *pre‑state ⇒ post‑state*.      |

> *Every reply the assistant writes should map naturally onto one or more of the above objects.*

---

## 3 · Engine Architecture

1. **Language choice**

   * **Core engine:** *Rust* for deterministic speed; compile to WASM bindings for Python & TypeScript callers.
   * **Support tooling / CLI:** Python (rich, typer) for faster iteration.
2. **Functional core, imperative shell**

   * Pure functions `(state, action) -> Result<state'>` live in `crate::rules`.
   * IO, CLI, bots live in `bin/` or separate packages.
3. **Event sourcing & snapshotting**

   * Persist the canonical log `(timestamp, pid, action_json)`.
   * Derive state by folding the log; snapshot every N events for performance.
4. **Configuration‑over‑code**

   * `assets/games/1830.yaml`, `1846.yaml`, etc. describe trains, tiles, par prices, map hexes, certificate limits.
5. **Validation layers**

   * Compile‑time: Rust type system.
   * Run‑time: `validate(state, action)` returns exhaustive enum of error types so callers can surface precise UX hints.

---

## 4 · AI Interaction Protocol

| When user says… | Assistant must…                                                                          |
| --------------- | ---------------------------------------------------------------------------------------- |
| “Design…”       | Produce high‑level diagrams (ASCII or Mermaid) before code.                              |
| “Implement…”    | Output fully‑compilable diff blocks ➜ Rust, plus test stubs.                             |
| “Refactor…”     | Show before/after excerpts; justify in bullets referencing perf, clarity, rule accuracy. |
| “Explain rule…” | Quote rule section & walk through a concrete example linked to state objects.            |
| Unclear request | Ask 1–2 concise clarifying questions — **never** proceed on guesswork.                   |

### Output formatting

* Use Markdown.
* Prefer *fenced* \`\`\`rust blocks with explicit module paths.
* Number TODO lists so they can be referenced in follow‑ups.

---
## 5 · Rule Enforcement Summary (1830)

* **Certificate limits**: Table 3.
* **Par prices**: \$67–\$100; 5 certs to float; treasury = 10× par.
* **Round order**: 1×OR → 2×OR after first 3‑train stock round → 3×OR after first 5‑train stock round.
* **Train limits**: 4/3/2 per phase; rust steps on first 4/6/D.
* **Privates**: buy‑in window opens with first 3; auto‑close on first 5; special powers Table 1.
* **Bankruptcy & bank‑break**: §24–25.

*(Full rule text lives in `docs/rules1830.rtf` — the AI must cite section numbers when reasoning.)*


---

## 9 · Anti‑Goals

* GUI client (out of scope for core library).
* Networked multiplayer (but engine must be deterministic enough for later addition).
* AI strategy bots — design hooks only.

---

## 10 · Questions the Assistant Should Ask by Default

1. Which milestone are we targeting now?
2. Preferred CI platform?
3. Licence (MIT/Apache‑2.0/BSD‑3)?
4. Target Rust edition (2021/2024)?

---

*End of AGENT guide.*
