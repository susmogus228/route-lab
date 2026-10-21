# Sources and resource provenance

Checked 2026-10-19.

| Resource | Source and use | Terms / status |
|---|---|---|
| Dijkstra / BFS / weighted path definitions | [NetworkX shortest paths documentation](https://networkx.org/documentation/stable/reference/algorithms/shortest_paths.html) | Reference only; own implementation, no vendored source |
| A* heuristic constraints / multiple shortest paths | [NetworkX A* documentation](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.shortest_paths.astar.astar_path.html) | Reference only; no runtime dependency |
| Heap operations / priority-queue patterns | [Python 3.12 heapq documentation](https://docs.python.org/3.12/library/heapq.html) | Standard-library API reference |
| Ten built-in editable maps | `route_lab.service.presets` | Original synthetic fixtures; project MIT license |
| Benchmark maps | `route_lab.benchmark.generate_scenario`; saved `results/scenarios/*.json` | Original seeded synthetic fixtures; project MIT license; individual SHA-256 in benchmark JSON/CSV |
| Benchmark chart | `results/benchmark.svg` from recorded rows | Original vector plot; no external font/image assets |
| UI screenshots | Captured during integration, when included | Actual local application captures; not model-generated UI or performance evidence |

The benchmark JSON records environment, protocol SHA-256, source-file SHA-256 values, exact scenario hashes, aggregate rows, and raw repetitions. No scraped map, private campus plan, map tile service, or third-party personal dataset enters this project.

NetworkX documentation is a conceptual reference. An independent test oracle uses a separate Bellman-Ford implementation in the tests. We do not claim that NetworkX is installed or that its runtime output has been checked unless a separate verification record states that fact.

## Experiment positioning, checked 2026-10-20

[Google Routes traffic preferences](https://developers.google.com/maps/documentation/routes/config_trade_offs) document traffic-aware routing. [Red Blob Games A* explanations](https://www.redblobgames.com/pathfinding/a-star/introduction.html) and [map bottleneck analysis](https://www.redblobgames.com/pathfinding/all-pairs/) already demonstrate related concepts. These references informed project positioning; no source code, images or external map data were copied. RouteLab claims an inspectable implementation and reproducible experiments, not a new pathfinding or resilience algorithm.

The six added fixtures, Lab canvas, cost plot and screenshots are original project outputs under the project MIT license. All displayed costs come from the local Python solver. No additional runtime library, font or image asset was downloaded for the Lab.
