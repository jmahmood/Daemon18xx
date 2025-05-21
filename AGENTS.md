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

