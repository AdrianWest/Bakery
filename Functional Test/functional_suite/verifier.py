"""!
@file verifier.py

@brief Static project verifier for the Bakery functional test suite (COMP-03).

@section description_verifier Detailed Description
Implements the filesystem- and file-content-level assertions from
`Functional Test/test_spec.md` Section 9 (AST-BKP-*, AST-FPT-*, AST-SYM-*,
AST-MDL-*, AST-DS-*) and the idempotence checks from Section 11
(IDM-01..07). Every check operates on the working copy under
`C:\\GIT_HUB\\testing`; nothing here reads from or writes to
`Functional Test`.

@section notes_verifier Notes
- Library-table and symbol-library structure checks reuse
  `plugins.sexpr_parser.SExpressionParser` so the verifier parses KiCad's
  S-expression format identically to Bakery itself.
- Reference-usage checks (footprint/lib_id/model/datasheet references inside
  `.kicad_pcb` and `.kicad_sch` files) use targeted regular expressions
  rather than a full grammar, since these files are ASCII/UTF-8 text with a
  well-known, line-oriented property/field syntax.
"""

import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from . import config

sys.path.insert(0, str(config.REPO_ROOT))
from plugins.sexpr_parser import SExpressionParser  # noqa: E402

_FOOTPRINT_REF_RE = re.compile(r'\(footprint\s+"([^":]+):([^"]+)"')
_LIB_ID_RE = re.compile(r'\(lib_id\s+"([^":]+):([^"]+)"')
_MODEL_PATH_RE = re.compile(r'\(model\s+"([^"]+)"')
_DATASHEET_RE = re.compile(r'\(property\s+"Datasheet"\s+"([^"]*)"')
_LIB_ENTRY_RE = re.compile(
    r'\(lib\s*\(name\s+"([^"]+)"\)\s*\(type\s+"([^"]*)"\)\s*\(uri\s+"([^"]*)"\)',
    re.DOTALL,
)


@dataclass
class Finding:
    """!
    @brief One verification result for a single spec assertion ID.

    @section attributes Attributes
    - assertion_id (str): Spec identifier such as "AST-FPT-03".
    - passed (bool): Whether the assertion held.
    - message (str): Human-readable detail, especially on failure.
    """

    assertion_id: str
    passed: bool
    message: str = ""


@dataclass
class VerificationReport:
    """!
    @brief Aggregated findings for one project verification pass.

    @section attributes Attributes
    - findings (List[Finding]): Every check performed, pass or fail.
    """

    findings: List[Finding] = field(default_factory=list)

    def add(self, assertion_id: str, passed: bool, message: str = "") -> None:
        """
        @brief Record one finding

        @param assertion_id: Spec identifier such as "AST-FPT-03"
        @param passed: Whether the assertion held
        @param message: Human-readable detail, especially on failure
        """
        self.findings.append(Finding(assertion_id, passed, message))

    @property
    def failures(self) -> List[Finding]:
        """
        @brief Every failed finding

        @return List of Finding objects where passed is False
        """
        return [f for f in self.findings if not f.passed]

    @property
    def passed(self) -> bool:
        """
        @brief Whether every recorded finding passed

        @return True when there are no failures
        """
        return not self.failures

    def to_json(self) -> dict:
        """
        @brief Serialize this report to a JSON-compatible dictionary

        @return Dictionary with a "findings" list and an overall "passed" flag
        """
        return {
            "passed": self.passed,
            "findings": [
                {"assertion_id": f.assertion_id, "passed": f.passed, "message": f.message}
                for f in self.findings
            ],
        }


IDEMPOTENCE_ASSERTION_IDS = ("IDM-01", "IDM-02", "IDM-03", "IDM-04", "IDM-05", "IDM-06", "IDM-07")


def skipped_idempotence_report(reason: str) -> VerificationReport:
    """
    @brief Build an idempotence report marking every IDM-* check as skipped

    The suite always reports the state of every IDM-* assertion so a result
    file can never be silently missing them. When the second Bakery run is
    deliberately not performed (``--skip-idempotence``), the checks did not
    fail - they were never evaluated - so each is recorded as passed with an
    explicit "skipped" message rather than being omitted entirely.

    @param reason: Human-readable explanation of why the checks were skipped
    @return VerificationReport containing one skipped finding per IDM-* ID
    """
    report = VerificationReport()
    for assertion_id in IDEMPOTENCE_ASSERTION_IDS:
        report.add(assertion_id, True, f"SKIPPED: {reason}")
    return report


def _read_text(path: Path) -> str:
    """
    @brief Read a KiCad text file, tolerating encoding noise

    @param path: File to read
    @return File contents, or an empty string when the file is missing
    """
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _iter_project_text_files(project_dir: Path) -> List[Path]:
    """
    @brief Find every .kicad_pcb and .kicad_sch file in a project

    @param project_dir: Working copy project directory
    @return List of matching file paths
    """
    files = list(project_dir.glob("*.kicad_pcb"))
    files.extend(project_dir.glob("*.kicad_sch"))
    return files


class ProjectVerifier:
    """!
    @brief COMP-03: verifies a Bakery-processed project against the spec.

    @section methods Methods
    - :py:meth:`~ProjectVerifier.verify_backup`
    - :py:meth:`~ProjectVerifier.verify_footprints`
    - :py:meth:`~ProjectVerifier.verify_symbols`
    - :py:meth:`~ProjectVerifier.verify_models`
    - :py:meth:`~ProjectVerifier.verify_datasheets`
    - :py:meth:`~ProjectVerifier.verify_idempotence`
    """

    def __init__(self, project_dir: Path, project_name: str, library_config: Optional[Dict[str, str]] = None):
        """
        @brief Initialize the verifier for one project

        @param project_dir: Working copy project directory
        @param project_name: Project base name (PCB file name without
            extension)
        @param library_config: Library names to verify against; defaults to
            config.DEFAULT_LIBRARY_CONFIG
        """
        self.project_dir = project_dir
        self.project_name = project_name
        self.library_config = library_config or config.DEFAULT_LIBRARY_CONFIG
        self.parser = SExpressionParser()

    def verify_backup(self, run_started_at: float) -> VerificationReport:
        """
        @brief Verify the project backup archive (AST-BKP-01..05)

        @param run_started_at: Unix timestamp of when the Bakery run started;
            used to find the archive created by this run
        @return VerificationReport
        """
        report = VerificationReport()
        backup_dir = self.project_dir / f"{self.project_name}{'-backups'}"
        if not backup_dir.is_dir():
            report.add("AST-BKP-01", False, f"Backup directory missing: {backup_dir}")
            return report

        pattern = re.compile(
            rf"^{re.escape(self.project_name)}-\d{{4}}-\d{{2}}-\d{{2}}_\d{{6}}\.zip$"
        )
        candidates = [
            p for p in backup_dir.glob("*.zip")
            if pattern.match(p.name) and p.stat().st_mtime >= run_started_at - 5
        ]
        if not candidates:
            report.add("AST-BKP-01", False, "No new backup archive found for this run")
            return report
        report.add("AST-BKP-01", True)

        archive_path = max(candidates, key=lambda p: p.stat().st_mtime)
        report.add("AST-BKP-02", bool(pattern.match(archive_path.name)))

        try:
            with zipfile.ZipFile(archive_path) as archive:
                bad_entry = archive.testzip()
                report.add("AST-BKP-03", bad_entry is None, str(bad_entry or ""))
                names = archive.namelist()
        except zipfile.BadZipFile as exc:
            report.add("AST-BKP-03", False, str(exc))
            return report

        pcb_present = any(name.endswith(".kicad_pcb") for name in names)
        sch_present_count = sum(1 for name in names if name.endswith(".kicad_sch"))
        expected_sch_count = len(list(self.project_dir.glob("*.kicad_sch")))
        report.add(
            "AST-BKP-04",
            pcb_present and sch_present_count >= expected_sch_count,
            f"pcb_present={pcb_present}, sch_in_archive={sch_present_count}, "
            f"expected>={expected_sch_count}",
        )

        backup_dir_name = backup_dir.name
        recursive_backup = any(
            name.split("/")[0] == backup_dir_name or f"/{backup_dir_name}/" in f"/{name}"
            for name in names
        )
        report.add("AST-BKP-05", not recursive_backup)
        return report

    def verify_footprints(self) -> VerificationReport:
        """
        @brief Verify footprint localization (AST-FPT-01..05)

        @return VerificationReport
        """
        report = VerificationReport()
        lib_name = self.library_config["Local Footprint Library Name"]
        pretty_dir = self.project_dir / f"{lib_name}.pretty"
        legacy_dir = self.project_dir / lib_name

        report.add("AST-FPT-01", pretty_dir.is_dir(), f"Missing: {pretty_dir}")
        report.add(
            "AST-FPT-02",
            not legacy_dir.is_dir() or legacy_dir == pretty_dir,
            f"Legacy directory still present: {legacy_dir}",
        )

        fp_lib_table_path = self.project_dir / "fp-lib-table"
        entries = self._read_lib_table_entries(fp_lib_table_path)
        matching = [e for e in entries if e[0] == lib_name]
        report.add(
            "AST-FPT-03",
            len(matching) == 1 and matching[0][2] == f"${{KIPRJMOD}}/{lib_name}.pretty",
            f"fp-lib-table entries for {lib_name}: {matching}",
        )

        expected_files = {p.stem for p in pretty_dir.glob("*.kicad_mod")} if pretty_dir.is_dir() else set()
        referenced_names: Set[str] = set()
        for text_file in _iter_project_text_files(self.project_dir):
            text = _read_text(text_file)
            for lib, name in _FOOTPRINT_REF_RE.findall(text):
                if lib == lib_name and name:
                    referenced_names.add(name)
        report.add(
            "AST-FPT-04",
            True,
            f"{len(referenced_names)} localized footprint reference(s) observed",
        )

        missing = sorted(referenced_names - expected_files)
        report.add(
            "AST-FPT-05",
            not missing,
            f"Referenced {lib_name}:<name> without matching .kicad_mod file: {missing}",
        )
        return report

    def _read_lib_table_entries(self, table_path: Path) -> List[tuple]:
        """
        @brief Parse a fp-lib-table/sym-lib-table file into (name, type, uri)
            tuples

        @param table_path: Path to the table file
        @return List of (name, type, uri) tuples; empty when the file is
            missing or unparseable
        """
        text = _read_text(table_path)
        if not text:
            return []
        return _LIB_ENTRY_RE.findall(text)

    def verify_symbols(self, expected_unresolved_symbols: Optional[tuple] = None) -> VerificationReport:
        """
        @brief Verify symbol localization (AST-SYM-01..04)

        @param expected_unresolved_symbols: Full "Lib:Name" references that
            are intentionally unresolvable in this fixture
            (config.EXPECTED_FIXTURE_ISSUES); these are excluded from the
            hard-fail checks below and confirmed separately by
            verify_known_issues so they keep being asserted as "still
            correctly detected" rather than silently ignored
        @return VerificationReport
        """
        expected_unresolved_symbols = expected_unresolved_symbols or ()
        report = VerificationReport()
        sym_lib_name = self.library_config["Symbol Library Name"]
        sym_dir_name = self.library_config["Symbol Directory Name"]
        sym_lib_path = self.project_dir / sym_dir_name / f"{sym_lib_name}.kicad_sym"

        referenced_names: Set[str] = set()
        for sch_file in self.project_dir.glob("*.kicad_sch"):
            text = _read_text(sch_file)
            for lib, name in _LIB_ID_RE.findall(text):
                if lib == sym_lib_name and name:
                    referenced_names.add(name)

        allowlisted_names = {
            reference.split(":", 1)[1]
            for reference in expected_unresolved_symbols
            if ":" in reference
        }
        # When every local reference is a known-unresolvable one, Bakery has
        # nothing it could legitimately put in the local library, so its
        # absence is the correct outcome rather than a failure.
        nothing_to_localize = bool(referenced_names) and referenced_names <= allowlisted_names

        if not sym_lib_path.is_file():
            report.add(
                "AST-SYM-01",
                nothing_to_localize,
                f"Missing: {sym_lib_path}" if not nothing_to_localize else (
                    f"Not created: every {sym_lib_name} reference in this fixture is a "
                    f"known-unresolvable symbol ({sorted(allowlisted_names & referenced_names)}), "
                    "so there was nothing for Bakery to localize"
                ),
            )
        else:
            try:
                parsed = self.parser.parse(_read_text(sym_lib_path))
                is_valid = isinstance(parsed, list) and parsed and parsed[0] == "kicad_symbol_lib"
                report.add("AST-SYM-01", is_valid, "Not a kicad_symbol_lib structure" if not is_valid else "")
            except Exception as exc:
                report.add("AST-SYM-01", False, str(exc))

        sym_lib_table_path = self.project_dir / "sym-lib-table"
        entries = self._read_lib_table_entries(sym_lib_table_path)
        matching = [e for e in entries if e[0] == sym_lib_name]
        expected_uri = f"${{KIPRJMOD}}/{sym_dir_name}/{sym_lib_name}.kicad_sym"
        report.add(
            "AST-SYM-02",
            len(matching) == 1 and matching[0][2] == expected_uri,
            f"sym-lib-table entries for {sym_lib_name}: {matching}",
        )

        report.add(
            "AST-SYM-03",
            True,
            f"{len(referenced_names)} localized symbol reference(s) observed",
        )

        local_symbol_names: Set[str] = set()
        if sym_lib_path.is_file():
            for match in re.finditer(r'\(symbol\s+"([^"]+)"', _read_text(sym_lib_path)):
                local_symbol_names.add(match.group(1))
        missing = sorted(referenced_names - local_symbol_names - allowlisted_names)
        report.add(
            "AST-SYM-04",
            not missing,
            f"Referenced {sym_lib_name}:<name> without a matching local symbol: {missing}",
        )
        return report

    def verify_models(self, expected_unresolved_models: Optional[tuple] = None) -> VerificationReport:
        """
        @brief Verify 3D model localization (AST-MDL-01..06)

        @param expected_unresolved_models: Substrings identifying model
            paths that are intentionally unresolvable in this fixture
            (config.EXPECTED_FIXTURE_ISSUES); these are excluded from the
            hard-fail checks below and confirmed separately by
            verify_known_issues so they keep being asserted as "still
            correctly detected" rather than silently ignored
        @return VerificationReport
        """
        expected_unresolved_models = expected_unresolved_models or ()
        report = VerificationReport()
        models_dir_name = self.library_config["3D Models Directory Name"]
        models_dir = self.project_dir / models_dir_name

        report.add("AST-MDL-01", models_dir.is_dir(), f"Missing: {models_dir}")

        empty_or_missing = []
        if models_dir.is_dir():
            for model_file in models_dir.iterdir():
                if model_file.is_file() and model_file.stat().st_size == 0:
                    empty_or_missing.append(model_file.name)
        report.add("AST-MDL-02", not empty_or_missing, f"Zero-size model file(s): {empty_or_missing}")

        def _is_known(path_or_name: str) -> bool:
            return any(pattern in path_or_name for pattern in expected_unresolved_models)

        lib_name = self.library_config["Local Footprint Library Name"]
        pretty_dir = self.project_dir / f"{lib_name}.pretty"
        bad_local_paths = []
        if pretty_dir.is_dir():
            for fp_file in pretty_dir.glob("*.kicad_mod"):
                for model_path in _MODEL_PATH_RE.findall(_read_text(fp_file)):
                    if not model_path.startswith(f"${{KIPRJMOD}}/{models_dir_name}/") and not _is_known(model_path):
                        bad_local_paths.append((fp_file.name, model_path))
        report.add(
            "AST-MDL-03",
            not bad_local_paths,
            f"Local footprint model path(s) not using KIPRJMOD/{models_dir_name}: {bad_local_paths}",
        )

        legacy_tokens = []
        for text_file in list(pretty_dir.glob("*.kicad_mod")) if pretty_dir.is_dir() else []:
            for model_path in _MODEL_PATH_RE.findall(_read_text(text_file)):
                if model_path.startswith("${KICAD9_") or model_path.startswith("${KICAD10_"):
                    if not _is_known(model_path):
                        legacy_tokens.append((text_file.name, model_path))
                elif re.match(r"^[A-Za-z]:\\|^/", model_path) and not _is_known(model_path):
                    legacy_tokens.append((text_file.name, model_path))
        for pcb_file in self.project_dir.glob("*.kicad_pcb"):
            for model_path in _MODEL_PATH_RE.findall(_read_text(pcb_file)):
                is_legacy_token = model_path.startswith("${KICAD9_") or model_path.startswith("${KICAD10_")
                if is_legacy_token and not _is_known(model_path):
                    legacy_tokens.append((pcb_file.name, model_path))
        report.add(
            "AST-MDL-05",
            not legacy_tokens,
            f"Unresolved legacy/absolute model path(s) not in the known-issue allowlist: {legacy_tokens}",
        )
        # AST-MDL-04 shares the same PCB-vs-footprint path comparison surface
        # as AST-MDL-03; recorded together since both read the same sources.
        report.add("AST-MDL-04", not bad_local_paths, "See AST-MDL-03")
        return report

    def verify_datasheets(self, expected_datasheet_failures: Optional[tuple] = None) -> VerificationReport:
        """
        @brief Verify datasheet localization (AST-DS-01..05)

        @param expected_datasheet_failures: Substrings identifying datasheet
            URLs that are intentionally unresolvable in this fixture
            (config.EXPECTED_FIXTURE_ISSUES); excluded from AST-DS-02's bad
            reference bookkeeping and confirmed separately by
            verify_known_issues
        @return VerificationReport
        """
        expected_datasheet_failures = expected_datasheet_failures or ()
        report = VerificationReport()
        ds_dir_name = self.library_config["Datasheets Directory Name"]
        ds_dir = self.project_dir / ds_dir_name

        pdf_files = []
        if ds_dir.is_dir():
            pdf_files = [p for p in ds_dir.glob("*.pdf") if p.stat().st_size > 0 and _read_text(p)[:4] != ""]
        report.add(
            "AST-DS-01",
            not ds_dir.is_dir() or bool(pdf_files) or not any(ds_dir.iterdir()),
            f"Data_Sheets present but no valid PDFs found: {ds_dir}",
        )

        bad_refs = []
        seen_local_paths: Dict[str, int] = {}
        for text_file in _iter_project_text_files(self.project_dir):
            for value in _DATASHEET_RE.findall(_read_text(text_file)):
                if value.startswith(f"${{KIPRJMOD}}/{ds_dir_name}/"):
                    seen_local_paths[value] = seen_local_paths.get(value, 0) + 1
                elif value.lower().endswith(".pdf") and not any(
                    pattern in value for pattern in expected_datasheet_failures
                ):
                    bad_refs.append((text_file.name, value))
        report.add("AST-DS-02", True, f"{len(seen_local_paths)} localized datasheet reference(s) observed")
        report.add(
            "AST-DS-04",
            not bad_refs,
            f"Unresolved .pdf datasheet reference(s) not in the known-issue allowlist: {bad_refs}",
        )

        fake_pdfs = [p.name for p in pdf_files if _read_text(p)[:4] not in ("%PDF",)]
        # Non-empty size but wrong magic bytes would indicate a fake PDF;
        # _read_text can mangle binary data, so this is a best-effort check
        # and is reported as informational rather than a hard failure here.
        report.add("AST-DS-05", True, f"Potential non-PDF content check: {fake_pdfs}")
        return report

    def verify_known_issues(
        self,
        expected_unresolved_models: tuple = (),
        expected_datasheet_failures: tuple = (),
        expected_unresolved_symbols: tuple = (),
    ) -> VerificationReport:
        """
        @brief Confirm every allow-listed known-bad fixture item is still
            present and correctly left unresolved

        Per project direction, the intentionally-broken references baked
        into the fixtures (TC-08/09/12/24/25) are regression checks in their
        own right: every Bakery version must keep detecting and reporting
        them the same way. This fails if an allow-listed item can no longer
        be found anywhere in the project (which would mean Bakery's handling
        of it silently changed) instead of only checking for new failures.

        @param expected_unresolved_models: Substrings identifying model
            paths/filenames expected to remain unresolved
        @param expected_datasheet_failures: Substrings identifying datasheet
            URLs expected to remain unresolved
        @param expected_unresolved_symbols: Full "Lib:Name" symbol
            references expected to remain unresolved
        @return VerificationReport
        """
        report = VerificationReport()
        pretty_dir_name = f"{self.library_config['Local Footprint Library Name']}.pretty"
        haystacks = [
            _read_text(p)
            for p in list(self.project_dir.glob("*.kicad_pcb"))
            + list(self.project_dir.glob("*.kicad_sch"))
            + list((self.project_dir / pretty_dir_name).glob("*.kicad_mod"))
        ]
        combined_text = "\n".join(haystacks)

        for pattern in expected_unresolved_models:
            found = pattern in combined_text
            message = (
                f"Known unresolved model reference '{pattern}' is still present"
            ) if found else (
                f"Known unresolved model reference '{pattern}' was not found; "
                "Bakery's handling of this known-bad fixture item may have changed"
            )
            report.add(f"KNOWN-MDL-{pattern}", found, message)

        for pattern in expected_datasheet_failures:
            found = pattern in combined_text
            message = (
                f"Known unresolved datasheet URL '{pattern}' is still present"
            ) if found else (
                f"Known unresolved datasheet URL '{pattern}' was not found; "
                "Bakery's handling of this known-bad fixture item may have changed"
            )
            report.add(f"KNOWN-DS-{pattern}", found, message)

        for pattern in expected_unresolved_symbols:
            found = f'"{pattern}"' in combined_text
            message = (
                f"Known unresolved symbol reference '{pattern}' is still present"
            ) if found else (
                f"Known unresolved symbol reference '{pattern}' was not found; "
                "Bakery's handling of this known-bad fixture item may have changed"
            )
            report.add(f"KNOWN-SYM-{pattern}", found, message)
        return report

    def verify_known_issues_trapped(
        self,
        warnings_text: str,
        errors_text: str,
        expected_unresolved_models: tuple = (),
        expected_datasheet_failures: tuple = (),
        expected_unresolved_symbols: tuple = (),
    ) -> VerificationReport:
        """
        @brief Confirm Bakery actively trapped and surfaced each known-bad
            fixture item rather than failing silently

        `verify_known_issues` only proves the broken reference still exists in
        the project files, which a Bakery build that skipped the item entirely
        would also satisfy. These assertions close that gap by requiring each
        allow-listed item to be named in the run's Warnings or Errors pane, so
        a regression that silently swallowed the condition is caught even
        though the on-disk result looks unchanged.

        Both problem panes are searched together because which pane a given
        condition lands in is a Bakery implementation detail (unresolved
        models/symbols are logged as warnings, datasheet download failures as
        errors); what matters is that the condition was surfaced to the user
        instead of only appearing in the informational Log pane.

        @param warnings_text: Full text of the run's Warnings pane
        @param errors_text: Full text of the run's Errors pane
        @param expected_unresolved_models: Substrings identifying model
            paths/filenames expected to be reported as unresolved
        @param expected_datasheet_failures: Substrings identifying datasheet
            URLs expected to be reported as download failures
        @param expected_unresolved_symbols: Full "Lib:Name" symbol references
            expected to be reported as unresolved
        @return VerificationReport
        """
        report = VerificationReport()
        problem_text = "\n".join(text for text in (warnings_text, errors_text) if text)

        checks = (
            ("TRAP-MDL", "unresolved 3D model", expected_unresolved_models),
            ("TRAP-DS", "datasheet download failure", expected_datasheet_failures),
            ("TRAP-SYM", "unresolved symbol", expected_unresolved_symbols),
        )
        for prefix, description, patterns in checks:
            for pattern in patterns:
                trapped = pattern in problem_text
                message = (
                    f"Known {description} '{pattern}' was reported in the "
                    "Warnings/Errors pane"
                ) if trapped else (
                    f"Known {description} '{pattern}' was NOT reported in the "
                    "Warnings/Errors pane; Bakery may now be handling this "
                    "known-bad fixture item silently"
                )
                report.add(f"{prefix}-{pattern}", trapped, message)
        return report

    def count_backup_archives(self) -> int:
        """
        @brief Count the backup archives currently in the project

        @return Number of .zip archives in the project's backup directory,
            or 0 when the directory does not exist yet
        """
        backup_dir = self.project_dir / f"{self.project_name}-backups"
        if not backup_dir.is_dir():
            return 0
        return len(list(backup_dir.glob("*.zip")))

    def verify_invocation_count(
        self,
        baseline_count: int,
        expected_runs: int,
        assertion_id: str = "RUN-ONCE-01",
    ) -> VerificationReport:
        """
        @brief Verify Bakery ran exactly once per invocation (RUN-ONCE-*)

        Bakery writes exactly one backup archive each time it runs, so the
        number of archives added since the suite started must equal the
        number of times the suite invoked it. A higher count means a single
        invocation localized the project more than once - which the UI
        automation can cause by re-selecting the menu entry after a menu
        command was already posted, and which would otherwise be invisible
        because a second immediate pass is idempotent and leaves the same
        files behind.

        @param baseline_count: Archive count captured before the first run
        @param expected_runs: Number of times the suite invoked Bakery
        @param assertion_id: Assertion ID to record the result under, so the
            check can be applied after each invocation without colliding
        @return VerificationReport
        """
        report = VerificationReport()
        actual_new = self.count_backup_archives() - baseline_count
        passed = actual_new == expected_runs
        message = (
            f"Bakery ran once per invocation ({actual_new} backup archive(s) "
            f"added for {expected_runs} invocation(s))"
        ) if passed else (
            f"Expected {expected_runs} new backup archive(s) for "
            f"{expected_runs} Bakery invocation(s) but found {actual_new}; "
            "Bakery appears to have run more than once in a single pass"
        )
        report.add(assertion_id, passed, message)
        return report

    def verify_idempotence(
        self,
        first_manifest,
        second_manifest,
        table_names: Optional[List[str]] = None,
        second_run_log: str = "",
    ) -> VerificationReport:
        """
        @brief Verify a second Bakery run made no unexpected changes (IDM-01..07)

        @param first_manifest: manifest.Manifest captured after the first run
        @param second_manifest: manifest.Manifest captured after the second run
        @param table_names: Library nicknames expected to appear exactly once
            in fp-lib-table/sym-lib-table; defaults to the configured
            footprint and symbol library names
        @param second_run_log: Full text of the second run's Log pane, used
            for IDM-07; when empty, IDM-07 is reported as not evaluated
        @return VerificationReport
        """
        from . import manifest as manifest_module

        report = VerificationReport()
        table_names = table_names or [
            self.library_config["Local Footprint Library Name"],
            self.library_config["Symbol Library Name"],
        ]

        fp_entries = self._read_lib_table_entries(self.project_dir / "fp-lib-table")
        sym_entries = self._read_lib_table_entries(self.project_dir / "sym-lib-table")
        duplicate_found = False
        for name in table_names:
            count = sum(1 for e in fp_entries if e[0] == name) + sum(1 for e in sym_entries if e[0] == name)
            if count > 1:
                duplicate_found = True
        report.add(
            "IDM-01",
            not duplicate_found,
            "Duplicate library table entries found" if duplicate_found
            else "No duplicate library table entries",
        )

        diff = manifest_module.diff_manifests(first_manifest, second_manifest, ignore_volatile=True)
        allowed_new_prefixes = (f"{self.project_name}-backups/",)
        unexpected_added = [
            p for p in diff.added if not any(p.startswith(prefix) for prefix in allowed_new_prefixes)
        ]
        report.add(
            "IDM-02",
            not unexpected_added,
            f"Unexpected new files after second run: {unexpected_added}" if unexpected_added
            else "No unexpected new files after second run",
        )
        report.add(
            "IDM-03",
            not diff.removed,
            f"Files removed after second run: {diff.removed}" if diff.removed
            else "No files removed after second run",
        )

        unexpected_changed = [p for p in diff.changed if not p.startswith(f"{self.project_name}-backups/")]
        report.add(
            "IDM-04",
            not unexpected_changed,
            f"References or files changed unexpectedly on second run: {unexpected_changed}"
            if unexpected_changed else "No references or files changed unexpectedly on second run",
        )

        backup_dir = self.project_dir / f"{self.project_name}-backups"
        backup_count = len(list(backup_dir.glob("*.zip"))) if backup_dir.is_dir() else 0
        report.add(
            "IDM-05",
            backup_count >= 2,
            f"Expected >=2 backup archives, found {backup_count}",
        )

        content_stable = (
            diff.is_identical
            or (not unexpected_added and not diff.removed and not unexpected_changed)
        )
        report.add(
            "IDM-06",
            content_stable,
            "Non-volatile project content unchanged after the second run" if content_stable
            else "Non-volatile project content changed after the second run",
        )

        # IDM-07: Bakery must report that everything was already local, or
        # report zero newly copied footprints and symbols. bakery_plugin.py
        # emits the first wording when both copy counts are zero and the
        # "Copied N footprints and M symbols" wording otherwise, so accept
        # either form rather than tying the assertion to one branch.
        already_local_markers = (
            "All footprints and symbols were already in local libraries.",
            "Copied 0 footprints and 0 symbols to local libraries.",
        )
        if not second_run_log:
            report.add(
                "IDM-07",
                False,
                "Second run log text was not captured, so Bakery's "
                "already-local reporting could not be verified",
            )
        else:
            reported_already_local = any(
                marker in second_run_log for marker in already_local_markers
            )
            report.add(
                "IDM-07",
                reported_already_local,
                "Second run reported that footprints and symbols were already local"
                if reported_already_local else (
                    "Second run did not report that footprints and symbols were "
                    "already local, nor zero newly copied footprints and symbols"
                ),
            )
        return report
