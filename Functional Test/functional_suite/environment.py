"""!
@file environment.py

@brief Environment controller for the Bakery functional test suite (COMP-01).

@section description_environment Detailed Description
Implements the preflight checks from `test_spec.md` Section 5 (ENV-01..08)
and the environment-controller responsibilities from Section 6 (COMP-01):
locating KiCad 10, ensuring no test-owned KiCad process is already running
against a fixture, running fixture preparation and plugin installation, and
recording KiCad/Bakery versions for the result artifacts.

@section notes_environment Notes
- The controller only terminates KiCad processes it can prove it started
  (FAIL-13 / Section 13); it never force-kills arbitrary `pcbnew.exe`
  processes belonging to the interactive user.
- Preflight failures raise `PreflightError` so the runner can fail fast
  (ENV-08) instead of silently skipping fixtures.
"""

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from . import config

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency fallback
    psutil = None


class PreflightError(RuntimeError):
    """!
    @brief Raised when a required preflight condition (ENV-01..08) is not met.
    """


@dataclass
class EnvironmentReport:
    """!
    @brief Snapshot of the verified test environment (written to
    environment.json, RES-03).

    @section attributes Attributes
    - os_version (str): Windows version string.
    - python_version (str): Python interpreter version.
    - kicad_pcbnew_path (str): Resolved path to pcbnew.exe.
    - kicad_version (str): KiCad version string, when discoverable.
    - bakery_source_version (str): PLUGIN_VERSION from the repository source.
    - pywinauto_available (bool): Whether pywinauto could be imported.
    """

    os_version: str
    python_version: str
    kicad_pcbnew_path: str
    kicad_version: str
    bakery_source_version: str
    pywinauto_available: bool

    def to_json(self) -> dict:
        """
        @brief Serialize this report to a JSON-compatible dictionary

        @return Dictionary of every report field
        """
        return {
            "os_version": self.os_version,
            "python_version": self.python_version,
            "kicad_pcbnew_path": self.kicad_pcbnew_path,
            "kicad_version": self.kicad_version,
            "bakery_source_version": self.bakery_source_version,
            "pywinauto_available": self.pywinauto_available,
        }


def find_pcbnew_executable() -> Optional[Path]:
    """
    @brief Locate the KiCad 10 pcbnew.exe (ENV-02)

    @return Path to pcbnew.exe, or None when KiCad 10 cannot be found
    """
    candidates = [
        Path(r"C:\Program Files\KiCad\10.0\bin\pcbnew.exe"),
        Path(r"C:\Program Files (x86)\KiCad\10.0\bin\pcbnew.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    for root in (Path(r"C:\Program Files\KiCad"), Path(r"C:\Program Files (x86)\KiCad")):
        if root.is_dir():
            for match in root.glob("10.0/bin/pcbnew.exe"):
                return match
    return None


def get_kicad_version(pcbnew_path: Path) -> str:
    """
    @brief Read the KiCad file version resource from pcbnew.exe

    @param pcbnew_path: Path to pcbnew.exe
    @return Version string, or "unknown" if it cannot be read
    """
    try:
        import win32api  # type: ignore

        info = win32api.GetFileVersionInfo(str(pcbnew_path), "\\")
        ms = info["FileVersionMS"]
        ls = info["FileVersionLS"]
        return "{}.{}.{}.{}".format(
            win32api.HIWORD(ms), win32api.LOWORD(ms),
            win32api.HIWORD(ls), win32api.LOWORD(ls),
        )
    except Exception:
        return config.KICAD_VERSION


def get_bakery_source_version() -> str:
    """
    @brief Read PLUGIN_VERSION directly from the repository's constants.py

    @return Version string, or "unknown" if it cannot be parsed
    """
    constants_path = config.PLUGINS_SOURCE_DIR / "constants.py"
    text = constants_path.read_text(encoding="utf-8")
    match = re.search(r'PLUGIN_VERSION\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else "unknown"


def find_running_kicad_processes(workspace: Path) -> List[str]:
    """
    @brief Find PCB/Schematic/Symbol/Footprint editor processes touching a
        directory

    Implements the ENV-07 test-environment safeguard: the suite itself
    checks that no editor already has one of the working fixtures open,
    since Bakery only detects locked `.kicad_sch` files.

    @param workspace: Directory tree to check process command lines against
    @return Human-readable descriptions of any matching running process
    """
    if psutil is None:
        return []

    editor_names = {"pcbnew.exe", "eeschema.exe", "pcbnew", "eeschema"}
    workspace_str = str(workspace).lower()
    matches: List[str] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name not in editor_names:
                continue
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if workspace_str in cmdline.lower():
                matches.append(f"{proc.info.get('name')} (pid {proc.info['pid']}): {cmdline}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return matches


def run_batch_script(script_path: Path, *args: str) -> subprocess.CompletedProcess:
    """
    @brief Run a Windows batch script in non-interactive mode and capture output

    @param script_path: Absolute path to the .bat file
    @param args: Additional command-line arguments (the suite always passes
        "/NonInteractive")
    @return Completed process with captured stdout/stderr and return code
    """
    return subprocess.run(
        ["cmd.exe", "/c", str(script_path), *args],
        cwd=str(script_path.parent),
        capture_output=True,
        text=True,
        timeout=120,
    )


class EnvironmentController:
    """!
    @brief COMP-01: locates KiCad, prepares fixtures, installs Bakery, and
        records versions.

    @section methods Methods
    - :py:meth:`~EnvironmentController.run_preflight`
    - :py:meth:`~EnvironmentController.prepare_fixtures`
    - :py:meth:`~EnvironmentController.install_plugin`
    - :py:meth:`~EnvironmentController.build_environment_report`
    """

    def __init__(self):
        """
        @brief Initialize controller state
        """
        self.pcbnew_path: Optional[Path] = None

    def run_preflight(self) -> None:
        """
        @brief Run every ENV-01..08 preflight check before any file is
            changed

        @throws PreflightError if a required condition is not satisfied
        """
        if sys.platform != "win32":
            raise PreflightError("ENV-01: this suite must run on Windows")

        self.pcbnew_path = find_pcbnew_executable()
        if self.pcbnew_path is None:
            raise PreflightError("ENV-02: KiCad 10 PCB Editor was not found")

        if sys.version_info < (3, 8):
            raise PreflightError("ENV-04: Python 3.8+ is required")

        try:
            import pywinauto  # noqa: F401
        except ImportError as exc:
            raise PreflightError(
                "ENV-05: pywinauto is required for UI automation"
            ) from exc

        if not config.FUNCTIONAL_TEST_DIR.is_dir():
            raise PreflightError(
                f"ENV-08: fixture directory not found: {config.FUNCTIONAL_TEST_DIR}"
            )
        for fixture in config.FIXTURE_MATRIX:
            source_dir = config.FUNCTIONAL_TEST_DIR / fixture.source_name
            if not source_dir.is_dir():
                raise PreflightError(
                    f"ENV-08: required fixture missing: {source_dir}"
                )

        stale = find_running_kicad_processes(config.TESTING_WORKSPACE)
        if stale:
            raise PreflightError(
                "ENV-07: an editor is already open against the test "
                "workspace: " + "; ".join(stale)
            )

    def clean_workspace(self) -> List[str]:
        """
        @brief Delete every entry in the test workspace except the results tree

        Guarantees each suite run starts from a known-empty workspace, so
        localized output left behind by an earlier run (or by manual testing)
        can never be mistaken for output produced by the current run. Without
        this, a fixture that Bakery failed to process could still appear
        correct because the previous run's artifacts were already on disk.

        The results tree is preserved so historical result bundles survive.
        Directories are matched by resolved path rather than by name, so only
        the real results root is skipped.

        @return Names of the removed top-level entries, for logging
        @throws PreflightError if the workspace path fails its safety check
        """
        workspace = config.TESTING_WORKSPACE
        if not workspace.exists():
            return []

        resolved = workspace.resolve()
        # Refuse to operate on anything that is not the expected workspace:
        # this method deletes recursively, so a mis-resolved path (for example
        # if the suite were relocated) must fail loudly rather than wipe an
        # unrelated tree.
        if resolved.name != "testing" or resolved == resolved.parent:
            raise PreflightError(
                f"Refusing to clean unexpected test workspace path: {resolved}"
            )
        if resolved == config.REPO_ROOT.resolve():
            raise PreflightError(
                f"Refusing to clean the repository root: {resolved}"
            )

        results_root = config.RESULTS_ROOT.resolve()
        removed: List[str] = []
        for entry in resolved.iterdir():
            if entry.resolve() == results_root:
                continue
            try:
                if entry.is_dir() and not entry.is_symlink():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()
            except OSError as exc:
                raise PreflightError(
                    f"Could not clean test workspace entry {entry}: {exc}"
                ) from exc
            removed.append(entry.name)
        return removed

    def prepare_fixtures(self) -> subprocess.CompletedProcess:
        """
        @brief Run start-manuel-test.bat in non-interactive mode (SETUP-01..06)

        @return Completed process (return code 0 only when all four copies
            succeeded, per SETUP-05/06)

        @throws PreflightError if the setup script itself cannot be found
        """
        if not config.SETUP_SCRIPT.is_file():
            raise PreflightError(f"ENV-08: setup script not found: {config.SETUP_SCRIPT}")
        return run_batch_script(config.SETUP_SCRIPT, "/NonInteractive")

    def install_plugin(self) -> subprocess.CompletedProcess:
        """
        @brief Run install.bat in non-interactive mode (INST-01..05)

        @return Completed process (return code 0 only when installation
            succeeded)

        @throws PreflightError if the install script itself cannot be found
        """
        if not config.INSTALL_SCRIPT.is_file():
            raise PreflightError(f"ENV-08: install script not found: {config.INSTALL_SCRIPT}")
        return run_batch_script(config.INSTALL_SCRIPT, "/NonInteractive")

    def build_environment_report(self) -> EnvironmentReport:
        """
        @brief Build the environment.json report (RES-03)

        @return Populated EnvironmentReport
        """
        try:
            import pywinauto  # noqa: F401
            pywinauto_available = True
        except ImportError:
            pywinauto_available = False

        pcbnew_path = self.pcbnew_path or find_pcbnew_executable()
        return EnvironmentReport(
            os_version=sys.getwindowsversion().__str__() if sys.platform == "win32" else sys.platform,
            python_version=sys.version,
            kicad_pcbnew_path=str(pcbnew_path) if pcbnew_path else "",
            kicad_version=get_kicad_version(pcbnew_path) if pcbnew_path else "unknown",
            bakery_source_version=get_bakery_source_version(),
            pywinauto_available=pywinauto_available,
        )
