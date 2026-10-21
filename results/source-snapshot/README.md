# Exact source of the supplied benchmark

These four Python files match source_files in ../benchmark.json byte-for-byte. They were recovered from the preserved pre-Lab source archive outputs/ui-fix-2026-10-20/route-lab-ui-2026-10-20.zip. The benchmark already included those hashes; this update does not alter its recorded measurements or hash claims.

The current package imports src/route_lab, not this directory. service.py in this snapshot predates the Lab features. The current core.py and benchmark.py match their recorded copies. Run python scripts/verify_results.py to verify the recorded bytes and report current-source differences separately.
