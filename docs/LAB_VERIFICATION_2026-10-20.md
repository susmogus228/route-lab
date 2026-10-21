# Resilience Lab verification

## Delivered behavior

Six explained synthetic scenarios extend the original four. The Lab and API provide congestion sensitivity and exhaustive independent single-cell closures on maps up to 256 total cells. The existing editor, CLI, Dijkstra/A* algorithms and recorded benchmark remain available. A bridge shortcut opens one specified crossing and measures the resulting map; editor changes use the same analysis.

## Evidence

- Python suite: **115 passed**, including the original 58, 47 new analysis/scenario tests, six new real HTTP tests and four historical-source verification tests.
- [Lab browser suite](lab-browser-verification.json): **51 assertions passed**, including cost4/6 versus reference7, pointer/keyboard input, delayed responses, unreachable maps, the bridge repair, custom editor maps, export, validation errors and both API operations.
- [Editor regression](editor-browser-verification.json): **68 assertions passed**, including all five navigation tabs, cost26 baseline, map geometry, imports, trace and the existing API explorer.
- Four browser sizes: 319x672, 375x812, 768x1024, 1280x800. The default Lab map fits the first screen at each size, with square cells and no horizontal page overflow.
- Actual in-app screenshot: [319px pane](images/lab-in-app-319.png). Desktop captures show [threshold](images/lab-threshold-desktop.png), [closures](images/lab-closures-desktop.png) and [repair](images/lab-repair-desktop.png).
- The browser downloaded analysis JSON. Parsing the actual file confirmed the repaired map has grid[2][5]=1 and critical_count=0.

TDD first confirmed missing Lab navigation, analysis HTTP404 responses and absent contract fields. Backend checks initially failed on missing analysis imports. The bridge repair race reproduced before the fix; repair now waits for its measured baseline. The tests include separate Bellman-Ford and flood-fill oracles, input immutability, equal-cost alternatives, start=goal, unknown fields and bounded work. The seeded threshold oracle covers 20 maps at nine levels, and the closure oracle covers 25 maps.

## Independent review

The selected implementation-reviewer could not start because its configured model is unsupported for this account. That attempt supplied no verdict. The fallback **Code Reviewer returned PASS** after inspecting formulas, API/OpenAPI parity, bounds and asynchronous state. It independently ran 59 relevant tests successfully. Root fixed the loading-state and early-repair findings before completion. The backend worker owned analysis/service/scenario tests; root owned HTTP, UI and integration.

## Reproduce

```sh
python -m pytest tests -q
python scripts/verify_results.py
python -m route_lab demo --results results --port 8767
# Separate shell, with optional Playwright development tools installed:
node tests/browser-ui.cjs
node tests/browser-lab.cjs
python -m build
```

## Limits

These are synthetic static entry costs, not minutes, live congestion or geographic road rules. Closure analysis tests one failed cell at a time and excludes endpoints. Zero disconnecting individual closures does not establish safety under combined failures. Work is local; no public deployment, GitHub publication, physical touch-device test or complete screen-reader audit was performed. The service remains loopback-only with four bounded concurrent requests.

Package, benchmark-source preservation and source-archive checks appear in the dated output folder's verification.json. Historical screenshots and reports describe their own earlier snapshots.

## Historical benchmark provenance

The supplied benchmark recorded hashes for four Python modules, including service.py. The Lab extends that service module. The four exact recorded source files were recovered from the preserved pre-Lab archive and verified against the original benchmark hashes in results/source-snapshot. The original benchmark JSON, CSV, chart and scenario bytes were preserved.

The verifier now reports `recorded_source_verified: true`, `current_source_matches: false` and `changed_files: ["service.py"]`. It rejects drift without a matching historical snapshot and rejects a corrupted snapshot even when the current source matches. The current core.py and benchmark.py still match the historical run. The old timings describe the recorded version; they are not fresh measurements of Lab analysis operations.
