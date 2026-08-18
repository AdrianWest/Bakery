# KiCad 9 to KiCad 10 Migration Plan

## Scope and Compatibility Policy

This work creates a **KiCad 10-only** version of Bakery. The upgraded plugin must use KiCad 10 scripting APIs, library paths, environment variables, and package metadata. It must not discover or load KiCad 8 or KiCad 9 installations at runtime.

Users who need KiCad 9 support must install the existing KiCad 9-compatible Bakery release. Do not alter its published package metadata or release artifacts.

KiCad 9 project files remain valid migration inputs. Bakery may normalize a versioned path token embedded in an input file, such as `${KICAD9_FOOTPRINT_DIR}`, to the corresponding KiCad 10 token. This is input migration, not discovery of or compatibility with a KiCad 9 installation. Bakery must never search KiCad 9 configuration directories or use KiCad 9 environment-variable values as runtime fallbacks.

| Migration area | Risk | Primary files |
|---|---|---|
| KiCad 10 `pcbnew` API and plugin loading | High | `bakery_plugin.py`, `footprint_localizer.py`, `__init__.py` |
| KiCad library lookup and environment variables | High | `library_manager.py`, `symbol_localizer.py`, `utils.py` |
| Symbol-library output format | Medium | `constants.py`, `symbol_localizer.py`, `sexpr_parser.py` |
| Package and release metadata | Medium | `plugins/metadata.json`, `metadata.json` |
| Installer, documentation, and tests | Medium | `install.bat`, `README.md`, `Unit Test/` |

---

## Checkpoint 1: KiCad 10 Facts and Remaining Probes

The confirmed facts below are sourced from the official KiCad 10.0.5 documentation and Doxygen Python scripting reference (docs.kicad.org, July 2026). Complete every item marked **[VERIFY]** against the installed KiCad 10 build before changing the code that depends on it.

### 1.1 Plugin Interface — CONFIRMED UNCHANGED

`pcbnew.ActionPlugin` still exists in KiCad 10. The complete registration pattern is unchanged:

```python
class MyPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "..."
        self.category = "..."
        self.description = "..."
        self.show_toolbar_button = True

    def Run(self):
        ...

MyPlugin().register()
```

Source: KiCad 10 PCB Editor scripting section, `text_by_date` example.

### 1.2 Documented Core pcbnew Calls — CONFIRMED

The following core calls used by Bakery are documented in KiCad 10:

| Call | Confirmed |
|---|---|
| `pcbnew.GetBoard()` | Yes — scripting examples use it directly |
| `board.GetFootprints()` | Yes — used in official examples |
| `board.Save(filename)` | Yes — documented as a `BOARD` method |
| `fp.GetReference()` | Yes — used in official examples |

**[VERIFY]** Run this in KiCad 10 on a disposable board with at least one footprint. Preserve and restore the original footprint ID so the probe does not modify the test board:

```python
import pcbnew
board = pcbnew.GetBoard()
footprints = list(board.GetFootprints())
fp = footprints[0]
original_id = fp.GetFPID()
print(original_id.GetLibNickname())
print(original_id.GetLibItemName())
try:
  new_id = pcbnew.LIB_ID("TestLib", "TestFP")
  fp.SetFPID(new_id)
  assert str(fp.GetFPID().GetLibNickname()) == "TestLib"
finally:
  fp.SetFPID(original_id)
```

If any getter, setter, accessor, or the `LIB_ID` two-argument constructor fails, record the exception and the verified replacement API before proceeding to Checkpoint 3.

### 1.3 Plugin Loader and Registration — [VERIFY]

`__init__.py` currently searches the active import stack for a `LoadPluginModule` symbol in a `pcbnew` frame. An interactive `inspect.stack()` call cannot validate that behavior because the plugin-import stack has already unwound.

Temporarily log `frame_info.function` and `frame_info.frame.f_globals.get("__name__")` from `__init__.py` while KiCad imports the package, then restart KiCad or use its plugin reload action. Record the actual import context and remove the temporary instrumentation afterward.

Use the observed import context to choose one of these implementations:

- Keep a corrected loader-context guard only if KiCad 10 requires it and the import-time evidence proves a stable condition.
- Otherwise use the documented action-plugin pattern: import `BakeryPlugin` and call `BakeryPlugin().register()` once inside the existing exception boundary.

The acceptance criterion is successful registration exactly once after a clean KiCad 10 startup and after the supported plugin reload workflow, not the presence of a guessed stack-frame name.

### 1.4 Environment Variables — CONFIRMED RENAMED

The official KiCad 10 path variables (source: `docs.kicad.org/10.0/en/kicad/kicad.html`):

| KiCad 10 variable | Purpose |
|---|---|
| `KICAD10_FOOTPRINT_DIR` | Global footprint library root |
| `KICAD10_3DMODEL_DIR` | Global 3D model library root |
| `KICAD10_SYMBOL_DIR` | Global symbol library root |
| `KICAD10_TEMPLATE_DIR` | Project template library root |
| `KICAD10_3RD_PARTY` | Plugin and Content Manager install root |
| `KIPRJMOD` | Current project directory (unchanged) |

**Important:** KiCad 10 automatically resolves `${KICAD9_FOOTPRINT_DIR}` to the value of `${KICAD10_FOOTPRINT_DIR}` inside KiCad's own path substitution engine. This helps open existing KiCad 9 projects in KiCad 10. Bakery's current resolvers use `os.environ`, but values configured in KiCad's Configure Paths dialog are internal to KiCad and are not guaranteed to exist in `os.environ`.

**[VERIFY]** Identify the KiCad 10 Python API that expands KiCad path variables. Test it with `KICAD10_FOOTPRINT_DIR` configured only in KiCad's Configure Paths dialog and deliberately absent from `os.environ`. If no supported expansion API exists, document and test the authoritative KiCad 10 configuration source before implementation. Do not treat an OS environment fixture as proof that normal Configure Paths values work.

### 1.5 Configuration and Library Table Paths — CONFIRMED

Global configuration directory (where `fp-lib-table` and `sym-lib-table` live):

| OS | Path |
|---|---|
| Windows | `%APPDATA%\kicad\10.0\` |
| Linux | `~/.config/kicad/10.0/` |
| macOS | `~/Library/Preferences/kicad/10.0/` |

Source: KiCad 10 first-time setup documentation.

User plugin install path:

| OS | Path |
|---|---|
| Windows | `%USERPROFILE%\Documents\KiCad\10.0\scripting\plugins` |
| Linux | `~/.local/share/kicad/10.0/scripting/plugins` |
| macOS | `~/Documents/KiCad/10.0/scripting/plugins` |

Source: KiCad 10 Python script locations section.

The current `library_manager.py` already probes `%APPDATA%\kicad\{version}\` and `%USERPROFILE%\Documents\KiCad\{version}\`. Both paths are correct for KiCad 10 after the version constant is updated in Checkpoint 2.

### 1.6 Symbol Library File Format — [VERIFY ON DISK]

Open a `.kicad_sym` file saved by KiCad 10 and record the header line values:

```
(kicad_symbol_lib
  (version XXXXXXXX)       <- record this date
  (generator kicad_symbol_editor)
  (generator_version X.X)  <- record this version string
```

Record the KiCad 10 file-format version independently from the application version. Also decide whether Bakery should retain `generator kicad_symbol_editor` or identify itself as the generator; do not copy a generator identity without confirming its intended semantics.

Create a minimal Bakery-generated symbol library, open and save it in KiCad 10, parse the saved result, and compare the header and structures Bakery reads or writes. Reopen the round-tripped library without warnings. Do not assume the complete KiCad 10 symbol schema is unchanged based only on a header comparison.

**Review gate:** Complete the footprint-ID, path-expansion, plugin-loader, and symbol-library probes. Record exact APIs and observed file headers before writing dependent implementation changes.

### 1.7 Risk Mitigations

The three items below carry the highest residual risk in this plan. Each has a mitigation that removes or bounds the risk instead of relying solely on a correct guess:

**Plugin loader/registration (section 1.3):** Do not depend on a guessed stack-frame name, and do not rely on a Python-side module flag alone — a plain module-level flag (for example `_registered = False`) resets whenever the interpreter re-executes `__init__.py` (KiCad's plugin reload action, or any `importlib.reload()`), so it cannot detect a registration that already exists in KiCad itself. Instead, query KiCad's own registered-plugin state before calling `.register()`: enumerate currently registered action plugins (for example via `pcbnew.GetActionPlugins()` or the equivalent confirmed in the KiCad 10 console) and skip registration if an entry with Bakery's identity is already present. Use a module-level flag only as an in-process fast path in addition to this check, never as a replacement for it. The acceptance criterion in section 1.3 is scoped precisely: a clean KiCad 10 startup registers Bakery once, and KiCad's supported plugin reload action results in exactly one visible Bakery entry under `Tools > External Plugins`, with no duplicate and no missing entry.

**Symbol library header (section 1.6):** Implementation work here may proceed without the exact KiCad 10 header values by keeping the existing values as a placeholder, but this is non-blocking for *development*, not for *release*. The round-trip comparison in section 1.6 is a required release gate: it must be executed as a real KiCad 10 GUI open/save/reopen cycle, because no evidence yet exists that KiCad 10 accepts the current header values, and unit tests cannot drive KiCad's GUI save. Perform this check in Checkpoint 6 using an actual KiCad 10 session, capture the before/after `.kicad_sym` header, and update `KICAD_SYMBOL_VERSION`/`KICAD_GENERATOR_VERSION` before the release is packaged in Checkpoint 5. Do not ship a release build with unverified header values.

**Path resolver rewrite (sections 1.4 and 2.2):** Implement resolution as an ordered chain that matches KiCad's documented precedence, not an arbitrary order: (1) an explicitly set OS environment variable, which KiCad's own documentation states overrides internal configuration, (2) the KiCad-native path-expansion API for values set only in Configure Paths, (3) a defined failure (see below) rather than a silently wrong or partially expanded path. This bounds the impact of an incorrect assumption about KiCad's internal API while remaining consistent with how KiCad itself resolves the same variable. Keep the current `os.environ`-based resolution available as the first tier rather than deleting it; add the native-API tier alongside it once confirmed in Checkpoint 1, and only remove either tier after the Checkpoint 2 review gate passes against a real Configure Paths-only setup with no environment variable set.

**Path resolver failure contract:** Define one explicit contract for an unresolved token: the shared resolver raises a dedicated exception (for example `KicadPathResolutionError`) rather than returning `None`, an empty string, or a path that still contains `${...}`. Callers in `footprint_localizer.py`, `symbol_localizer.py`, and `data_sheet_localizer.py` must catch this exception at the localization boundary, log the unresolved variable, surface it through the existing user-facing warning/error UI, and skip only the affected asset rather than producing a partially copied file or a malformed library entry.

---

## Checkpoint 2: Make Compatibility Code KiCad 10 Only

**Files:** `constants.py`, `library_manager.py`, `symbol_localizer.py`, `utils.py`

### 2.1 constants.py — Exact changes

| Constant | Current value | New value | Source |
|---|---|---|---|
| `KICAD_VERSION_PRIMARY` | `"9.0"` | `"10.0"` | Confirmed |
| `KICAD_VERSION_FALLBACK` | `"8.0"` | Remove | KiCad 9 installations are not runtime sources |
| `KICAD_VERSIONS` | `["9.0","8.0"]` | `["10.0"]` (no fallback) | — |
| `ENV_VAR_PREFIX_PRIMARY` | `"KICAD9_"` | `"KICAD10_"` | Confirmed |
| `ENV_VAR_PREFIX_FALLBACK` | `"KICAD8_"` | Remove from active code | — |
| `KICAD_GENERATOR_VERSION` | `"9.0"` | Value from CP1 section 1.6 | Verify |
| `KICAD_SYMBOL_VERSION` | `"20241209"` | Date string from CP1 section 1.6 | Verify |

Define legacy input-token names separately from runtime discovery constants. A legacy token is permitted only as input to normalization; it must not cause an OS environment lookup or configuration-directory search for an older KiCad installation.

### 2.2 Shared KiCad Path Resolution

Path expansion is currently duplicated in `LibraryManager.expand_path()`, `SymbolLocalizer.expand_path()`, and `utils.expand_kicad_path()`. Replace the duplicated behavior with one shared resolver in `utils.py`, then route footprints, symbols, 3D models, and datasheets through it.

The shared resolver must:

1. Expand `${KIPRJMOD}` from the explicit project directory.
2. Normalize supported legacy input tokens (`KICAD9_FOOTPRINT_DIR`, `KICAD9_3DMODEL_DIR`, and `KICAD9_SYMBOL_DIR`) to their `KICAD10_*` equivalents before resolution.
3. Resolve the normalized token using the ordered chain from section 1.7: an explicitly set `os.environ` value first (KiCad's documented override precedence), then the KiCad-native path-expansion API for values set only in Configure Paths (once confirmed in Checkpoint 1), then the failure contract below.
4. Raise the dedicated resolution exception defined in section 1.7 for any token that remains unresolved after both tiers; never return a path that still contains `${...}`.
5. Never read `KICAD9_*` or `KICAD8_*` values from `os.environ` and never search KiCad 9 or KiCad 8 configuration directories.

Remove or delegate `LibraryManager.expand_path()` and `SymbolLocalizer.expand_path()` so they cannot diverge from `utils.expand_kicad_path()`. Keep the `os.environ` resolution tier intact during this transition rather than deleting it — it is the tested fallback described in section 1.7, not dead code.

### 2.3 utils.py and source comments

Document `KICAD10_*` as the runtime variables and the narrowly supported `KICAD9_*` input-token normalization. Remove references that imply Bakery can run against KiCad 8 or KiCad 9 installations.

### 2.4 plugins/metadata.json

| Field | Current | New |
|---|---|---|
| `kicad_version` | `"9.0"` | `"10.0"` |
| `kicad_version_max` | `"9.99"` | `"10.99"` |

**Review gate:** Run the unit tests:
```powershell
python "Unit Test/run_tests.py"
```
All path-construction tests must pass. Deliberately set `KICAD10_FOOTPRINT_DIR` in the test environment and confirm the resolver finds it. Confirm that a `KICAD9_*` path in an existing project file still expands to the KiCad 10 library location.

Also test the normal KiCad Configure Paths case with `KICAD10_*` absent from `os.environ`, using the authoritative mechanism captured in Checkpoint 1. Run the same cases through the footprint, symbol, 3D-model, and datasheet call paths.

---

## Checkpoint 3: Port `pcbnew` and Plugin Registration

**Files:** `bakery_plugin.py`, `footprint_localizer.py`, `__init__.py`

### 3.1 Known-unchanged calls (no code change expected)

The following calls are confirmed unchanged in KiCad 10 by official documentation and scripting examples:

- `pcbnew.ActionPlugin` class interface (`defaults()`, `Run()`, `register()`)
- `pcbnew.GetBoard()`
- `board.GetFootprints()`
- `board.Save(filename)`

Do not alter these unless the **[VERIFY]** step in Checkpoint 1 shows otherwise.

### 3.2 Calls requiring console verification before coding

After completing the **[VERIFY]** step in Checkpoint 1 section 1.2, apply fixes for any of these calls that changed:

- `fp.GetFPID()` / `fp.SetFPID(new_id)` — footprint library ID getter/setter
- `fpid.GetLibNickname()` / `fpid.GetLibItemName()` — ID component accessors
- `pcbnew.LIB_ID(lib_name, fp_name)` — two-argument constructor

If the `LIB_ID` constructor changed, use the signature confirmed in the console. Do not add speculative overloads.

### 3.3 Plugin Registration

Implement the registration guard described in Checkpoint 1 section 1.7: check KiCad's own registered-plugin state before calling `.register()`, rather than depending on a guessed call-stack frame, symbol name, or a Python-side flag alone. Preserve the plugin-boundary exception logging and verify that a clean startup and the supported KiCad plugin reload action each result in exactly one visible Bakery entry, with no duplicate registration and no missed registration.

### 3.4 Symbol library output

`symbol_localizer.py` writes a `.kicad_sym` header using `KICAD_SYMBOL_VERSION`, `KICAD_GENERATOR_NAME`, and `KICAD_GENERATOR_VERSION` from `constants.py`. Apply the header and any parser or serializer changes demonstrated by the round-trip comparison in Checkpoint 1 section 1.6. Do not change structures that the comparison did not show to be different.

**Review gate:** Bakery appears in `Tools > External Plugins` in KiCad 10. Run it on a copy of a test project. Confirm that PCB footprint IDs update to the local library name, the board saves, and reopening the board shows the local library reference intact.

---

## Checkpoint 4: Update Unit Tests

**Files:** All files under `Unit Test/`

### 4.1 Environment variable fixture replacement

The unit tests inject mock KiCad path variables as `os.environ` fixtures. Replace ordinary runtime fixtures with the KiCad 10 equivalents. Retain `KICAD9_*` tokens only in tests explicitly covering legacy input normalization, and never use them as successful runtime environment sources:

- `KICAD9_FOOTPRINT_DIR` → `KICAD10_FOOTPRINT_DIR`
- `KICAD9_3DMODEL_DIR` → `KICAD10_3DMODEL_DIR`
- `KICAD9_SYMBOL_DIR` → `KICAD10_SYMBOL_DIR`
- `KICAD8_*` → remove

Use `grep_search` to locate all occurrences before editing:
```
query: "KICAD9_|KICAD8_", includePattern: "Unit Test/**"
```

### 4.2 Config path strings in tests

Any test that constructs expected library-table paths such as `kicad\9.0\fp-lib-table` must update the version segment to `10.0`.

### 4.3 Added assertions

Add focused assertions that:
- A `KICAD10_*` value resolves correctly to an expected path.
- KiCad 10 global `fp-lib-table` and `sym-lib-table` paths are searched.
- A KiCad 9 project file containing `${KICAD9_3DMODEL_DIR}` is normalized to `${KICAD10_3DMODEL_DIR}` and resolved exclusively through the KiCad 10 mechanism.
- `KICAD9_*` values present in `os.environ` are not used as runtime sources.
- Footprint, symbol, 3D-model, and datasheet callers produce the same resolution result through the shared resolver.
- Generated symbol libraries carry the KiCad 10 header (from Checkpoint 1 section 1.6).

### 4.4 Review gate

```powershell
python "Unit Test/run_tests.py"
```

All tests must pass. No test should reference `KICAD9_*` or `KICAD8_*` variable names unless it is explicitly testing that old variable names in existing project files resolve to KiCad 10 values.

---

## Checkpoint 5: Package the KiCad 10 Release Correctly

**Files:** `plugins/metadata.json`, root `metadata.json`, `install.bat`, release scripts

1. Update `plugins/metadata.json` to declare KiCad 10 only:
   - `kicad_version`: `"10.0"`
   - `kicad_version_max`: the intended KiCad 10 maximum version
   - description text: KiCad 10 only
2. Keep each existing entry in the root `metadata.json` unchanged because it represents a published KiCad 9 release with a fixed archive URL, checksum, and size.
3. After building the new package, add a **new** root-manifest version entry for the KiCad 10 release with its own download URL, SHA-256, download size, install size, and KiCad 10 version range.
4. Verify `install.bat` uses its single `KICAD_VERSION=10.0` setting for every target path.
5. Update active installation and compatibility documentation. Preserve historic release notes as historical records unless they claim current support.

**Review gate:** The installed plugin metadata accepts KiCad 10, while the published KiCad 9 releases remain downloadable and correctly described in the root manifest.

---

## Checkpoint 6: End-to-End KiCad 10 Validation

1. Copy `Functional Test/Ki-Test 02 - BackUp/` to a temporary working directory. Do not run the plugin against the repository fixture.
2. Open the copied project in KiCad 10 and run Bakery.
3. Reopen the resulting board, schematic, and local symbol library in KiCad 10.
4. Perform the symbol-library round-trip required by Checkpoint 1 section 1.6 and section 1.7: open the Bakery-generated `.kicad_sym` file in the KiCad 10 Symbol Editor, save it, reopen it, and confirm no warnings appear. Capture the before/after header and update `KICAD_SYMBOL_VERSION`/`KICAD_GENERATOR_VERSION` in `constants.py` if they differ. This step is a release gate; do not package the release in Checkpoint 5 until it passes.
5. Verify all of the following:
   - [ ] Plugin appears in the KiCad 10 menu and the configuration dialog opens.
   - [ ] No unhandled exceptions appear in KiCad's scripting console.
   - [ ] Local `.pretty` library contains the required footprints.
   - [ ] Local `.kicad_sym` library loads without warnings.
   - [ ] `fp-lib-table` and `sym-lib-table` contain valid local-library entries.
   - [ ] PCB footprint IDs persist after saving and reopening.
   - [ ] Schematic symbol references point to the local library.
   - [ ] 3D models and datasheets use `${KIPRJMOD}` paths where Bakery localizes them.
   - [ ] Backups are created before source files change.
6. Inspect the before-and-after project files and confirm only the intended library references, tables, copied assets, and backup artifacts changed.

**Review gate:** A clean KiCad 10 session can load and use the localized project without external-library errors, and the symbol-library round-trip in step 4 has passed with verified header values.

---

## Final Repository Review

Before release, search the repository for `KiCad 8`, `KiCad 9`, `KICAD8_`, and `KICAD9_`. Classify every remaining match as one of:

- a preserved historic release record;
- an input fixture retained for migration testing; or
- a documented legacy input-token normalization with no older-installation lookup; or
- an outdated active implementation, test, installer, or document that must be changed.

Do not ship code that discovers KiCad 8 or KiCad 9 installations, reads their environment values, or searches their configuration directories in the KiCad 10 release.
