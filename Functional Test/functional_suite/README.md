# Bakery Functional Test Suite

Implements `Functional Test/test_spec.md` end to end: it restores the four
fixture projects, installs Bakery into a real KiCad 10 install, drives the
plugin's wxPython UI, and verifies the localized output against the
assertions in the spec (Sections 8-13). It has been validated against a real
interactive KiCad 10 install, not just written against the spec text.

## Requirements

- Windows with KiCad 10 installed (KiCad 9/8 optional, only needed if you
  also want to sanity-check `install.bat`/`start-manuel-test.bat` against
  older installs manually).
- Python 3.x with `pywinauto`, `pywin32`, and `psutil` installed
  (`pip install pywinauto pywin32 psutil`).
- Network access for datasheet downloads is *not* required — datasheet
  failures are captured and classified, not treated as hard failures (see
  "Known/expected fixture issues" below).

## Running the suite

```powershell
# From the repository root, run every fixture (FT-01..FT-04):
python -m functional_suite.run_functional_tests
# (run from "Functional Test\", or add it to PYTHONPATH first)

# Run a subset while iterating:
python -m functional_suite.run_functional_tests --fixtures FT-01,FT-03

# Skip the second-run idempotence pass and/or the KiCad PCB/schematic reopen check:
python -m functional_suite.run_functional_tests --skip-idempotence --skip-reopen
```

The suite always:

1. Runs preflight checks (`ENV-01..08`) — KiCad 10 present, no stale
   `pcbnew.exe`/plugin processes, disk space, etc. Fails fast with a clear
   message if any preflight check fails.
2. Cleans `C:\GIT_HUB\testing`, deleting every entry **except the `results`
   tree**, so no artifact from an earlier run or from manual testing can be
   mistaken for output produced by the current run. Historical result
   bundles are preserved. Reported as the `CLEAN` step; the removed entry
   names are recorded in its `details`.
3. Restores the four named fixtures via `start-manuel-test.bat` into
   `C:\GIT_HUB\testing` and verifies the copy with a SHA-256 manifest
   (`SETUP-01..07`).
4. Installs Bakery via `install.bat` and verifies the installed files with a
   SHA-256 manifest against the repository source (`INST-01..06`).
5. For each selected fixture: captures a baseline, launches `pcbnew.exe`,
   drives the Bakery UI (config dialog → confirmation → completion →
   success), and verifies the result against the `AST-*` assertions.
6. Re-runs Bakery in the same session and checks idempotence (`IDM-01..07`),
   then reopens the localized PCB and root schematic in fresh KiCad
   processes to confirm both still load (`AST-RUI-01..04`, Section 9.7).
7. Confirms the source fixtures were not mutated (`FIX-01`).
8. Writes `junit.xml`, `summary.json`, `environment.json`,
   `report.md`, and `installed-plugin-manifest.json` under
   `C:\GIT_HUB\testing\results\<timestamp>\` (Section 14), and returns 0 only
   if every assertion passed (RES-06/RES-07).

`BAKERY_TEST_TIMEOUT_SECONDS` overrides the five-minute per-project timeout
without editing code (Section 8.3).

## Bakery is invoked exactly once per pass (`RUN-ONCE-*`)

Bakery localizes a project in a **single pass**; it never needs a second run
to finish its work. The suite proves this two ways:

- `RUN-ONCE-01`/`RUN-ONCE-02` assert that exactly one backup archive appears
  per Bakery invocation. Bakery writes one archive per run, so an extra
  archive means one invocation localized the project more than once. This is
  otherwise invisible, because a repeated pass is idempotent and leaves the
  same files behind.
- `IDM-07` asserts the second run reports *"All footprints and symbols were
  already in local libraries"* — i.e. the first pass had already finished
  everything.

The suite deliberately runs Bakery **twice per fixture**: once to do the
work, and once more to prove the operation is idempotent (spec Section 11,
`IDM-01..07`). That second run is the *verification* that one pass is
sufficient, not Bakery needing two passes. Use `--skip-idempotence` to run
each fixture a single time; the `IDM-*` rows are then reported as skipped.

A genuine unintended double-invocation was fixed in `_invoke_plugin_menu`:
its retry loop (added to survive KiCad's cold-start `ElementNotEnabled`
race) could re-select the menu entry after `menu_select` had already posted
the command, launching Bakery twice in one pass. It now checks for an
existing Bakery dialog before every retry and returns instead of clicking
again.

## Release report (`report.md`)

Every run writes a `report.md` beside the JSON artifacts: a formatted,
release-ready summary intended for pasting onto a Bakery release page. It
renders the verdict and totals, the environment tested against, per-fixture
results, assertion coverage grouped by area, the deliberately-tolerated
known fixture issues (and whether Bakery reported each one), and — only when
something failed — a failures section naming the failed assertions.

It is a pure transformation of `summary.json` + `environment.json`, so it can
never disagree with the machine-readable results, and any historical run can
be re-rendered without re-running the suite:

```powershell
# Re-render the most recent run
python -m functional_suite.markdown_report

# Re-render a specific run
python -m functional_suite.markdown_report C:\GIT_HUB\testing\results\2026-09-02_180513
```

## Known/expected fixture issues (allowlist)

The shipped fixtures intentionally contain a few permanently-unresolvable
references — a missing 3D model file, dead/blocked datasheet URLs, and (in
FT-02) dangling local symbol references — to exercise Bakery's
warning/error handling (spec TC-08/09/12/24/25). These are *not*
environment gaps in the test machine. Per project direction, the suite
treats them as **regression checks in their own right**:

- `functional_suite/config.py::EXPECTED_FIXTURE_ISSUES` is a per-fixture
  allowlist of substrings (3D model filenames/paths, datasheet URLs) and
  full `Lib:Name` symbol references that are known-intentional.
- `ProjectVerifier.verify_models`/`verify_datasheets`/`verify_symbols`
  exclude allowlisted items from the hard-fail checks (`AST-MDL-03/04/05`,
  `AST-DS-04`, `AST-SYM-01/04`) so a known-bad fixture item does not fail
  the run.
- `ProjectVerifier.verify_known_issues` then asserts every allowlisted item
  is **still** present and unresolved after the run — if a known issue
  silently disappears (e.g. because Bakery's handling of it changed), that
  is itself reported as a failure, since it means the regression case is no
  longer being exercised.
- `ProjectVerifier.verify_known_issues_trapped` asserts Bakery **actively
  trapped** each allowlisted item, by requiring it to be named in the run's
  Warnings or Errors pane (`TRAP-MDL-*`, `TRAP-DS-*`, `TRAP-SYM-*`). The
  presence check above is not sufficient on its own: a Bakery build that
  silently skipped the item entirely would also leave the broken reference
  in place and therefore still pass it. Requiring the condition to be
  surfaced to the user is what makes "Bakery detects and reports these"
  an actual test rather than an assumption.
- Any unresolved reference that is *not* on the allowlist still fails the
  test normally.

Both problem panes are searched together in the trap check, because which
pane a condition lands in is a Bakery implementation detail (unresolved
models and symbols are logged as warnings, datasheet download failures as
errors). What is asserted is that it appeared in a *problem* pane at all,
rather than only in the informational Log pane. On any assertion failure the
run's Log/Warnings/Errors pane text is now written to the failure-evidence
bundle (`FAIL-06..08`), so a `TRAP-*` failure is diagnosable after the fact.

`EXPECTED_FIXTURE_ISSUES` has been populated and confirmed against live
runs for **all four fixtures** (FT-01 on 2026-09-01; FT-02/03/04 on
2026-09-02, results `2026-09-02_155539` / `2026-09-02_161148`).

Similarly, `kicad_driver.classify_error_lines()` splits the Bakery Errors
pane into genuine Bakery errors (hard failure, per RUN-09/AST-UI-05) versus
datasheet network/download failures (recorded as a separate `"environment"`
outcome, per ENV-06/AST-DS-04) — this reconciles the two per spec sections
that would otherwise conflict for TC-24/TC-25.

## Fixed: Bakery was not idempotent for 3D model paths

Running Bakery a second time on an already-localized FT-01 project used to
cause previously-localized `(model "${KIPRJMOD}/3D Models/...")` references
in the board file to **revert** to global paths
(`${KICAD9_3DMODEL_DIR}/...`/`${KICAD10_3DMODEL_DIR}/...`). This was
confirmed by diffing the `.kicad_pcb` file after each of two consecutive
Bakery runs on a freshly-restored fixture, and is now caught/verified by
`IDM-04`/`IDM-06`/`AST-MDL-03..05`.

Root cause (in `plugins/footprint_localizer.py`), confirmed via live,
instrumented KiCad runs:

1. `update_pcb_references()` tried to fix each footprint's embedded 3D
   model reference in memory via `for model in fp.Models(): model.m_Filename
   = new_path`. In KiCad's SWIG/pcbnew bindings, indexed access into the
   `VECTOR_FP_3DMODEL` returned by `fp.Models()` yields a **copy** of each
   `FP_3DMODEL` element, so mutating `model.m_Filename` directly was a
   silent no-op — the in-memory board never actually changed.
2. Because of (1), the only place the fix "worked" was
   `update_pcb_model_paths()`'s separate textual find/replace pass over the
   just-saved `.kicad_pcb` file, driven entirely by `self.copied_models`
   (the old-global-path → new-local-path map built while copying 3D models
   that run).
3. On a second run, footprints are already local, so `localize_3d_models()`
   only produces **identity** mappings (local → local) — it has no memory
   of the original global path. The textual patch therefore can't repair
   the still-stale in-memory global path that `board.Save()` had just
   written to disk, and any subsequent save (e.g. on KiCad exit) would
   re-persist the stale global paths.

Fix applied:

- `update_pcb_references()` now writes the mutated `FP_3DMODEL` back into
  the vector with `models[idx] = model` (SWIG `std::vector::__setitem__`),
  which is required for edits to actually persist on the footprint.
- `update_pcb_model_paths()` gained an optional supplemental sweep
  (`resolve_unlocalized_pcb_models()`) that scans the saved `.kicad_pcb`
  text directly for any embedded model path not yet covered by
  `self.copied_models` and not already `${KIPRJMOD}/...`, resolves it via
  `LibraryManager.expand_path()`, and copies it into the local 3D Models
  folder if needed — making the repair self-sufficient on any run, not
  just the first.

Both changes were verified live: two consecutive Bakery runs plus a final
KiCad save-and-close no longer revert any embedded 3D model path (aside
from the pre-existing, unrelated `KSA_Tactile_SPST.step` missing-source-file
case already tracked in the known-issue allowlist).

## Test case (TC-01..34) coverage

| TC | Covered by | Notes |
|----|------------|-------|
| TC-01..07 | `AST-FPT-*`/`AST-SYM-*` in `verifier.py`, driven by FT-01..04 | Basic/global localization paths |
| TC-08, TC-09 | `EXPECTED_FIXTURE_ISSUES` + `verify_models`/`verify_known_issues`/`verify_known_issues_trapped` | Missing 3D model handling (FT-01 confirmed); `TRAP-MDL-*` confirms the warning was actually raised |
| TC-10, TC-11 | `AST-MDL-*` | 3D model copy/relink checks |
| TC-12 | `EXPECTED_FIXTURE_ISSUES`/`verify_datasheets`/`verify_known_issues_trapped` | Dead datasheet URL handling; `TRAP-DS-*` confirms each failure was reported |
| TC-13..16 | `AST-BKP-*` | Backup archive checks |
| TC-17 | `synthetic.make_corrupt_symbol_library_fixture` | Written, **not wired into the main runner** — standalone extension point |
| TC-18..23 | `IDM-*`, `AST-RUI-01` | Idempotence + reopen; found and verified the fix for the 3D-model regression above |
| TC-24, TC-25 | `classify_error_lines` + `EXPECTED_FIXTURE_ISSUES` + `verify_known_issues_trapped` | Datasheet network failure classification; `TRAP-DS-*` asserts the URLs reached the Errors pane |
| TC-26, TC-27 | `LGC-*` handling in `kicad_driver._handle_startup_dialogs` | Legacy KiCad-9 project conversion; exercised live for FT-02/FT-04 on 2026-09-02 |
| TC-28 | `synthetic.make_missing_library_tables_fixture` | Written, **not wired into the main runner** |
| TC-29..32 | `environment.py` preflight (`ENV-01..08`) | |
| TC-33 | `synthetic.make_duplicate_backup_race_fixture` | Written, **not wired into the main runner** |
| TC-34 | `synthetic.make_all_hidden_project_fixture` | Written, **not wired into the main runner** |

The spec itself notes (Section 17) that several TCs require synthetic
fixtures beyond the four shipped ones; `functional_suite/synthetic.py`
implements generators for TC-17/28/33/34 as documented, standalone utilities
you can call directly to build a throwaway fixture and point
`ProjectVerifier`/`KicadDriver` at it — they are intentionally not wired
into `run_functional_tests.py`'s default run so the default run stays
focused on the four real, shipped fixtures.

## Idempotence state is always reported

Every `IDM-*` assertion is recorded in `summary.json` on every run, whether
it passed, failed, or was skipped — a result file can never be silently
missing them:

- The idempotence findings are merged into the fixture's main
  `VerificationReport`, so a **green** run's `details.findings` now contains
  `IDM-01..07` alongside the `AST-*` rows.
- A **failing** idempotence run records the merged report too, so the
  failure evidence also carries the first-run `AST-*` context.
- With `--skip-idempotence`, `verifier.skipped_idempotence_report()` emits
  one row per `IDM-*` ID with a `SKIPPED: <reason>` message. `Finding.passed`
  is a plain bool with no tri-state, so skipped rows are recorded as passed
  and identified by the message prefix.

`IDM-07` (spec line 350 — Bakery must report that everything was already
local on the second run) was previously undocumented and unimplemented; it
now asserts the second run's Log pane contains
`All footprints and symbols were already in local libraries.` or
`Copied 0 footprints and 0 symbols to local libraries.` `bakery_plugin.py`
only emits the first wording (the two are mutually exclusive branches), but
both are accepted because the spec permits either.

## Not yet validated

- `synthetic.py` generators are implemented but have not been exercised by
  an actual test run.

## Fixed: dangling local symbol references were silently reported as success

FT-02 (`Ki-Test 01-09 - Backup`) ships a half-localized project: its
`sym-lib-table` declares `MySymbols` at
`${KIPRJMOD}/MySym/MySymbols.kicad_sym` and every schematic symbol
references `MySymbols:*`, but neither the `MySym` directory nor the library
file exists, and no copy survives in the fixture's own `Ki-Test-backups`
archive. (FT-03/FT-04 by contrast ship a genuinely populated `MySym`, so
this is specific to FT-02 rather than the intended pattern.)

`SymbolLocalizer.copy_symbols` decided a symbol was "already local" from
the **library nickname alone** (`lib_name == symbol_lib_name`), so all four
references were skipped with `→ Skipping MySymbols:R (already local)` and
Bakery reported `Localization complete!` — leaving a project that cannot be
opened without missing-symbol errors. The check now also requires the
symbol to actually be present in a readable local library file; otherwise
the reference is reported as an unresolved local symbol in the Warnings
pane (not the Errors pane, so `RUN-09`/`AST-UI-05` stay meaningful) and
left untouched, since there is no source library to copy from.

The fixture itself was deliberately **not** modified — fabricating symbol
content would invent test data that never existed. Instead the four
references are recorded in `EXPECTED_FIXTURE_ISSUES["FT-02"]
["unresolved_symbols"]`, so `AST-SYM-01/04` tolerate them while the new
`KNOWN-SYM-*` assertions confirm Bakery keeps detecting them.

## Module map

| Module | Spec component | Responsibility |
|--------|----------------|-----------------|
| `config.py` | — | Paths, fixture matrix, timeouts, allowlists |
| `manifest.py` | SETUP-07/INST-06/FIX-01/IDM-06 | SHA-256 recursive manifest + diff |
| `environment.py` | COMP-01 | Preflight, batch script invocation, version detection |
| `kicad_driver.py` | COMP-02 | wxPython/pywinauto UI automation |
| `verifier.py` | COMP-03 | Post-run file/reference assertions |
| `reporter.py` | COMP-04 | JUnit XML, JSON summary, failure evidence |
| `markdown_report.py` | RES-02 | Release-ready `report.md` rendered from the JSON results |
| `fixtures.py` | Section 4/12 | Fixture discovery, baseline capture, source-integrity check |
| `synthetic.py` | Section 17 | Synthetic fixture generators (extension points) |
| `run_functional_tests.py` | — | CLI entry point tying everything together |
