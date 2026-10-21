# Weighted-grid algorithms

Each walkable cell is a vertex. For adjacent walkable cells `u` and `v`, a directed edge `u -> v` has weight equal to the value of `v`. Both directions can exist with different weights. Start cost is zero regardless of its cell value.

The implementation uses a minimum heap, distance and predecessor maps, and a settled set. It ignores stale heap entries and stops when it settles the goal. Discovering the goal alone is not sufficient to finish.

Dijkstra orders by accumulated path cost `g`. A* orders by `f = g + h`, where `h` is Manhattan distance to the goal times the minimum positive cost in the fixed grid. Every move costs at least that minimum and changes Manhattan distance by at most one. The heuristic is therefore admissible and consistent under this four-neighbor model. It may be weak if a cheap but irrelevant cell lowers the global minimum.

Ties use `(f, h, insertion serial)`. The insertion order follows up, right, down, left. The predecessor changes only on a strict improvement. These decisions produce deterministic paths and traces for a fixed request. Different correct algorithms can choose different optimal paths.

With bounded degree, `E <= 4V`. Search costs `O((V+E) log V)` in the usual heap analysis and stores `O(V+E)` state when allowing stale heap entries. The grid maximum is 16,384 cells. Recorded traces add at most 2,048 small entries and do not stop the search.

`expanded` counts accepted node pops, including the goal if reached. `heap_peak` records the maximum queue length and can include stale entries. The UI may replay expanded nodes from `trace`; it cannot recover the exact frontier from these events alone. `trace_truncated` states that some expansions were not recorded. A missing trace is not an incomplete solve.

Breadth-first search minimizes the number of edges. A weighted detour can be cheaper while taking more steps, so BFS is not offered as a competing optimal weighted solver.

Independent tests use Bellman-Ford relaxation with separately defined adjacency and destination weights. They compare optimal cost and reachability, then recompute route validity and cost without calling production helpers.
