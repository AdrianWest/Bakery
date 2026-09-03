# Bakery - KiCad Plugin - AI Coding Agent Instructions

## Project Overview

Bakery is a KiCad 10 plugin that localizes all external project resources into
project-local libraries and folders.

**Purpose**: Copy global KiCad symbols, footprints, 3D models, and datasheets
into the project so the design is portable and no longer depends on a user's
global KiCad library installation.

**Current target**: KiCad 10.x only. Bakery accepts legacy KiCad 9 path
variables in project files as input, but it must not discover, install to, or
run against KiCad 8/9 at runtime.

**Tech Stack**

- Python 3.x from KiCad's embedded Python runtime
- KiCad `pcbnew` Python API for board, footprint, and 3D model operations
- Direct S-expression parsing/editing for schematics, symbol libraries, and
  library tables
- wxPython for dialogs and progress UI

## Operating Context and Instruction Precedence

These repository rules apply to Bakery development in this repo. They are meant to be read alongside the platform/tooling instructions that control the execution environment, but they take precedence for code style, testing, and KiCad-specific behavior in this project.

- Treat this as a repository-specific coding guide for Bakery, not a general-purpose template for unrelated projects.
- Prefer direct inspection and editing for small, single-file, or single-feature tasks.
- Use parallel or delegated work only for genuinely independent research or long-running tasks that benefit from a separate context.
- Do not broaden the task beyond Bakery-specific behavior unless a change is required to complete the requested work safely.
- Keep fixes surgical: the default is to edit the minimal relevant files and validate with the smallest existing test command that checks the changed behavior.

## Architecture

```text
Bakery KiCad Plugin
├── Plugin entry point
│   └── plugins/bakery_plugin.py
├── Shared localizer behavior
│   └── plugins/base_localizer.py
├── Project backup creation
│   └── plugins/backup_manager.py
├── Footprint and 3D model localization
│   └── plugins/footprint_localizer.py
├── Symbol localization
│   └── plugins/symbol_localizer.py
├── Datasheet localization
│   └── plugins/data_sheet_localizer.py
├── Library-table and path management
│   └── plugins/library_manager.py
├── S-expression parsing/serialization
│   └── plugins/sexpr_parser.py
├── UI components
│   └── plugins/ui_components.py
├── Constants and user-facing strings
│   └── plugins/constants.py
└── Shared utilities
    └── plugins/utils.py
```

### Major Components

- **Plugin Core** (`plugins/bakery_plugin.py`): KiCad `ActionPlugin`
  implementation. Coordinates backup, footprint, symbol, datasheet, board save,
  and completion UI.
- **Backup Manager** (`plugins/backup_manager.py`): Creates mandatory
  KiCad-compatible timestamped ZIP backups in `<project>-backups` before any
  localization changes are made.
- **Footprint Localizer** (`plugins/footprint_localizer.py`): Scans PCB and
  schematics, copies footprints, localizes 3D models, updates footprint/model
  references, and keeps repeat runs safe.
- **Symbol Localizer** (`plugins/symbol_localizer.py`): Copies schematic symbols
  into a local `.kicad_sym`, updates references, and warns about dangling local
  symbol references instead of reporting false success.
- **Datasheet Localizer** (`plugins/data_sheet_localizer.py`): Downloads or
  copies PDF datasheets and rewrites references to `${KIPRJMOD}` paths in
  symbols, schematics, and PCB files.
- **Library Manager** (`plugins/library_manager.py`): Resolves KiCad path
  variables and updates `fp-lib-table`/`sym-lib-table`.
- **S-Expression Parser** (`plugins/sexpr_parser.py`): Parses and serializes
  KiCad S-expression files.
- **UI Components** (`plugins/ui_components.py`): Configuration dialog, progress
  logger, completion dialog, banners, Help button, and support QR/button UI.

## Current User-Facing Behavior

- Bakery must create a KiCad-compatible project ZIP backup before making
  changes. If backup creation fails, localization must stop before scanning or
  writing project files.
- Backups are restored through KiCad Project Manager:
  **File** > **Unarchive Project...**.
- The configuration dialog includes fields for local footprint library, symbol
  library, symbol directory, 3D model directory, and datasheets directory.
- The configuration dialog includes a **Help** button that opens
  `https://github.com/AdrianWest/Bakery`.
- The completion dialog includes the localization summary, a support QR code,
  a support message, and a **Buy me a coffee** button.
- GitHub README support links must use GitHub-compatible HTML/images, not
  `<script>` tags, because GitHub strips scripts from README rendering.

## Project-Specific Conventions

### Code Style

- Follow PEP 8 for Python code.
- Class names: `PascalCase` (for example, `BakeryPlugin`, `SymbolLocalizer`).
- Functions and methods: `snake_case` (for example, `localize_symbols`,
  `copy_footprint`).
- Constants: `UPPER_SNAKE_CASE` (for example, `PLUGIN_VERSION`,
  `DEFAULT_LOCAL_LIB_NAME`).
- Preserve KiCad API method names as provided by KiCad, such as `GetBoard()` and
  `GetFootprints()`.
- Prefer small helper methods when a workflow grows, but avoid broad rewrites
  outside the task.
- Keep user-facing strings in `plugins/constants.py` when they are reused or are
  part of plugin behavior.
- These Bakery-specific rules take priority. Where this file does not define a
  coding standard, follow the Google Python Style Guide:
  https://google.github.io/styleguide/pyguide.html

### Documentation Style

Use Doxygen-compatible docstrings for all modules, classes, functions, and
methods.

**File/module docstring**

```python
"""!
@file example_file.py

@brief Short file description.

@section description_main Detailed Description
Longer explanation of the file's role.

@section notes_main Notes
- Any special notes or constraints.
"""
```

**Function docstring**

```python
def copy_footprint(source_path, dest_path, footprint_name):
    """
    @brief Copy a footprint from a source library to a project library

    @param source_path: Absolute path to source .kicad_mod file
    @param dest_path: Absolute path to destination .pretty folder
    @param footprint_name: Footprint name being copied
    @return True if the copy succeeds, False otherwise
    @throws IOError if the source file cannot be read
    """
```

**Class docstring**

```python
class ExampleLocalizer:
    """!
    @brief Short class description.

    @section methods Methods
    - :py:meth:`~ExampleLocalizer.run`

    @section attributes Attributes
    - logger: Logger-like object used for user-visible messages.
    """
```

Common tags: `@file`, `@brief`, `@param`, `@return`, `@throws`,
`@exception`, `@note`, `@see`, and `@section`.

### Error Handling

- Never crash KiCad. Catch exceptions at plugin boundaries and show
  user-friendly wx dialogs for fatal errors.
- Do not swallow write, parser, path-resolution, or reference-update failures.
  Propagate or surface them so Bakery does not report partial localization as
  success.
- Avoid broad `except Exception` except at top-level plugin/test isolation
  boundaries where the error is logged or reported.
- KiCad API calls can fail depending on project/editor state; guard them and
  log useful context.
- Respect file lock checks and modification-time rechecks before replacing
  schematics or symbol libraries.
- Use atomic replacement writes for modified KiCad text files where the existing
  code pattern does so.

### Localization Safety

- Keep path safety checks for any path derived from project files or user
  configuration.
- Use `${KIPRJMOD}` for project-local references.
- Preserve collision-safe naming with stable source hashes for symbols,
  footprints, 3D models, and datasheets.
- Preserve repeat-run safety: running Bakery again on an already-localized
  project must not duplicate files, overwrite unrelated files, or revert local
  3D model paths back to global paths.
- Do not rewrite PCB/schematic references unless the corresponding local library
  table update succeeded.
- Already-local symbols are only safe to skip when the referenced symbol exists
  in a readable local symbol library.

## Development Workflows

### Install Locally

```powershell
# From repository root
.\install.bat

# Script-friendly install used by functional tests
.\install.bat /NonInteractive
```

Manual KiCad 10 installation paths:

- Windows: `%USERPROFILE%\Documents\KiCad\10.0\scripting\plugins\Bakery\`
- Linux: `~/.kicad/10.0/scripting/plugins/Bakery/`
- macOS: `~/Library/Preferences/kicad/10.0/scripting/plugins/Bakery/`

After changing plugin files, close KiCad completely and reopen it so KiCad loads
the updated Python modules.

### Run Bakery

1. Open a KiCad project and its PCB in **PCB Editor**.
2. Use the toolbar Bakery icon or **Tools** > **External Plugins** >
   **Bakery - Localize Symbols, Footprints, and 3d Models**.
3. Configure local library/folder names.
4. Confirm localization and review the log/warnings/errors panes.

## Testing

### Unit Tests

Run the unit test suite from the repository root:

```powershell
python "Unit Test\run_tests.py"
python "Unit Test\run_tests.py" --verbose
python "Unit Test\run_tests.py" --list
python "Unit Test\run_tests.py" --coverage
```

`--coverage` requires:

```powershell
python -m pip install coverage
```

Unit tests mock KiCad/wx APIs where needed. Keep tests focused and update them
when behavior changes.

### Functional Tests

The Windows functional suite drives a real KiCad 10 UI with `pywinauto`.

Install prerequisites:

```powershell
python -m pip install pywinauto pywin32 psutil
```

Run from repository root:

```powershell
python "Functional Test\functional_suite\run_functional_tests.py"
python "Functional Test\functional_suite\run_functional_tests.py" --fixtures FT-01,FT-03
python "Functional Test\functional_suite\run_functional_tests.py" --skip-idempotence --skip-reopen
```

The suite:

1. Verifies KiCad 10 and test environment preflight checks.
2. Cleans `C:\GIT_HUB\testing` while preserving prior `results`.
3. Restores fixture projects with `start-manuel-test.bat`.
4. Installs Bakery with `install.bat /NonInteractive`.
5. Drives the config dialog, confirmation, progress logger, and success dialog.
6. Verifies localized files, backups, repeat-run safety, and KiCad reopen.
7. Writes artifacts under `C:\GIT_HUB\testing\results\<timestamp>\`.

Network/datasheet failures that are known fixture issues are classified and
reported separately; unexpected localization failures should fail the suite.

## Packaging and Release Notes

- `install.bat` copies every runtime plugin module plus `plugins\resources\*`
  into the KiCad 10 plugin directory.
- `create_release.bat` must include any runtime resource added under
  `plugins\resources`.
- Root `resources\` is for README/repository display assets.
- Runtime UI assets needed by KiCad must also exist under `plugins\resources`.
- Keep README, changelog/release notes, metadata, install script, and release
  script aligned when adding user-visible features or runtime resources.

## Integration Points

### KiCad Python API (`pcbnew`)

- Used for board access, footprints, 3D model references, and board saves.
- Import inside plugin runtime with `import pcbnew`.
- API docs: https://docs.kicad.org/doxygen-python/
- Be careful with SWIG containers. For example, editing a 3D model object
  returned from a vector can require assigning the modified object back into the
  vector for the change to persist.

### KiCad Schematic and Library Files

- `.kicad_sch`, `.kicad_pcb`, `.kicad_sym`, `fp-lib-table`, and `sym-lib-table`
  use S-expression syntax.
- Schematics are edited as files because the schematic Python API is limited.
- Preserve symbol properties, footprint placement, routing, and project visual
  appearance.

### Useful Documentation

- KiCad Python API: https://docs.kicad.org/doxygen-python/
- KiCad project archive/unarchive:
  https://docs.kicad.org/10.0/en/kicad/kicad.html#project-archive

## Common Tasks

### Adding a New Runtime Image

1. Add README-only images to `resources\`.
2. Add plugin UI images to `plugins\resources\`.
3. Update `create_release.bat` if the release script copies resources
   explicitly.
4. Confirm `install.bat` copies the image through the `plugins\resources\*`
   copy step.
5. Run unit tests; run functional tests if UI flow changed.

### Updating Dialogs

1. Put reusable strings and URLs in `plugins/constants.py`.
2. Implement layout in `plugins/ui_components.py`.
3. Avoid `wx.MessageBox` when the dialog needs images or custom controls.
4. Preserve dialog titles/text used by functional UI automation unless the tests
   are updated at the same time.
5. Run unit tests and, for user-visible flow changes, the functional suite.

### Updating Localization Logic

1. Search for existing helper functions before adding new path, parser, or
   library-table logic.
2. Preserve backup-before-write behavior.
3. Preserve atomic write and lock-check patterns.
4. Add or update unit tests for the changed behavior.
5. Run targeted tests first, then the full unit suite; run functional tests for
   PCB/schematic/UI workflow changes.
