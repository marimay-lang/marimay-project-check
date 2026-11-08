# Budgets defined before measurement

Local CLI: first and repeated ready-native execution ≤100 ms, small VM case
≤500 ms, and `mmay test . --engine both` ≤2 s. Measure the first native
execution immediately after build, without warming it first.

File applications use a synthetic tree of 1000 files in 20 directories with
Unicode names, varied sizes and a known JSON/report: native ≤2 s, VM ≤20 s.
The extension to 10000 files in 100 directories has native ≤20 s and VM
≤200 s. Peak RSS is ≤128 MiB native and ≤256 MiB VM; managed heap is 64 MiB.
Measurement results must not relax budgets. Larger workloads do not replace
exact acceptance of errors, overflow and changes to the scanned tree.

Env-paths uses 100 explicitly named synthetic variables (64 permitted and 36
exercising existing capability denial) and 100 paths: native ≤100 ms, VM
≤500 ms, with the same RSS limits. It never dumps the environment. Reports
record host, revisions, inputs, first/repeated conditions and raw samples.
