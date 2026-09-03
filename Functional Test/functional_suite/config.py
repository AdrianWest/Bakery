"""!
@file config.py

@brief Central configuration and path constants for the functional test suite.

@section description_config Detailed Description
Defines every path, timeout, and fixture-matrix constant referenced by the
Bakery functional test suite (see `Functional Test/test_spec.md`, Section 3
and Section 4). Keeping these values in one module lets every component
resolve paths and defaults consistently and lets the timeout be overridden
without editing test code, as required by Section 8.2.

@section notes_config Notes
- Paths are expressed with `pathlib.Path` for correct Windows separator
  handling.
- `FIXTURE_MATRIX` mirrors the table in Section 4 of `test_spec.md` exactly;
  update both together if fixtures change.
"""

import os
from dataclasses import dataclass
from pathlib import Path

# Repository and fixture locations (test_spec.md, Section 3).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FUNCTIONAL_TEST_DIR = REPO_ROOT / "Functional Test"
SYNTHETIC_FIXTURES_DIR = FUNCTIONAL_TEST_DIR / "functional_suite" / "synthetic_fixtures"
SETUP_SCRIPT = REPO_ROOT / "start-manuel-test.bat"
INSTALL_SCRIPT = REPO_ROOT / "install.bat"
PLUGINS_SOURCE_DIR = REPO_ROOT / "plugins"

# Test workspace and results (test_spec.md, Section 3 and Section 14).
TESTING_WORKSPACE = REPO_ROOT.parent / "testing"
RESULTS_ROOT = TESTING_WORKSPACE / "results"

# Installed plugin location (test_spec.md, Section 3).
KICAD_VERSION = "10.0"
INSTALLED_PLUGIN_DIR = (
    Path(os.environ.get("USERPROFILE", str(Path.home())))
    / "Documents"
    / "KiCad"
    / KICAD_VERSION
    / "scripting"
    / "plugins"
    / "Bakery"
)

# Default per-project Bakery timeout in seconds (test_spec.md, Section 8.3).
# Overridable via the BAKERY_TEST_TIMEOUT_SECONDS environment variable so the
# suite never requires editing test code to change it.
DEFAULT_BAKERY_TIMEOUT_SECONDS = 5 * 60


def get_bakery_timeout_seconds() -> int:
    """
    @brief Resolve the configured Bakery run timeout

    @return Timeout in seconds, taken from BAKERY_TEST_TIMEOUT_SECONDS when
        set and valid, otherwise DEFAULT_BAKERY_TIMEOUT_SECONDS
    """
    raw_value = os.environ.get("BAKERY_TEST_TIMEOUT_SECONDS")
    if not raw_value:
        return DEFAULT_BAKERY_TIMEOUT_SECONDS
    try:
        return int(raw_value)
    except ValueError:
        return DEFAULT_BAKERY_TIMEOUT_SECONDS


@dataclass(frozen=True)
class Fixture:
    """!
    @brief Describes one functional-test fixture (test_spec.md, Section 4).

    @section attributes Attributes
    - test_id (str): Test identifier such as "FT-01".
    - source_name (str): Immutable source directory name under
      `Functional Test`.
    - working_name (str): Working copy directory name under
      `C:\\GIT_HUB\\testing` (the `- Backup`/`- BackUp` suffix removed).
    - pcb_file (str): Name of the fixture's `.kicad_pcb` file.
    - intent (str): Short description of what the fixture exercises.
    - is_legacy (bool): True for KiCad 9-format compatibility fixtures.
    """

    test_id: str
    source_name: str
    working_name: str
    pcb_file: str
    intent: str
    is_legacy: bool


# Fixture matrix mirrors test_spec.md Section 4 exactly.
FIXTURE_MATRIX = (
    Fixture(
        test_id="FT-01",
        source_name="Ki-Test 01-10 - Backup",
        working_name="Ki-Test 01-10",
        pcb_file="Ki-Test.kicad_pcb",
        intent="KiCad 10 basic/global-library localization",
        is_legacy=False,
    ),
    Fixture(
        test_id="FT-02",
        source_name="Ki-Test 01-09 - Backup",
        working_name="Ki-Test 01-09",
        pcb_file="Ki-Test.kicad_pcb",
        intent="KiCad 9-format project opened and localized by KiCad 10",
        is_legacy=True,
    ),
    Fixture(
        test_id="FT-03",
        source_name="Ki-Test 02-10 - BackUp",
        working_name="Ki-Test 02-10",
        pcb_file="5V_REG_20A.kicad_pcb",
        intent="KiCad 10 mixed local/global project and existing-assets handling",
        is_legacy=False,
    ),
    Fixture(
        test_id="FT-04",
        source_name="Ki-Test 02-09 - BackUp",
        working_name="Ki-Test 02-09",
        pcb_file="5V_REG_20A.kicad_pcb",
        intent="KiCad 9-format mixed project, legacy paths, and existing-assets handling",
        is_legacy=True,
    ),
)

# Default library configuration values Bakery ships (test_spec.md, RUN-03),
# imported directly from the plugin source so this suite never drifts from
# the shipped defaults.
DEFAULT_LIBRARY_CONFIG = {
    "Local Footprint Library Name": "MyLib",
    "Symbol Library Name": "MySymbols",
    "Symbol Directory Name": "MySym",
    "3D Models Directory Name": "3D Models",
    "Datasheets Directory Name": "Data_Sheets",
}

# Known, intentionally-unresolvable items baked into the shipped fixtures to
# exercise Bakery's warning/error handling (TC-08/09/12/24/25). These are not
# environment gaps: the suite must keep confirming Bakery still detects and
# reports each one the same way on every run (regression protection), while
# still failing on any *new*, previously-unseen unresolved item. Extend this
# table as additional known-bad items are identified per fixture; each entry
# is matched as a case-sensitive substring against the relevant reference
# text (a 3D model path/filename, or a datasheet URL).
EXPECTED_FIXTURE_ISSUES = {
    "FT-01": {
        # Global "Button_Switch_THT" footprint references a 3D model file
        # that does not exist on disk; Bakery leaves the reference
        # unmodified and logs a warning (observed during suite validation).
        "unresolved_models": ("KSA_Tactile_SPST.step",),
        # Dead/blocked datasheet URLs and one URL that serves non-PDF
        # content; Bakery logs each failure and leaves the property
        # unmodified (observed during suite validation).
        "datasheet_failures": (
            "seielect.com/catalog/SEI-CF_CFM.pdf",
            "ohmite.com/assets/images/res-ox-oy-rev-7.23.pdf",
            "digikey.com/en/models/823904",
        ),
        "unresolved_symbols": (),
    },
    # FT-02..04 entries below were confirmed against live runs on
    # 2026-09-02 (results/2026-09-02_155539). Each datasheet URL listed
    # here was observed failing with a logged HTTP 403/404 while Bakery
    # left the reference unmodified. None of these fixtures produced an
    # unresolved 3D model reference (AST-MDL-05 was clean for all three),
    # so their "unresolved_models" tuples stay empty.
    "FT-02": {
        "unresolved_models": (),
        # Both blocked with HTTP 403 (Forbidden).
        "datasheet_failures": (
            "digikey.com/en/models/462974",
            "phoenixcontact.com/us/products/1843240/pdf",
        ),
        # This fixture ships a half-localized project: sym-lib-table
        # declares MySymbols at ${KIPRJMOD}/MySym/MySymbols.kicad_sym and
        # every schematic symbol references it, but neither the MySym
        # directory nor the library file exists (and no copy survives in
        # the fixture's own Ki-Test-backups archive). There is therefore no
        # source library for Bakery to copy these from, so the correct
        # behaviour is to warn and leave them untouched rather than report
        # success - see SymbolLocalizer.copy_symbols.
        "unresolved_symbols": (
            "MySymbols:1N4004",
            "MySymbols:C_US",
            "MySymbols:Conn_01x04",
            "MySymbols:R",
        ),
    },
    "FT-03": {
        "unresolved_models": (),
        # coilcraft/TDK block automated fetches with HTTP 403; the Murata
        # deep-links are permanently dead (HTTP 404).
        "datasheet_failures": (
            "coilcraft.com/en-us/files/datasheet/xal7070",
            "mlcc_automotive_general_en.pdf",
            "GRM155R71C563KA88-01.pdf",
            "GRM155R71C102KA01-01.pdf",
            "GRM155R71H391KA01-01.pdf",
            "GRM155R71C822KA01-01.pdf",
            "GRM1885C2A100JA01-01.pdf",
        ),
        "unresolved_symbols": (),
    },
    # FT-04 is the KiCad-9 counterpart of FT-03 and carries the same board,
    # so it exhibits the identical datasheet failures.
    "FT-04": {
        "unresolved_models": (),
        "datasheet_failures": (
            "coilcraft.com/en-us/files/datasheet/xal7070",
            "mlcc_automotive_general_en.pdf",
            "GRM155R71C563KA88-01.pdf",
            "GRM155R71C102KA01-01.pdf",
            "GRM155R71H391KA01-01.pdf",
            "GRM155R71C822KA01-01.pdf",
            "GRM1885C2A100JA01-01.pdf",
        ),
        "unresolved_symbols": (),
    },
}
# (test_spec.md, Section 11 and Section 12). Documented explicitly instead of
# using an unrestricted glob, per the spec's requirement.
VOLATILE_FILE_SUFFIXES = (
    ".kicad_prl",  # Per-session KiCad UI state, not written by Bakery.
    "fp-info-cache",  # KiCad-maintained footprint metadata cache.
)
