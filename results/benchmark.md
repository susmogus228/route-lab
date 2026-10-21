# RouteLab recorded benchmark

45 synthetic scenarios; 450 timed runs; 5 repetitions per algorithm after one warmup.

All recorded Dijkstra and A* costs agree. Timings exclude validation and serialization; trace capture is disabled.

| Family | Size | Dijkstra median ms | A* median ms |
|---|---:|---:|---:|
| open_uniform | 32 | 2.280 | 0.185 |
| open_uniform | 64 | 9.777 | 0.396 |
| open_uniform | 128 | 43.509 | 0.812 |
| open_weighted | 32 | 2.255 | 2.613 |
| open_weighted | 64 | 10.092 | 11.524 |
| open_weighted | 128 | 44.360 | 51.389 |
| blocked_weighted | 32 | 1.634 | 1.783 |
| blocked_weighted | 64 | 9.828 | 9.051 |
| blocked_weighted | 128 | 34.844 | 39.461 |

Table values are medians across per-map timing medians. Inspect per-seed rows and all raw measurements before interpreting the aggregate.

A* can expand fewer nodes while spending time on heuristic calculations. These results establish measured behavior on the saved fixtures, not a universal ranking.

![Recorded benchmark](benchmark.svg)
