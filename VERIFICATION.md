# Historical local verification — 2026-09-08

This translates the original record; it does not report a new run. Host:
macOS arm64; compiler based on parent commit `94d1e85` with the D092 named-void
pattern fix. Source/compiler/engine hashes and exact commands are in the
reports and language evidence `cp42-files-context-2026-09-08.json`.

- Source tests: **4**, `mmay test . --engine both`.
- Process scenarios: **31**, exact stdout/stderr/status in VM/native
  Debug/Release; separate denied cases use VM and native Release.
- Closed stdout: **3**, with typed write/flush failures.
- Acceptance: `python3 tools/acceptance.py`, `build/acceptance/report.json`.
- Measurement: `python3 tools/measure.py`, `build/latest-measurement.txt`.

| Workload | Engine | First sample, ms | Remaining median*, ms | Max RSS, MiB |
|---|---|---:|---:|---:|
| 1-files | native | 391.37 | 9.04 | 2.20 |
| 1-files | vm | 452.07 | 440.12 | 29.00 |
| 1000-files | native | 30.90 | 29.26 | 7.77 |
| 1000-files | vm | 606.83 | 614.12 | 33.42 |
| 10000-files | native | 237.87 | 237.87 | 41.19 |
| 10000-files | vm | 2003.49 | 2003.49 | 70.98 |

*When only one sample exists, it is shown in both columns. The 1000-file and
100-env/100-path workloads have three repetitions; the 10000-file workload has
one. JSON retains all raw samples. This table does not establish confidence
intervals or a stable cross-platform baseline. Repeated source-test both:
787.08 ms against a 2000 ms budget.

Large-workload and RSS budgets passed locally. **First native execution missed
100 ms**; subsequent small runs passed, without relaxing the budget. Processes
were measured sequentially after verification with ordinary background apps.
No cleared disk cache, fresh host or proven system-level explanation of the
startup delay was claimed. Full CP42 acceptance remained open.
