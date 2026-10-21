# RouteLab: application walkthrough

Source version 0.1.1; actual local captures on 2026-10-21.

Fresh visual/API scenarios cover current-map solving, congestion, one-at-a-time closures, a second crossing and validation. Existing solver/oracle, asynchronous-import and keyboard tests support deeper behavior. The gallery does not model simultaneous closures, real roads or real traffic.

## Compare two optimal solvers

Run A* and Dijkstra on the same weighted grid. Both find cost 26 in this example. Expansion counts describe this map, not a universal speed advantage.

![Compare two optimal solvers](images/workspace-desktop.jpg)

## Traffic as a modeled cost

Select the rush-hour scenario. Increased tile costs make a six-cost detour preferable to the seven-cost reference path; these are synthetic costs, not live traffic.

![Traffic as a modeled cost](images/congestion-desktop.jpg)

## Inspect the map on a narrow screen

Use the same congestion scenario in the responsive browser layout. This screenshot checks presentation, not a physical phone.

![Inspect the map on a narrow screen](images/congestion-mobile.jpg)

## Find a fragile crossing

Run the single-tile closure sweep. Three of 69 tested closures disconnect this map. Each trial closes one tile independently.

![Find a fragile crossing](images/bridge-closures.jpg)

## Test a proposed improvement

Add the second crossing and repeat the sweep. All 70 tested single-tile closures remain connected; the maximum added route cost is two in this scenario.

![Test a proposed improvement](images/second-crossing.jpg)

## Read the recorded benchmark

Inspect the 90 recorded rows and their route/expansion results. These are historical runs, separate from the current map calculation.

![Read the recorded benchmark](images/benchmark.jpg)

## Call the solver API

Send POST /api/compare through the application console. The local server returns HTTP 200 and the two algorithms agree on detour cost six.

![Call the solver API](images/api-success.jpg)

## Reject an invalid grid

Send an empty grid. The server returns HTTP 400 with a grid validation error instead of constructing an invalid route.

![Reject an invalid grid](images/api-validation.jpg)
