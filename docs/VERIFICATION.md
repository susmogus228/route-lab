# Verification

Core implementation evidence, 2026-10-19:

- Initial RED: 47 tests failed because the solver package had not been implemented.
- Core GREEN: 47 tests passed after the core/service implementation.
- CLI/benchmark RED: four new tests failed because CLI/benchmark modules were missing; an existing service-validation check passed.
- Combined GREEN: 52 tests passed after CLI and benchmark implementation.
- The exhaustive test covers 648 valid grid/endpoint combinations from every 2x2 grid over values 0, 1, and 2. Both algorithms run on each combination. An independent Bellman-Ford oracle supplies costs.
- Sixty seeded random grids provide another 120 algorithm/oracle comparisons. Additional fixtures cover asymmetric entry weights, blocked goals, weighted detours, and equal endpoints.
- The saved benchmark contains 45 scenario files, 90 summaries, and 450 measured runs. Every measured run matches its algorithm's warmup cost and expansion count; Dijkstra and A* costs match for each scenario.

Commands from the repository root:

```sh
python -m pytest tests/test_core.py tests/test_cli_benchmark.py -q
python scripts/verify_results.py
python -m route_lab benchmark --output work/reproduced-results
python -m route_lab solve --input examples/weighted-detour.json --algorithm dijkstra --path-csv work/path.csv
```

Create the output parent directory before CLI exports. The benchmark command creates its own directory.

These core checks do not establish web-interface correctness, wheel portability, public deployment, or GitHub publication. Integration/release verification must record those checks separately after the actual artifacts exist. No external NetworkX run is included in the current core evidence.

The benchmark ran on a shared development host without isolating other process load. Treat its timings as exploratory measurements, preserve the raw repetitions, and rerun on an idle host before making performance conclusions. Chart panels use their own horizontal scale; read the millisecond annotations when comparing across map families.

## Integrated UI correction, 2026-10-20

58 Python tests and64 focused browser assertions passed after the responsive correction. An independent UI Designer confirmed closure of the reported layout defect. [Evidence and limits](UI_FIX_2026-10-20.md) distinguish the corrected first-screen layout from precision touch editing of large maps.

## Resilience Lab, 2026-10-20

115 Python tests passed, including 47 new analysis/scenario tests, six real HTTP integration tests and four historical-source verification tests. The browser suites passed 68 editor and 51 Lab assertions. [Current evidence](LAB_VERIFICATION_2026-10-20.md) records exact scenarios, limits and reviewer status. Prior correction counts above describe the earlier snapshot.

## Integrated audit correction, 2026-10-20

See [the current integrated record](AUDIT_FIXES_2026-10-20.md) for the corrected behavior, fresh browser cases, result preservation and installed-wheel smoke. Earlier counts above describe their own source snapshots.
