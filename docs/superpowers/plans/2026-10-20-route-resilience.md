# Route resilience implementation plan

**Goal:** Deliver six explained scenarios, an exact congestion tipping point, and independent single-cell closure analysis in the editor, Lab, and reusable API.
**Architecture:** Preserve core.py and the standard-library Python service. Add a pure analysis module, two strict bounded API operations, and a separate native-JS Lab view using current CSS tokens. No new runtime dependency or external data transfer.
**Tech Stack:** Python 3.12+, HTML, CSS, JavaScript, existing pytest and Playwright.
**Spec:** User-approved six scenarios and threshold/closure proposal in the current chat.

## Constraints and ownership
- Project: D:/Projects/applied-ai-portfolio/route-lab. English product text; current graphite/blue system UI. Keep existing editor and benchmark.
- Backend Architect owns analysis.py, service.py, new analysis/scenario tests and six JSON examples. Root owns demo.py, static files, HTTP/browser tests, documentation and release.
- Both analyses accept at most 256 total cells. Solve/compare retain 128x128. No API key, geodata, live traffic, minutes, push, or deployment.
- Threshold: 1..9 simultaneous costs on explicit unique non-endpoint traversable cells; report first strictly suboptimal level of the level-1 reference path. Ties do not count as a switch.
- Closures: independently close each traversable non-endpoint cell; compare to the same baseline. Already unreachable maps do not gain newly critical cells. Export real calculation JSON.

## Memory and agents
Codex memory supplies continuity; fresh Codebase Memory has no RouteLab graph, so files are authoritative, no indexing. Independent backend work precedes integration. Root owns the shared UI/HTTP surfaces. A read-only implementation-reviewer checks semantics, validation, state freshness and limits after integration.

## Review focus
- Equal-cost alternatives must not create a false threshold.
- Stale responses must never overwrite a changed map or selected closure.
- Previously unreachable and singleton maps need meaningful empty states.
- Import/selection resets old sensitivity and closure results.
- Narrow panes retain readable controls, square cells and keyboard inspection.

## Tasks
- [x] Backend tests RED: switch2, ties, flood-fill closure oracle, immutable inputs, strict limits, all six fixtures. Implement analyses and pass tests.
- [x] HTTP tests RED: POST /api/threshold returns switch2, POST /api/closures returns independent failures, lab.js serves, OpenAPI exposes request/response shapes. Wire and pass.
- [x] UI test RED: Lab view, Rush Hour selector, slider with measured cost4/6, closure heatmap, custom editor map, export and narrow viewport. Implement Lab and pass.
- [x] Preserve old browser regression, run complete Python tests, benchmark verifier and fresh wheel build. Inspect desktop and actual narrow pane.
- [x] Reviewer verdict, fix reproducible issues, save verification and screenshots, create dated source/wheel delivery. Leave local view open. No publication.
