# Contributing

Run `python -m pip install -e ".[dev]"` and `python -m pytest -q` before proposing a change. Keep the runtime standard-library only unless a new dependency has a concrete need.

State the input scenario, expected cost, observed result, and reproduction command in a bug report. Attach small synthetic JSON maps rather than private campus plans. For a correctness change, include an independent oracle check and a failing regression case. Avoid asserting an exact route when several minimum-cost paths exist.

Changing entry-cost semantics, movement rules, tie breaking, or heuristic construction changes the algorithm contract. Update docs, tests, source provenance, and benchmark artifacts together. Record raw timing repetitions; do not replace unfavorable measurements with selected runs.

For UI changes, check keyboard access, current-result invalidation after editing, unreachable/loading/error states, touch input, and overflow at a narrow viewport. Keep API examples synchronized with actual server responses. Never include credentials or machine-specific absolute paths in release files.

Run `python -m build` and test the resulting wheel in a fresh environment before release. Preserve source attribution and the MIT license. The repository does not have a published maintainer contact or hosted support service yet; do not invent either in reports or templates.
