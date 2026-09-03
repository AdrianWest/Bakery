"""!
@file kicad_driver.py

@brief KiCad UI driver for the Bakery functional test suite (COMP-02).

@section description_kicad_driver Detailed Description
Drives KiCad 10 PCB Editor and the Bakery plugin's wxPython dialogs through
`pywinauto`, implementing the launch and run procedures from
`Functional Test/test_spec.md` Section 8 (LNCH-01..04, RUN-01..12).

Two `pywinauto` backends are combined deliberately:
- The `win32` backend reliably finds wx-created dialogs by title and reads
  native `Edit`/`Button` controls (wx maps directly onto them).
- The `uia` backend, reconnected by window handle, is used only to read text
  from the themed `TaskDialog` MessageBoxes (`Bakery - Localize Libraries`
  and `Bakery - Success`), whose text is not exposed as classic `Edit`/
  `Static` window text under `win32`.

@section notes_kicad_driver Notes
- All dialog titles, control orders, and control identifiers used here were
  captured from a real Bakery run against the FT-01 fixture in this
  repository's KiCad 10 installation.
- The Bakery "Close" button on the Localization Log only becomes enabled
  after the "Bakery - Success" MessageBox has been dismissed (see
  `bakery_plugin.py Run()`), so `run_bakery` waits for either window and
  handles the success dialog before the close-enabled wait resolves.
"""

import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from pywinauto import Application
from pywinauto.base_wrapper import ElementNotEnabled
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.timings import TimeoutError as PywinautoTimeoutError

from . import config

CONFIG_DIALOG_TITLE = "Bakery Configuration"
CONFIRM_DIALOG_TITLE = "Bakery - Localize Libraries"
LOG_DIALOG_TITLE_RE = ".*Localization Log.*"

# Timeouts for waiting on Bakery's own dialogs. These are deliberately
# generous: the suite deletes the test workspace before every run, so KiCad
# always starts against a cold project with no fp-info-cache and can spend
# many seconds rebuilding caches while the UI is unresponsive. Tight
# timeouts here surface as spurious RUN-05/RUN-07 failures that look like
# Bakery defects but are really automation races.
DIALOG_WAIT_SECONDS = 60
# How long to keep retrying the External Plugins menu selection while the
# main window is still initializing and reports itself as not enabled.
MENU_READY_TIMEOUT_SECONDS = 60
SUCCESS_DIALOG_TITLE = "Bakery - Success"
MENU_PATH = (
    "Tools -> External Plugins -> "
    "Bakery - Localize Symbols, Footprints, and 3D Models"
)
SCHEMATIC_WINDOW_TITLE_RE = r".*Schematic Editor.*"
SCHEMATIC_BLOCKING_DIALOG_PATTERNS = (
    r".*[Ee]rror.*",
    r".*[Rr]escue.*",
    r".*[Mm]issing.*",
    r".*[Ss]ymbol.*[Ll]ibrar.*",
)

# Config field order matches CONFIG_FIELD_SPECS in plugins/ui_components.py,
# which is also the order pywinauto returns the dialog's Edit controls in.
CONFIG_FIELD_ORDER = (
    "Local Footprint Library Name",
    "Symbol Library Name",
    "Symbol Directory Name",
    "3D Models Directory Name",
    "Datasheets Directory Name",
)

# Known KiCad legacy-project conversion/warning dialog title fragments
# (LNCH-03). Extend this list if a new KiCad release renames the dialog.
LEGACY_CONVERSION_DIALOG_PATTERNS = (
    r".*[Ss]ave.*[Cc]hanges.*",
    r".*[Rr]escue.*",
    r".*[Cc]onvert.*",
    r".*[Ll]egacy.*",
    r".*[Nn]ewer version of KiCad.*",
)


class KicadDriverError(RuntimeError):
    """!
    @brief Raised when KiCad or a Bakery dialog does not behave as expected.
    """


@dataclass
class BakeryRunResult:
    """!
    @brief Everything captured while driving one Bakery run (RUN-01..12).

    @section attributes Attributes
    - config_defaults (dict): Field values read from the Configuration dialog.
    - log_text (str): Full text of the main Log pane.
    - warnings_text (str): Full text of the Warnings pane.
    - errors_text (str): Full text of the Errors pane.
    - success_shown (bool): Whether the Success dialog appeared.
    - success_text (str): Text captured from the Success dialog.
    """

    config_defaults: dict = field(default_factory=dict)
    log_text: str = ""
    warnings_text: str = ""
    errors_text: str = ""
    success_shown: bool = False
    success_text: str = ""


def _read_uia_text(hwnd: int) -> str:
    """
    @brief Read all Text-control content from a themed TaskDialog by handle

    @param hwnd: Native window handle of the dialog
    @return Concatenated text of every UIA Text control found
    """
    app = Application(backend="uia").connect(handle=hwnd)
    window = app.window(handle=hwnd)
    texts = [t.window_text() for t in window.descendants(control_type="Text")]
    return "\n".join(text for text in texts if text)


class KicadDriver:
    """!
    @brief COMP-02: starts PCB Editor and drives the Bakery plugin UI.

    @section methods Methods
    - :py:meth:`~KicadDriver.launch`
    - :py:meth:`~KicadDriver.launch_schematic`
    - :py:meth:`~KicadDriver.run_bakery`
    - :py:meth:`~KicadDriver.save_and_close`
    - :py:meth:`~KicadDriver.close_without_saving`
    - :py:meth:`~KicadDriver.force_close`
    """

    def __init__(self, pcbnew_path: Path):
        """
        @brief Initialize the driver

        @param pcbnew_path: Path to KiCad 10's pcbnew.exe
        """
        self.pcbnew_path = pcbnew_path
        self.process: Optional[subprocess.Popen] = None
        self.app: Optional[Application] = None
        self.main_window = None

    def launch(self, pcb_path: Path, converted_hint: bool = False) -> bool:
        """
        @brief Start PCB Editor against a copied .kicad_pcb file (LNCH-01..03)

        @param pcb_path: Path to the working copy's .kicad_pcb file
        @param converted_hint: True when the fixture is a KiCad 9-format
            project (test_spec.md Section 2), so a conversion dialog is
            expected and must be accepted rather than treated as a failure
        @return True when a legacy conversion dialog was seen and accepted
            (LGC-05 "record whether KiCad converted a file format")

        @throws KicadDriverError if the main window never becomes available
        """
        self.process = subprocess.Popen(
            [str(self.pcbnew_path), str(pcb_path)],
            cwd=str(pcb_path.parent),
        )
        converted = self._handle_startup_dialogs(converted_hint)

        self.app = Application(backend="win32").connect(
            title_re=r".*PCB Editor.*", timeout=60
        )
        self.main_window = self.app.window(title_re=r".*PCB Editor.*")
        self.main_window.wait("exists visible ready", timeout=60)
        return converted

    def launch_schematic(self, schematic_path: Path) -> None:
        """
        @brief Start KiCad Schematic Editor against a copied .kicad_sch file
            and fail if KiCad reports missing libraries or rescue/errors

        @param schematic_path: Path to the working copy's root .kicad_sch file

        @throws KicadDriverError if Eeschema is unavailable, the schematic
            window never becomes available, or a blocking load dialog appears
        """
        eeschema_path = self.pcbnew_path.with_name("eeschema.exe")
        if not eeschema_path.is_file():
            raise KicadDriverError(
                f"AST-RUI-04: KiCad Schematic Editor not found: {eeschema_path}"
            )

        self.process = subprocess.Popen(
            [str(eeschema_path), str(schematic_path)],
            cwd=str(schematic_path.parent),
        )

        deadline = time.monotonic() + 60
        last_dialog = ""
        while time.monotonic() < deadline:
            last_dialog = self._blocking_dialog_text(SCHEMATIC_BLOCKING_DIALOG_PATTERNS)
            if last_dialog:
                raise KicadDriverError(
                    "AST-RUI-04: schematic load showed a blocking dialog: "
                    f"{last_dialog}"
                )

            try:
                self.app = Application(backend="win32").connect(
                    process=self.process.pid, timeout=1
                )
                self.main_window = self.app.window(title_re=SCHEMATIC_WINDOW_TITLE_RE)
                self.main_window.wait("exists visible ready", timeout=1)
                time.sleep(3)
                last_dialog = self._blocking_dialog_text(
                    SCHEMATIC_BLOCKING_DIALOG_PATTERNS
                )
                if last_dialog:
                    raise KicadDriverError(
                        "AST-RUI-04: schematic load showed a blocking dialog: "
                        f"{last_dialog}"
                    )
                return
            except (ElementNotFoundError, PywinautoTimeoutError):
                time.sleep(1)

        raise KicadDriverError(
            "AST-RUI-04: root schematic did not open in KiCad Schematic "
            "Editor within 60s"
        )

    def _blocking_dialog_text(self, title_patterns) -> str:
        """
        @brief Return text for the first blocking dialog owned by this process

        @param title_patterns: Iterable of title regex patterns to inspect
        @return Dialog title and text, or an empty string when none is found
        """
        if self.process is None:
            return ""
        for pattern in title_patterns:
            try:
                app = Application(backend="win32").connect(
                    process=self.process.pid, title_re=pattern, timeout=1
                )
                dialog = app.window(title_re=pattern)
                text = _read_uia_text(dialog.handle)
                if not text:
                    text = "\n".join(
                        child.window_text()
                        for child in dialog.children()
                        if child.window_text()
                    )
                return f"{dialog.window_text()}: {text}"
            except (ElementNotFoundError, PywinautoTimeoutError):
                continue
        return ""

    def _handle_startup_dialogs(self, converted_hint: bool) -> bool:
        """
        @brief Accept a legacy-format conversion dialog if KiCad shows one

        @param converted_hint: Whether this fixture is expected to trigger a
            conversion prompt
        @return True if a matching dialog was found and accepted
        """
        deadline = time.monotonic() + 30
        accepted = False
        while time.monotonic() < deadline:
            try:
                app = Application(backend="win32").connect(
                    title_re=r".*PCB Editor.*", timeout=1
                )
                app.window(title_re=r".*PCB Editor.*").wait(
                    "exists visible ready", timeout=1
                )
                return accepted
            except (ElementNotFoundError, PywinautoTimeoutError):
                pass

            for pattern in LEGACY_CONVERSION_DIALOG_PATTERNS:
                try:
                    dialog_app = Application(backend="win32").connect(
                        title_re=pattern, timeout=1
                    )
                    dialog = dialog_app.window(title_re=pattern)
                    for button_title in ("&Yes", "Yes", "OK", "&OK", "Continue"):
                        try:
                            dialog.child_window(
                                title=button_title, class_name="Button"
                            ).click()
                            accepted = True
                            break
                        except ElementNotFoundError:
                            continue
                except (ElementNotFoundError, PywinautoTimeoutError):
                    continue
            time.sleep(1)

        if not converted_hint and not accepted:
            return False
        return accepted

    def _config_dialog(self):
        """
        @brief Wait for and return the Bakery Configuration dialog

        @return pywinauto window wrapper for the Configuration dialog
        """
        app = Application(backend="win32").connect(
            title=CONFIG_DIALOG_TITLE, timeout=DIALOG_WAIT_SECONDS
        )
        return app.window(title=CONFIG_DIALOG_TITLE)

    def _read_config_defaults(self, dialog) -> dict:
        """
        @brief Read every field value currently shown in the Configuration
            dialog

        @param dialog: Configuration dialog window wrapper
        @return Mapping of CONFIG_FIELD_ORDER label to its current text
        """
        edits = dialog.children(class_name="Edit")
        return {
            label: edit.window_text()
            for label, edit in zip(CONFIG_FIELD_ORDER, edits)
        }

    def _bakery_dialog_present(self) -> bool:
        """
        @brief Report whether a Bakery dialog is already on screen

        Used to detect that the plugin has in fact been launched, even though
        the menu selection that launched it reported an error.

        @return True when the Bakery Configuration or Localization Log window
            can be found
        """
        for kwargs in ({"title": CONFIG_DIALOG_TITLE}, {"title_re": LOG_DIALOG_TITLE_RE}):
            try:
                Application(backend="win32").connect(timeout=1, **kwargs)
                return True
            except (ElementNotFoundError, PywinautoTimeoutError):
                continue
        return False

    def _invoke_plugin_menu(self) -> None:
        """
        @brief Select the Bakery entry from the External Plugins menu exactly
            once

        The main window can report itself as not-enabled for a short period
        while KiCad finishes loading a project and rebuilding its caches,
        which makes an immediate `menu_select` raise `ElementNotEnabled`. A
        busy KiCad can also silently drop the posted menu command. Both are
        automation races rather than Bakery defects, so the selection is
        retried until the Configuration dialog actually appears.

        Retrying is only safe while the plugin has definitely not started.
        `menu_select` can post the menu command and *then* fail (for example
        if the UI thread is busy when pywinauto waits for it to go idle), so
        a blind retry would invoke Bakery a second time and localize the
        project twice in one pass. Every attempt therefore checks for the
        Configuration dialog first and returns as soon as it is present,
        instead of clicking the menu again.

        @throws KicadDriverError if the plugin never starts
        """
        deadline = time.monotonic() + MENU_READY_TIMEOUT_SECONDS
        last_error: Optional[Exception] = None
        while time.monotonic() < deadline:
            if self._bakery_dialog_present():
                return
            try:
                self.main_window.wait("ready", timeout=5)
                self.main_window.set_focus()
                self.main_window.menu_select(MENU_PATH)
            except (ElementNotEnabled, ElementNotFoundError, PywinautoTimeoutError) as exc:
                last_error = exc
                time.sleep(1)
                continue
            # Confirm the command was actually accepted before giving up the
            # attempt; a dropped menu command leaves no dialog behind.
            if self._connect_dialog(timeout=10, title=CONFIG_DIALOG_TITLE) is not None:
                return
        if self._bakery_dialog_present():
            return
        raise KicadDriverError(
            "RUN-01: the Bakery Configuration dialog did not appear within "
            f"{MENU_READY_TIMEOUT_SECONDS}s of selecting the plugin menu entry"
        ) from last_error

    def _connect_dialog(self, timeout: int = 1, **kwargs):
        """
        @brief Try to connect to a window, returning None instead of raising

        @param timeout: Seconds to wait for the window
        @param kwargs: Window selectors passed to Application.connect
        @return Connected Application, or None when not found
        """
        try:
            return Application(backend="win32").connect(timeout=timeout, **kwargs)
        except (ElementNotFoundError, PywinautoTimeoutError):
            return None

    def _click_until_dialog(
        self,
        dialog,
        button_title: str,
        error_message: str,
        **target,
    ):
        """
        @brief Click a dialog button until the expected next window appears

        A single `click()` is not reliable against a busy KiCad: while the
        application rebuilds caches after a cold start its UI thread can drop
        the synthesized mouse input, leaving the suite waiting for a dialog
        that was never triggered. Re-clicking until the expected window shows
        up converts that silent drop into a retry.

        Re-clicking is safe: once the button has been accepted its dialog is
        destroyed, so a further click raises and is treated as "already
        accepted, keep waiting for the target window".

        @param dialog: Window wrapper owning the button to click
        @param button_title: Title of the button to click
        @param error_message: KicadDriverError message used on timeout
        @param target: Window selectors identifying the expected next window
        @return Connected Application for the expected window

        @throws KicadDriverError if the expected window never appears
        """
        deadline = time.monotonic() + DIALOG_WAIT_SECONDS
        while time.monotonic() < deadline:
            try:
                dialog.child_window(title=button_title, class_name="Button").click()
            except (ElementNotFoundError, ElementNotEnabled, PywinautoTimeoutError, RuntimeError):
                # The dialog is already gone, so the click landed earlier.
                pass
            app = self._connect_dialog(timeout=5, **target)
            if app is not None:
                return app
        raise KicadDriverError(error_message)

    def run_bakery(
        self,
        timeout_seconds: Optional[int] = None,
        accept_confirmation: bool = True,
    ) -> BakeryRunResult:
        """
        @brief Invoke Bakery and drive it through completion (RUN-01..11)

        @param timeout_seconds: Maximum time to wait for the Localization Log
            to finish; defaults to config.get_bakery_timeout_seconds()
        @param accept_confirmation: When False, selects No on the
            confirmation dialog and returns immediately (TC-05)
        @return Populated BakeryRunResult

        @throws KicadDriverError if a required dialog never appears
        """
        timeout_seconds = timeout_seconds or config.get_bakery_timeout_seconds()
        result = BakeryRunResult()

        self._invoke_plugin_menu()

        config_dialog = self._config_dialog()
        result.config_defaults = self._read_config_defaults(config_dialog)

        confirm_app = self._click_until_dialog(
            config_dialog,
            "OK",
            "RUN-05: confirmation dialog did not appear",
            title=CONFIRM_DIALOG_TITLE,
        )
        confirm_dialog = confirm_app.window(title=CONFIRM_DIALOG_TITLE)
        button_title = "&Yes" if accept_confirmation else "&No"

        if not accept_confirmation:
            confirm_dialog.child_window(title=button_title, class_name="Button").click()
            return result

        log_app = self._click_until_dialog(
            confirm_dialog,
            button_title,
            "RUN-07: Localization Log dialog did not appear",
            title_re=LOG_DIALOG_TITLE_RE,
        )
        log_dialog = log_app.window(title_re=LOG_DIALOG_TITLE_RE)

        self._wait_for_completion(log_dialog, result, timeout_seconds)
        self._capture_log_panes(log_dialog, result)
        log_dialog.child_window(title="Close", class_name="Button").click()
        # Wait for the log window to actually disappear. A lingering dialog
        # would otherwise be mistaken for an already-running plugin by the
        # next invocation's menu guard, which would skip the menu selection
        # and leave the second run waiting on a dialog that never opens.
        close_deadline = time.monotonic() + DIALOG_WAIT_SECONDS
        while time.monotonic() < close_deadline:
            if self._connect_dialog(timeout=1, title_re=LOG_DIALOG_TITLE_RE) is None:
                break
            time.sleep(1)
        return result

    def _wait_for_completion(self, log_dialog, result: BakeryRunResult, timeout_seconds: int) -> None:
        """
        @brief Wait until the Close button is enabled, handling the Success
            dialog if it appears first (RUN-08..10)

        @param log_dialog: Localization Log window wrapper
        @param result: BakeryRunResult to populate with success dialog data
        @param timeout_seconds: Maximum time to wait

        @throws KicadDriverError if the timeout elapses before Close is
            enabled
        """
        close_button = log_dialog.child_window(title="Close", class_name="Button")
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                success_app = Application(backend="win32").connect(
                    title=SUCCESS_DIALOG_TITLE, timeout=1
                )
                success_dialog = success_app.window(title=SUCCESS_DIALOG_TITLE)
                result.success_shown = True
                result.success_text = _read_uia_text(success_dialog.handle)
                success_dialog.child_window(title="OK", class_name="Button").click()
            except (ElementNotFoundError, PywinautoTimeoutError):
                pass

            try:
                if close_button.is_enabled():
                    return
            except Exception:
                pass
            time.sleep(1)

        raise KicadDriverError(
            f"RUN-08: Bakery did not complete within {timeout_seconds}s"
        )

    def _capture_log_panes(self, log_dialog, result: BakeryRunResult) -> None:
        """
        @brief Read the Log, Warnings, and Errors pane text (RUN-09, RUN-11)

        @param log_dialog: Localization Log window wrapper
        @param result: BakeryRunResult to populate
        """
        edits = log_dialog.children(class_name="Edit")
        if len(edits) >= 3:
            result.log_text = edits[0].window_text()
            result.warnings_text = edits[1].window_text()
            result.errors_text = edits[2].window_text()

    def save_and_close(self) -> None:
        """
        @brief Save the board and close PCB Editor normally (RUN-12)
        """
        self.main_window.set_focus()
        self.main_window.type_keys("^s")
        time.sleep(2)
        self.main_window.close()
        if self.process:
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass

    def close_without_saving(self) -> None:
        """
        @brief Close an editor window without intentionally writing files
        """
        if self.main_window is not None:
            self.main_window.close()
        if self.process:
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                for button_title in (
                    "&No",
                    "No",
                    "Don't Save",
                    "Do&n't Save",
                    "Discard",
                ):
                    try:
                        app = Application(backend="win32").connect(
                            process=self.process.pid,
                            title_re=r".*[Ss]ave.*",
                            timeout=1,
                        )
                        app.window(title_re=r".*[Ss]ave.*").child_window(
                            title=button_title, class_name="Button"
                        ).click()
                        break
                    except (
                        ElementNotFoundError,
                        ElementNotEnabled,
                        PywinautoTimeoutError,
                    ):
                        continue
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass

    def force_close(self) -> None:
        """
        @brief Terminate the exact PID this driver started (FAIL-12/FAIL-13)

        Attempts a normal window close first; only terminates the tracked
        process if that does not succeed within a short grace period.
        """
        try:
            if self.main_window is not None:
                self.main_window.close()
                time.sleep(3)
        except Exception:
            pass
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()


def classify_error_lines(errors_text: str) -> List[str]:
    """
    @brief Split the Errors pane into lines that are not network/datasheet
        download failures

    Reconciles test_spec.md RUN-09 / AST-UI-05 ("Errors pane must be empty")
    with ENV-06 and AST-DS-04, which require unreachable external datasheets
    to be reported separately from a genuine Bakery application failure.
    Only lines that do not match a known download-failure pattern are
    returned; any returned line still fails the test per RUN-09.

    @param errors_text: Full text of the Errors pane
    @return Error lines that are not classified as datasheet network
        failures
    """
    network_patterns = (
        r"HTTP [Ee]rror \d+",
        r"URLError",
        r"timed? ?out",
        r"downloading https?://",
        r"[Nn]etwork",
        r"[Cc]onnection (refused|reset|error)",
        # TC-24/TC-25: an unreachable or non-PDF external datasheet is a
        # content/network problem, not a Bakery application bug (ENV-06,
        # AST-DS-04), and every such line names the offending URL.
        r"not a valid PDF.*https?://",
        r"[Dd]ownload(ed|ing)?.*https?://",
    )
    combined = re.compile("|".join(network_patterns))
    lines = [line for line in errors_text.splitlines() if line.strip()]
    return [line for line in lines if not combined.search(line)]
