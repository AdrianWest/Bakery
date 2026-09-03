# Bakery Automated Functional Test Specification

## 1. Purpose

Build a Windows functional test suite that proves the current Bakery source can
be installed into KiCad, launched against representative projects, complete its
GUI workflow, and produce self-contained KiCad projects without corrupting the
source fixtures.

The suite must automate the same high-level workflow as a manual release test:

1. Restore clean copies of the four projects from `Functional Test`.
2. Install the current Bakery source with `install.bat`.
3. Open each copied PCB in KiCad PCB Editor.
4. Run Bakery from **Tools > External Plugins**.
5. Accept the default Bakery configuration and confirm localization.
6. Verify the Bakery result in the UI and on disk.
7. Reopen the project and verify KiCad can load the localized PCB and root
   schematic.
8. Produce machine-readable results and failure evidence.

## 2. Compatibility Scope

Bakery currently installs into and runs under **KiCad 10 only**. The projects
whose names contain `-09` are KiCad 9-format compatibility inputs; they are not
executed with KiCad 9. They must be opened and processed by KiCad 10 to verify
legacy project compatibility and normalization of legacy `${KICAD9_*}` paths.

Execution under the KiCad 9 application is out of scope unless Bakery restores
KiCad 9 runtime support in a future release.

## 3. Source and Working Directories

| Purpose | Path |
|---|---|
| Repository | `C:\GIT_HUB\Bakery` |
| Immutable functional fixtures | `C:\GIT_HUB\Bakery\Functional Test` |
| Fixture preparation script | `C:\GIT_HUB\Bakery\start-manuel-test.bat` |
| Plugin installation script | `C:\GIT_HUB\Bakery\install.bat` |
| Test workspace | `C:\GIT_HUB\testing` |
| Installed KiCad 10 plugin | `%USERPROFILE%\Documents\KiCad\10.0\scripting\plugins\Bakery` |
| Test results | `C:\GIT_HUB\testing\results` |

The suite must never run Bakery directly against a project below
`C:\GIT_HUB\Bakery\Functional Test`.

## 4. Test Fixture Matrix

`start-manuel-test.bat` removes the ` - Backup` or ` - BackUp` suffix while
copying each fixture to the test workspace.

| Test ID | Source fixture | Working project | PCB file | Intent |
|---|---|---|---|---|
| FT-01 | `Ki-Test 01-10 - Backup` | `Ki-Test 01-10` | `Ki-Test.kicad_pcb` | KiCad 10 basic/global-library localization |
| FT-02 | `Ki-Test 01-09 - Backup` | `Ki-Test 01-09` | `Ki-Test.kicad_pcb` | KiCad 9-format project opened and localized by KiCad 10 |
| FT-03 | `Ki-Test 02-10 - BackUp` | `Ki-Test 02-10` | `5V_REG_20A.kicad_pcb` | KiCad 10 mixed local/global project and existing-assets handling |
| FT-04 | `Ki-Test 02-09 - BackUp` | `Ki-Test 02-09` | `5V_REG_20A.kicad_pcb` | KiCad 9-format mixed project, legacy paths, and existing-assets handling |

The test runner must discover only these four fixture directories. Markdown
files and other files stored in `Functional Test` must not be copied as test
projects.

## 5. Required Test Environment

The runner must check these prerequisites before changing any files:

- **ENV-01** — Windows 10 or Windows 11 interactive desktop session.
- **ENV-02** — KiCad 10 PCB Editor and Schematic Editor installed.
- **ENV-03** — The KiCad 10 global symbol, footprint, and 3D model libraries
  required by the fixtures are installed and configured.
- **ENV-04** — Python 3 available to the test runner.
- **ENV-05** — A Windows UI Automation library capable of controlling native
  KiCad and wxPython dialogs. The initial implementation should use
  `pywinauto` with the UI Automation backend.
- **ENV-06** — Internet access for remote PDF datasheet tests. A missing or
  unreachable external datasheet must be reported separately from a Bakery
  application failure.
- **ENV-07** — No PCB Editor, Schematic Editor, Symbol Editor, or Footprint
  Editor process may have one of the working fixtures open. This is a
  test-environment safeguard the runner enforces itself: Bakery only checks
  for locked `.kicad_sch` files (via a `~*.lck` marker and an OS file-lock
  probe) and does not detect an open PCB, Footprint, or Symbol Editor. A
  failure caused by one of these other editors being open must be attributed
  to the test environment, not to Bakery.
- **ENV-08** — The runner fails during preflight, rather than skipping
  silently, when KiCad, the plugin install location, or a required fixture
  cannot be found.

## 6. Automation Components

The suite should contain four logical components:

1. **COMP-01 — Environment controller**
   - Locates KiCad 10.
   - Ensures stale test-owned KiCad processes are closed.
   - Runs fixture preparation and plugin installation.
   - Records KiCad and Bakery versions.

2. **COMP-02 — KiCad UI driver**
   - Starts `pcbnew.exe` with the copied `.kicad_pcb` path.
   - Handles a KiCad 9-to-10 conversion prompt when one appears.
   - Opens **Tools > External Plugins** and selects
     **Bakery - Localize Symbols, Footprints, and 3D Models**.
   - Drives the Bakery configuration, confirmation, log, and success dialogs.
   - Saves and closes the PCB Editor.
   - Reopens the localized root schematic in KiCad Schematic Editor and fails
     on missing-symbol-library, rescue, or schematic parse dialogs.

3. **COMP-03 — Project verifier**
   - Captures a pre-run manifest.
   - Parses or inspects the resulting KiCad S-expression files.
   - Verifies localized libraries, references, backups, and file integrity.
   - Performs an idempotence comparison after a second Bakery run.

4. **COMP-04 — Result reporter**
   - Writes JUnit XML and a JSON summary.
   - Captures screenshots and Bakery log text on failure.
   - Preserves the failed working project for diagnosis.

## 7. Script Requirements

### 7.1 Fixture preparation

The automated suite must use `start-manuel-test.bat` as the canonical fixture
copy operation. The script must support a non-interactive mode that:

- **SETUP-01** — Recreates the four working directories below
  `C:\GIT_HUB\testing`.
- **SETUP-02** — Replaces an existing working copy completely.
- **SETUP-03** — Does not copy `test_spec.md` or other non-fixture files.
- **SETUP-04** — Does not pause for keyboard input.
- **SETUP-05** — Returns exit code `0` only when all four copies succeed.
- **SETUP-06** — Returns a non-zero exit code when a source is missing, a
  destination cannot be replaced, or a copy is incomplete.
- **SETUP-07** — The suite compares source and destination manifests
  immediately after the copy: relative paths, file sizes, and SHA-256 hashes
  must match.

### 7.2 Bakery installation

The suite must run `install.bat` before launching KiCad. The script must support
a non-interactive mode that:

- **INST-01** — Installs only from the current repository checkout.
- **INST-02** — Removes the previous KiCad 10 Bakery installation.
- **INST-03** — Copies every runtime Python module, `metadata.json`,
  `LICENSE`, and all resources required by the plugin.
- **INST-04** — Does not pause for keyboard input.
- **INST-05** — Returns a non-zero exit code if any required copy fails.
- **INST-06** — After installation, the suite compares the installed runtime
  files with the repository files by relative path and SHA-256 hash. This
  check prevents a functional run from accidentally testing stale code.

## 8. Per-Project Test Procedure

Each fixture must run in isolation from a newly restored working copy.

### 8.1 Baseline

1. **BASE-01** — Record a recursive manifest of the working project.
2. **BASE-02** — Record the contents and hashes of:
   - The `.kicad_pcb` file.
   - Every `.kicad_sch` file.
   - `fp-lib-table`, when present.
   - `sym-lib-table`, when present.
3. **BASE-03** — Record existing files in:
   - `MyLib` and `MyLib.pretty`.
   - `MySym`.
   - `3D Models`.
   - `Data_Sheets`.
   - The project's `*-backups` directory.

### 8.2 Launch

1. **LNCH-01** — Start KiCad 10 PCB Editor directly with the copied PCB path.
2. **LNCH-02** — Wait for the PCB Editor main window and loaded board to
   become responsive.
3. **LNCH-03** — If KiCad presents a legacy-format warning or conversion
   dialog, accept the conversion required to continue in KiCad 10.
4. **LNCH-04** — Eeschema must stay closed during Bakery execution. Bakery's
   `check_schematic_locks` aborts localization if it detects an open schematic
   (a `~*.lck` marker file or an OS-level file lock on a `.kicad_sch` file), so
   the test must not open Eeschema between launching PCB Editor and the Bakery
   run completing.

### 8.3 Run Bakery

1. **RUN-01** — Invoke Bakery from **Tools > External Plugins**.
2. **RUN-02** — Verify the **Bakery Configuration** dialog appears and
   displays the Bakery version from the installed source.
3. **RUN-03** — Verify these default values:

   | Field | Expected value |
   |---|---|
   | Local Footprint Library Name | `MyLib` |
   | Symbol Library Name | `MySymbols` |
   | Symbol Directory Name | `MySym` |
   | 3D Models Directory Name | `3D Models` |
   | Datasheets Directory Name | `Data_Sheets` |

4. **RUN-04** — Select **OK** without changing the values.
5. **RUN-05** — Verify the **Bakery - Localize Libraries** confirmation
   appears.
6. **RUN-06** — Select **Yes**.
7. **RUN-07** — Wait for the **Bakery - Localization Log** dialog.
8. **RUN-08** — Wait until the Close button is enabled or the configured test
   timeout is reached.
9. **RUN-09** — Fail immediately if the Errors pane contains text.
10. **RUN-10** — Verify the **Bakery - Success** dialog appears and contains
    `Localization Complete!`.
11. **RUN-11** — Dismiss the success dialog, capture the log text, and close
    the log dialog.
12. **RUN-12** — Save the board and exit PCB Editor normally.

The default per-project Bakery timeout is five minutes. The timeout must be
configurable without editing test code.

## 9. Required Post-Run Assertions

All assertions apply to every fixture unless identified as conditional.

### 9.1 Process and UI

- **AST-UI-01** — KiCad remains running until the automated close step and
  does not crash.
- **AST-UI-02** — Bakery is present in the External Plugins menu.
- **AST-UI-03** — No Bakery error dialog appears.
- **AST-UI-04** — The Bakery logger reaches `Complete`.
- **AST-UI-05** — The Bakery logger Errors pane is empty.
- **AST-UI-06** — The success dialog is shown.

Warnings do not automatically fail the test, but every warning must be captured
in the result (**AST-UI-07**). Unresolved footprints, symbols, 3D models, or
local files are functional failures even if Bakery reports them as warnings
(**AST-UI-08**).

### 9.2 Project backup

- **AST-BKP-01** — A new archive exists in `<project-name>-backups`.
- **AST-BKP-02** — Its name matches `<project-name>-YYYY-MM-DD_HHMMSS.zip`.
- **AST-BKP-03** — It is a readable ZIP file.
- **AST-BKP-04** — It contains the pre-Bakery PCB and every pre-Bakery
  schematic using paths relative to the project directory.
- **AST-BKP-05** — It does not recursively contain the project's backup
  directory.

### 9.3 Footprint localization

- **AST-FPT-01** — `MyLib.pretty` exists after Bakery completes.
- **AST-FPT-02** — The legacy `MyLib` directory is absent after it has been
  migrated to `MyLib.pretty`.
- **AST-FPT-03** — `fp-lib-table` exists and contains exactly one `MyLib`
  entry whose URI is `${KIPRJMOD}/MyLib.pretty`.
- **AST-FPT-04** — Every non-empty footprint library reference in the PCB and
  schematics that Bakery successfully resolved uses `MyLib:<name>`.
- **AST-FPT-05** — Every referenced `MyLib:<name>` has a matching
  `MyLib.pretty\<name>.kicad_mod` file.
- **AST-FPT-06** — Filename collision handling must not overwrite two
  different source footprints. Renamed targets must be consistently
  referenced by the PCB, schematics, and local library.

### 9.4 Symbol localization

- **AST-SYM-01** — `MySym\MySymbols.kicad_sym` exists and is parseable as a
  KiCad symbol library.
- **AST-SYM-02** — `sym-lib-table` exists and contains exactly one
  `MySymbols` entry whose URI is `${KIPRJMOD}/MySym/MySymbols.kicad_sym`.
- **AST-SYM-03** — Every schematic `lib_id` that Bakery successfully resolved
  uses `MySymbols:<name>`.
- **AST-SYM-04** — Every referenced localized symbol exists in
  `MySym\MySymbols.kicad_sym`.
- **AST-SYM-05** — Embedded symbol definitions and their child units use
  names consistent with the localized symbol name.

### 9.5 3D model localization

- **AST-MDL-01** — `3D Models` exists.
- **AST-MDL-02** — Every 3D model copied by Bakery exists as a regular file
  and has a non-zero size.
- **AST-MDL-03** — Local footprint model references use
  `${KIPRJMOD}/3D Models/<filename>`.
- **AST-MDL-04** — PCB model references for localized footprints use the same
  local paths.
- **AST-MDL-05** — No remaining model reference in a localized footprint or
  corresponding PCB footprint begins with `${KICAD9_`, `${KICAD10_`, or an
  absolute path.
- **AST-MDL-06** — Existing project-local models are preserved and not
  duplicated.

### 9.6 Datasheet localization

- **AST-DS-01** — When at least one valid PDF source is available,
  `Data_Sheets` exists and contains at least one valid, non-empty PDF.
- **AST-DS-02** — Successfully localized datasheet properties use
  `${KIPRJMOD}/Data_Sheets/<filename>`.
- **AST-DS-03** — The same original URL or local path is downloaded or
  copied only once.
- **AST-DS-04** — A failed external download is recorded with its URL and
  reason. Network failures must be distinguishable from invalid Bakery output.
- **AST-DS-05** — Non-PDF URLs and empty datasheet properties may remain
  unlocalized and must not create fake `.pdf` files.

### 9.7 KiCad reopen verification

After filesystem checks, reopen the localized PCB and root schematic in KiCad
10 and verify:

- **AST-RUI-01** — The PCB loads without a parse, rescue, or
  missing-footprint error dialog.
- **AST-RUI-02** — The board contains at least one footprint.
- **AST-RUI-03** — KiCad can display the board and close normally.
- **AST-RUI-04** — Opening the root schematic in KiCad Schematic Editor does
  not show schematic parse, missing symbol library, missing symbol, or rescue
  dialogs.

AST-RUI-04 is mandatory for fixtures whose symbol references are expected to be
fully resolvable after Bakery completes. If a fixture intentionally contains a
known unresolved symbol reference listed in the suite allowlist, the runner may
record AST-RUI-04 as skipped for that fixture only; the static symbol
assertions and known-issue trap assertions remain mandatory so the skipped GUI
open cannot hide an unexpected localization failure.

## 10. Legacy Fixture Assertions

For FT-02 and FT-04:

- **LGC-01** — KiCad 10 must successfully open the KiCad 9-format project.
- **LGC-02** — Bakery must process legacy `${KICAD9_FOOTPRINT_DIR}`,
  `${KICAD9_3DMODEL_DIR}`, and `${KICAD9_SYMBOL_DIR}` inputs when present.
- **LGC-03** — Localized output must not depend on a KiCad 9 installation or
  KiCad 9 environment variables.
- **LGC-04** — Modified project files must remain readable by KiCad 10.
- **LGC-05** — The test must record whether KiCad converted a file format. A
  conversion is expected behavior, not a failure.

## 11. Idempotence Test

Each project must be run through Bakery a second time without restoring it,
in the same KiCad PCB Editor session used for the first run (the project must
remain open with the board loaded; do not relaunch KiCad or reopen the PCB
file between runs). Running the second pass in the same session is what
"content is unchanged after the second run" (below) is measured against —
relaunching KiCad would introduce incidental changes to session-only files
(e.g. `.kicad_prl`) that are not caused by Bakery and would need to be
reclassified as volatile.

The second run must satisfy all normal UI and integrity assertions, plus:

- **IDM-01** — No duplicate `MyLib` or `MySymbols` table entries are added.
- **IDM-02** — No duplicate footprint, symbol, 3D model, or datasheet files
  are created.
- **IDM-03** — Existing localized files are not renamed again.
- **IDM-04** — References remain stable.
- **IDM-05** — A second valid project backup is created.
- **IDM-06** — Excluding expected backup files and KiCad-generated volatile
  files, the project content is unchanged after the second run.
- **IDM-07** — Bakery reports that footprints and symbols are already local,
  or reports zero newly copied footprints and symbols.

Volatile files and fields must be documented in the verifier rather than
ignored with unrestricted directory or text patterns.

## 12. Source Fixture Integrity

**FIX-01** — At the end of the complete suite, regenerate the source fixture
manifests and compare them with their pre-suite manifests. Any changed,
added, or removed file below `Functional Test\Ki-Test * - BackUp` or
`Functional Test\Ki-Test * - Backup` fails the suite.

## 13. Failure Evidence

For each failed test, preserve:

- **FAIL-01** — Test ID, fixture name, and phase.
- **FAIL-02** — KiCad executable path and version.
- **FAIL-03** — Bakery version and installed-file hash manifest.
- **FAIL-04** — Exit codes from both batch files.
- **FAIL-05** — Screenshot of the active KiCad or Bakery window.
- **FAIL-06** — Text from the Bakery Log, Warnings, and Errors panes.
- **FAIL-07** — Window titles and visible modal dialogs.
- **FAIL-08** — Python traceback from the test runner.
- **FAIL-09** — Pre-run and post-run project manifests.
- **FAIL-10** — A file-level diff summary.
- **FAIL-11** — The complete failed working project.

The runner must attempt a normal KiCad shutdown after failure (**FAIL-12**).
It may terminate only the exact process IDs that it started if normal
shutdown times out (**FAIL-13**).

## 14. Test Results

Write these artifacts under a timestamped directory below
`C:\GIT_HUB\testing\results`:

- **RES-01** — `junit.xml`
- **RES-02** — `summary.json`
- **RES-03** — `environment.json`
- **RES-04** — `installed-plugin-manifest.json`
- **RES-05** — One directory per test ID containing manifests, logs, diffs,
  and screenshots

The process exit code must be:

- **RES-06** — `0` when all mandatory tests pass.
- **RES-07** — Non-zero when preflight, setup, installation, UI automation,
  verification, or cleanup integrity fails.

## 15. Acceptance Criteria

The functional suite is complete when one command can:

1. **ACC-01** — Start from any repository working tree state without using
   previously installed Bakery files.
2. **ACC-02** — Restore all four fixtures into `C:\GIT_HUB\testing`.
3. **ACC-03** — Install the current Bakery source into KiCad 10.
4. **ACC-04** — Run Bakery twice on each of the four projects.
5. **ACC-05** — Verify the UI outcome, localized files and references,
   project backup, PCB and schematic KiCad reopen behavior, and idempotence.
6. **ACC-06** — Leave the source fixtures unchanged.
7. **ACC-07** — Return a reliable exit code and produce sufficient artifacts
   to diagnose a failure without rerunning the suite interactively.

## 16. Detailed Test Case Catalog

The cases below are derived directly from Bakery's implemented behavior (not
just its happy path) and supplement the four end-to-end fixture runs in
Section 4. Each case lists its trigger, expected result, the code path it
exercises, and whether it is already reachable through the existing fixtures
or requires a synthetic/injected fixture. Synthetic fixtures must be added
under `Functional Test` following the same immutable-source convention as the
existing four projects (Section 12 applies to them too).

### 16.1 Plugin entry guards (`bakery_plugin.py`)

| TC | Trigger | Expected result | Fixture |
|----|---------|------------------|---------|
| TC-01 | Run Bakery with no board loaded (`pcbnew.GetBoard()` returns falsy) | `ERROR_NO_BOARD` message box shown; no logger window opens; no files touched | Requires launching the Bakery command with PCB Editor in a no-project state (synthetic) |
| TC-02 | Run Bakery on a board that has never been saved to disk | `ERROR_PROJECT_NOT_SAVED` message box shown; no files touched | Requires an unsaved-board scenario (synthetic) |
| TC-03 | Select **Cancel** on the **Bakery Configuration** dialog | Dialog closes; no confirmation dialog, no logger, no backup, no file changes | Any FT-01..04 fixture |
| TC-04 | Enter an empty value, or a value containing `<>:"/\|?*` or a control character, in any config field, then select OK | `validate_library_name` fails; a **Validation Error** message box names the offending field; the Configuration dialog stays open with values retained | Any FT-01..04 fixture |
| TC-05 | Accept valid config, then select **No** on the **Bakery - Localize Libraries** confirmation | Localization aborts; no backup archive, no library changes | Any FT-01..04 fixture |
| TC-06 | A `.kicad_sch` file in the project is open in Eeschema (or otherwise OS-locked) when Bakery runs | `check_schematic_locks` reports the file; logger shows warning + error; a blocking **Schematic Files Locked** message box lists the file; no backup or localization occurs | Requires opening a schematic in Eeschema before running Bakery (synthetic step on any fixture) |

### 16.2 Footprint localization (`footprint_localizer.py`)

| TC | Trigger | Expected result | Fixture |
|----|---------|------------------|---------|
| TC-07 | A PCB/schematic footprint reference already uses the local library nickname (e.g. `MyLib:...`) | `filter_footprints_to_copy` skips it (logged "already in local library"); no duplicate `.kicad_mod` is written; the existing local file is still tracked so its 3D models can be repaired | FT-03/FT-04 (`5V_REG_20A` already references `MyLib:QFN50P350X450X100-20N` and `MyLib:8-PowerVDFN`) |
| TC-08 | A referenced footprint's source library nickname is not in the effective `fp-lib-table` | `find_footprint_library_path` returns `None`; a warning "Could not find library" is logged; the reference is left unmodified; run continues and still succeeds | Requires a fixture with an unresolvable global library nickname (synthetic) |
| TC-09 | The source library is found but the named `.kicad_mod` file is missing from it | Warning "Could not find source for `lib:name`" logged; footprint left unmodified; run continues | Requires a corrupted/pruned global library on the test machine (synthetic) |
| TC-10 | Two different source libraries each contain a footprint with the same base name | Both are copied using `make_localized_item_name(lib, name)`-derived distinct target names; neither file is overwritten; PCB/schematic references point at the correct distinct targets | Requires two same-named footprints from different libraries (synthetic) |
| TC-11 | A footprint's 3D model path is already `${KIPRJMOD}/...` and the file exists | Model is not re-copied; logged "Model is already project-local"; reference unchanged | FT-03/FT-04 (existing `${KIPRJMOD}/3D Models/CSD17307Q5A.step` references) |
| TC-12 | A footprint's 3D model path cannot be resolved (missing env var target or missing file) | `failed_count` increments; a warning is logged; the footprint file's model path for that entry is left unmodified; run does not abort | Requires an unresolvable/missing model path (synthetic) |
| TC-13 | A footprint or 3D model path uses a legacy `${KICAD9_*}` token | Path is normalized/resolved to the `KICAD10_*` equivalent; localized output no longer references any `${KICAD9_*}` or `${KICAD10_*}` token | FT-02/FT-04 (`${KICAD9_3DMODEL_DIR}` present in source `.kicad_pcb`) |

### 16.3 Symbol localization (`symbol_localizer.py`)

| TC | Trigger | Expected result | Fixture |
|----|---------|------------------|---------|
| TC-14 | A referenced symbol has an `(extends "Parent")` clause and the parent is not yet local | The parent is auto-queued and copied into the same local library file; both symbols are renamed with the same `lib:name`-derived prefix; the child's `(extends ...)` is rewritten to the localized parent name | FT-03/FT-04 (`Device:C_Small`, `Device:R_Small_US` in the global KiCad Device library extend base symbols) |
| TC-15 | A parent symbol required by `(extends ...)` is already present in the local library from a prior run | Parent is not recopied or renamed again; child is still localized and its `(extends ...)` still resolves correctly | Second-run pass of FT-03/FT-04 (Section 11) |
| TC-16 | A schematic references a `power:*` symbol (e.g. `power:GND`, `power:VBUS`) | Power symbols are filtered out entirely; never copied, never appear in `MySymbols.kicad_sym`, and remain referenced as `power:*` in schematics | FT-01..04 (all reference `power:GND`; FT-01/02 also reference `power:VBUS`) |
| TC-17 | The local `MySymbols.kicad_sym` file exists but is empty or is not a valid `kicad_symbol_lib` structure | A warning is logged; the file is replaced with a fresh valid library structure instead of crashing; new symbols are still written successfully | Requires a corrupted local symbol library (synthetic) |
| TC-18 | A multi-unit symbol embedded in a schematic (`(symbol "Lib:Name_0_1" ...)` child blocks) is localized | Root definition `(symbol "Lib:Name" ...)` and every child unit `(symbol "Name_x_y" ...)` are renamed consistently to the new local target name via `_rename_embedded_symbol_definitions` | FT-03/FT-04 (`LM25145RGYT` schematic symbol has multiple embedded unit blocks) |

### 16.4 Datasheet localization (`data_sheet_localizer.py`)

| TC | Trigger | Expected result | Fixture |
|----|---------|------------------|---------|
| TC-19 | A `Datasheet` property is empty or `"~"` | Classified `empty`; skipped silently; no file created | FT-01/FT-02 (multiple empty/`~` Datasheet properties) |
| TC-20 | A `Datasheet` property already starts with `${KIPRJMOD}` | Classified `localised`; skipped silently | FT-02 (`Diodes.kicad_sch` already has `${KIPRJMOD}/Data_Sheets/1n4001.pdf`) |
| TC-21 | A `Datasheet` property is a local file path without a `.pdf` extension | Classified `non_pdf`; skipped, logged "Skipping non-PDF local datasheet"; no file created | Requires a non-PDF local datasheet reference (synthetic) |
| TC-22 | The same datasheet URL appears on multiple component instances | Downloaded/copied exactly once; all instances' properties are rewritten to the same local `${KIPRJMOD}/Data_Sheets/<filename>` path | FT-03/FT-04 (`LM25145RGYT` datasheet URL repeats across instances) |
| TC-23 | A datasheet URL is a TI redirect wrapper (`.../suppproductinfo.tsp?...gotoUrl=...`) | `_normalize_download_url` extracts and downloads the direct target URL, not the wrapper | FT-03/FT-04 (`ti.com/general/docs/suppproductinfo.tsp?...gotoUrl=...lm25145`) |
| TC-24 | A datasheet URL is unreachable (DNS failure, timeout, HTTP error) | Download failure is logged with the URL and reason; the property is left unmodified; the overall Bakery run still completes and reports success for everything else | Requires a dead/unreachable URL or simulated network outage (synthetic or environment-injected) |
| TC-25 | A downloaded or copied file does not start with the `%PDF` magic bytes | `_is_valid_pdf`/`_is_valid_pdf_content` rejects it; no `.pdf` file is left in `Data_Sheets`; failure is logged | Requires a URL/path that returns non-PDF content (synthetic) |
| TC-26 | A local datasheet source file is copied, then Bakery is re-run and the destination is already current | `_should_update_file` returns `False`; file is not re-copied; logged "Destination file is up-to-date" | Second-run pass of FT-02 (has a local-file datasheet reference) |
| TC-27 | A local datasheet source file is newer than an already-copied destination | `_should_update_file` returns `True`; destination is overwritten with the newer source | Requires touching the source datasheet's mtime between runs (synthetic) |

### 16.5 Library table management (`library_manager.py`, `utils.update_library_table`)

| TC | Trigger | Expected result | Fixture |
|----|---------|------------------|---------|
| TC-28 | Project has no `fp-lib-table` / `sym-lib-table` before the run | File is created containing exactly one entry for the local library with the correct `${KIPRJMOD}` URI | Requires a fixture with no pre-existing library table (synthetic; FT-01..04 all already ship tables) |
| TC-29 | Project's `fp-lib-table` / `sym-lib-table` already contains unrelated entries | The new local-library entry is appended; pre-existing unrelated entries are preserved unchanged | Requires a table with unrelated entries (synthetic) |
| TC-30 | Bakery is re-run and the local-library entry already exists in the table | Entry is not duplicated (upsert semantics); table is functionally identical to the first-run result | Second-run pass of any FT-01..04 fixture (Section 11) |

### 16.6 Project backup (`backup_manager.py`)

| TC | Trigger | Expected result | Fixture |
|----|---------|------------------|---------|
| TC-31 | Normal first Bakery run | `<project>-backups\<project>-<timestamp>.zip` is created containing every visible project file at relative paths, before any localization changes are applied | Any FT-01..04 fixture |
| TC-32 | Project contains hidden files/directories and a prior `*-backups` directory | Hidden entries and the backup directory itself are excluded from the new archive | FT-01..04 (each already has a `*-backups` directory with a prior archive) |
| TC-33 | Two backups are triggered within the same second (`FileExistsError` path) | The pre-existing archive is left untouched; the error is logged and the run aborts before modifying any project file | Requires forcing two backup attempts within one second, e.g. clock/time-source injection (synthetic) |
| TC-34 | `_find_project_files` finds zero eligible files (e.g. project directory contains only hidden files) | `RuntimeError` is raised and logged; Bakery aborts before creating a partial backup or touching libraries | Requires an all-hidden project directory (synthetic) |

### 16.7 Coverage note

TC-01, TC-02, TC-06, TC-08, TC-09, TC-10, TC-12, TC-17, TC-21, TC-24, TC-25,
TC-27, TC-28, TC-29, TC-33, and TC-34 are not reachable from the four shipped
fixtures alone. Implementers must add small synthetic fixtures (or scripted
environment/network fault injection) for these cases; do not skip them, since
several guard critical data-safety paths (locked-file abort, backup failure
abort, empty-project abort).

## 17. Recommended Implementation Order

1. Add non-interactive, strict-error modes to both batch files.
2. Implement fixture and installed-plugin hash manifests.
3. Implement one FT-01 happy-path UI test.
4. Add static project verification.
5. Add FT-02 through FT-04.
6. Add KiCad PCB and schematic reopen verification.
7. Add second-run idempotence checks.
8. Add screenshots, JUnit XML, JSON reporting, and failure cleanup.
