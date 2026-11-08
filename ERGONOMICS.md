# Ergonomics observations

## Shared decisions in the filesystem wave

- `fs.readDirectory` returns sorted sibling names and explicit entry kinds.
  A separate tree sort establishes global path order.
- The shared `tree` package uses an explicit stack, total-entry and depth limits,
  accumulates subdirectory errors and does not follow symlinks. Its pinned
  version is recorded in `PROVENANCE.json`; both consumers retain their tests.
- `std/text` lacks a public lexical comparator, and `<`/`<=` on strings are
  rejected with T0003. This is an API gap, not an integer-comparison defect.
  The `tree` sort encodes each path once into Bytes and compares those keys
  without per-comparison allocations. Memory is O(total path length); sorting
  uses O(n log n) comparisons. A general public sort/comparator needs its own
  rationale; no language API was added solely for this utility.
- `fs.LimitExceeded` must not stand for a directory-entry limit: the separate
  `fs.TooManyEntries` exists. Acceptance confirmed the corrected mapping; global
  overflow now fails while preserving the previous output file.
- D092 fixed the checker defect involving `Ok(value)` from `Result<void,E>`:
  T0002 replaces an internal or silent failure, including nested/named patterns.
  Valid void consumption continues to use `Ok(_)`.

## Remaining shared limitations

The escaping-mutable-capture warning and `Result<T,never>` transport remain open
language work. This package does not implement or close them. Full CP42,
platform validation, startup budgets and later CP41/CP39/CP40 remain open too.
Timing and memory observations are recorded in `VERIFICATION.md`. This is a
historical account rather than a new verification of the current compiler.

The config v1/v2 validator is reused as a package without rewriting its JSON
decoder. Requiring `requiredFiles` to remain inside the root belongs to the
checking application and does not change the config schema. Explicit
`unverified` findings prevent claims that inaccessible files are missing.
Every applicable finding is collected before output.
