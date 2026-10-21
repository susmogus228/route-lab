# Route resilience experiments

RouteLab models a rectangular synthetic grid with four-direction movement. Zero blocks movement; positive integers 1..9 are entry costs. Start contributes zero. The Lab accepts at most 256 total cells, including walls. The solver and editor retain their 128x128 limit.

## Congestion threshold

Choose 1..32 unique open cells excluding start and goal. The Python service sets all selected cells to each entry cost from 1 through 9 and solves each map. It recomputes the admissible heuristic after each change.

The reference route is the deterministic optimum at zone cost 1. The threshold is the first tested cost at which keeping that exact reference path costs strictly more than the current optimum. Equal-cost alternatives do not count. A null threshold means no strict loss in the tested range, or no reference route exists. It makes no claim about costs above 9.

Rush hour has three selected cells. At cost 1 the reference takes four steps and costs 4. At cost 2 the reference costs 7, while the six-step bypass costs 6. The slider selects one of nine real backend responses. The chart and table use those same responses.

## Independent single-cell closures

The service solves the original map, then tests each open non-endpoint cell independently as a wall. It starts from the same original map for each test. A critical cell disconnects an originally reachable start and goal. If both paths exist, delta measures extra optimal cost; otherwise delta is null. Maximum added cost includes only tests with surviving routes.

The bridge example has 69 eligible closure cells, of which 3 disconnect the endpoints. Opening the additional crossing at row 2, column 5 produces 70 eligible cells and zero disconnecting single-cell closures. Both maps use the same endpoints. This test establishes survival of these individual closures, not simultaneous failures or a probability of safe travel.

Click a cell to inspect its closure. The service computes the surviving replacement path through the existing solve operation. Use the editor to test other repairs. The before/after text reports the number tested in both maps because opening a passage changes the candidate count.

## Scenarios

| Map | Experiment |
|---|---|
| City blocks | Intersections and multiple equal-cost routes |
| Rush hour | The exact cost at which the original route loses optimality |
| Roadworks | A closed central section with a surviving 12-step detour |
| Main road vs bypass | A 12-cost detour versus the 29-cost direct street |
| Bridge bottleneck | Single failures and an additional crossing |
| Disconnected district | Explicit unreachable results and zero newly critical cells |

The four original maps remain available. JSON examples contain only solve-ready fields. Preset metadata includes explanations and optional traffic cells; the API rejects descriptive metadata in solve/analysis bodies.

## Reuse and boundaries

`route_lab.service.threshold` and `route_lab.service.closures` provide the same calculations as `POST /api/threshold` and `POST /api/closures`. See [API contract](API.md). Export analysis saves the actual map, zone, selected cost/closure and response. Changing a map or mode clears old results; delayed responses cannot replace a newer selection.

The project uses established shortest-path algorithms. It supplies inspectable experiments, original synthetic fixtures and reusable local code. It does not ingest live traffic, geographic networks, directional road rules or calibrated travel times. It does not estimate failure probabilities or propose a new optimization algorithm.
