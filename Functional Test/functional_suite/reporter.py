"""!
@file reporter.py

@brief Result reporter for the Bakery functional test suite (COMP-04).

@section description_reporter Detailed Description
Writes the artifacts required by `Functional Test/test_spec.md` Section 14:
`junit.xml` (RES-01), `summary.json` (RES-02), `environment.json` (RES-03),
`installed-plugin-manifest.json` (RES-04), and one per-test directory with
manifests, logs, diffs, and screenshots (RES-05).

@section notes_reporter Notes
- JUnit XML is written with the standard library's `xml.etree.ElementTree`
  so the suite has no additional third-party dependency for reporting.
- `TestOutcome.status` uses "passed", "failed", "skipped", and
  "environment" - the last is used for datasheet network failures that
  ENV-06 requires to be distinguished from a genuine Bakery failure.
"""

import json
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TestOutcome:
    """!
    @brief Result of one test case (an FT-xx fixture run or a TC-xx case).

    @section attributes Attributes
    - test_id (str): Identifier such as "FT-01" or "TC-04".
    - name (str): Human-readable test name.
    - status (str): One of "passed", "failed", "skipped", "environment".
    - duration_seconds (float): Wall-clock duration of the test.
    - message (str): Failure summary, empty when passed.
    - details (dict): Structured extra data (findings, warnings, etc.).
    """

    test_id: str
    name: str
    status: str
    duration_seconds: float = 0.0
    message: str = ""
    details: Dict = field(default_factory=dict)


class ResultReporter:
    """!
    @brief COMP-04: accumulates outcomes and writes every result artifact.

    @section methods Methods
    - :py:meth:`~ResultReporter.record`
    - :py:meth:`~ResultReporter.preserve_failure_evidence`
    - :py:meth:`~ResultReporter.write_all`
    - :py:meth:`~ResultReporter.exit_code`
    """

    def __init__(self, results_root: Path):
        """
        @brief Initialize a reporter writing into a timestamped results
            directory

        @param results_root: Parent directory for all results (RES-05); a
            timestamped subdirectory is created under it
        """
        timestamp = time.strftime("%Y-%m-%d_%H%M%S")
        self.run_dir = results_root / timestamp
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.outcomes: List[TestOutcome] = []

    def record(self, outcome: TestOutcome) -> None:
        """
        @brief Record one completed test outcome

        @param outcome: TestOutcome to append to the run's results
        """
        self.outcomes.append(outcome)

    def test_dir(self, test_id: str) -> Path:
        """
        @brief Resolve (and create) the per-test evidence directory (RES-05)

        @param test_id: Test identifier such as "FT-01"
        @return Path to the test's evidence directory
        """
        directory = self.run_dir / test_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def preserve_failure_evidence(
        self,
        test_id: str,
        *,
        kicad_path: str = "",
        kicad_version: str = "",
        bakery_version: str = "",
        setup_exit_code: Optional[int] = None,
        install_exit_code: Optional[int] = None,
        log_text: str = "",
        warnings_text: str = "",
        errors_text: str = "",
        window_titles: Optional[List[str]] = None,
        traceback_text: str = "",
    ) -> None:
        """
        @brief Write the failure evidence bundle for one failed test
            (FAIL-01..11)

        @param test_id: Test identifier such as "FT-01"
        @param kicad_path: KiCad executable path (FAIL-02)
        @param kicad_version: KiCad version string (FAIL-02)
        @param bakery_version: Installed Bakery version (FAIL-03)
        @param setup_exit_code: Exit code from start-manuel-test.bat (FAIL-04)
        @param install_exit_code: Exit code from install.bat (FAIL-04)
        @param log_text: Bakery Log pane text (FAIL-06)
        @param warnings_text: Bakery Warnings pane text (FAIL-06)
        @param errors_text: Bakery Errors pane text (FAIL-06)
        @param window_titles: Visible window/dialog titles (FAIL-07)
        @param traceback_text: Python traceback from the test runner (FAIL-08)
        """
        directory = self.test_dir(test_id)
        evidence = {
            "test_id": test_id,
            "kicad_path": kicad_path,
            "kicad_version": kicad_version,
            "bakery_version": bakery_version,
            "setup_exit_code": setup_exit_code,
            "install_exit_code": install_exit_code,
            "window_titles": window_titles or [],
        }
        (directory / "failure-evidence.json").write_text(
            json.dumps(evidence, indent=2), encoding="utf-8"
        )
        (directory / "bakery-log.txt").write_text(log_text, encoding="utf-8")
        (directory / "bakery-warnings.txt").write_text(warnings_text, encoding="utf-8")
        (directory / "bakery-errors.txt").write_text(errors_text, encoding="utf-8")
        if traceback_text:
            (directory / "traceback.txt").write_text(traceback_text, encoding="utf-8")

    def write_junit_xml(self) -> Path:
        """
        @brief Write junit.xml (RES-01)

        @return Path to the written file
        """
        suite = ET.Element(
            "testsuite",
            name="BakeryFunctionalTests",
            tests=str(len(self.outcomes)),
            failures=str(sum(1 for o in self.outcomes if o.status == "failed")),
            skipped=str(sum(1 for o in self.outcomes if o.status == "skipped")),
        )
        for outcome in self.outcomes:
            case = ET.SubElement(
                suite,
                "testcase",
                name=f"{outcome.test_id}: {outcome.name}",
                classname="BakeryFunctionalTests",
                time=f"{outcome.duration_seconds:.3f}",
            )
            if outcome.status == "failed":
                failure = ET.SubElement(case, "failure", message=outcome.message)
                failure.text = json.dumps(outcome.details, indent=2)
            elif outcome.status == "skipped":
                ET.SubElement(case, "skipped", message=outcome.message)
            elif outcome.status == "environment":
                # JUnit has no first-class "environment issue" status; encode
                # it as a system-out annotation so the case still counts as
                # passed for RES-06 while remaining visible for triage.
                system_out = ET.SubElement(case, "system-out")
                system_out.text = f"ENVIRONMENT ISSUE: {outcome.message}"
        path = self.run_dir / "junit.xml"
        ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)
        return path

    def write_summary_json(self) -> Path:
        """
        @brief Write summary.json (RES-02)

        @return Path to the written file
        """
        summary = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total": len(self.outcomes),
            "passed": sum(1 for o in self.outcomes if o.status == "passed"),
            "failed": sum(1 for o in self.outcomes if o.status == "failed"),
            "skipped": sum(1 for o in self.outcomes if o.status == "skipped"),
            "environment_issues": sum(1 for o in self.outcomes if o.status == "environment"),
            "results": [
                {
                    "test_id": o.test_id,
                    "name": o.name,
                    "status": o.status,
                    "duration_seconds": o.duration_seconds,
                    "message": o.message,
                    "details": o.details,
                }
                for o in self.outcomes
            ],
        }
        path = self.run_dir / "summary.json"
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return path

    def write_environment_json(self, environment_report) -> Path:
        """
        @brief Write environment.json (RES-03)

        @param environment_report: environment.EnvironmentReport instance
        @return Path to the written file
        """
        path = self.run_dir / "environment.json"
        path.write_text(json.dumps(environment_report.to_json(), indent=2), encoding="utf-8")
        return path

    def write_installed_plugin_manifest(self, plugin_manifest) -> Path:
        """
        @brief Write installed-plugin-manifest.json (RES-04)

        @param plugin_manifest: manifest.Manifest of the installed plugin
            directory
        @return Path to the written file
        """
        path = self.run_dir / "installed-plugin-manifest.json"
        path.write_text(json.dumps(plugin_manifest.to_json(), indent=2), encoding="utf-8")
        return path

    def write_markdown_report(self, environment_report=None) -> Path:
        """
        @brief Write report.md, a release-ready rendering of the run (RES-02)

        Derived from the same data as summary.json so the human-readable
        report can never disagree with the machine-readable one.

        @param environment_report: Optional environment.EnvironmentReport
        @return Path to the written file
        """
        from .markdown_report import write_markdown_report

        summary = json.loads((self.run_dir / "summary.json").read_text(encoding="utf-8"))
        environment = environment_report.to_json() if environment_report is not None else None
        return write_markdown_report(self.run_dir, summary, environment)

    def write_all(self, environment_report=None, plugin_manifest=None) -> None:
        """
        @brief Write every required result artifact (RES-01..05)

        @param environment_report: Optional environment.EnvironmentReport
        @param plugin_manifest: Optional manifest.Manifest of the installed
            plugin
        """
        self.write_junit_xml()
        self.write_summary_json()
        if environment_report is not None:
            self.write_environment_json(environment_report)
        if plugin_manifest is not None:
            self.write_installed_plugin_manifest(plugin_manifest)
        self.write_markdown_report(environment_report)

    def exit_code(self) -> int:
        """
        @brief Compute the process exit code (RES-06/RES-07)

        @return 0 when every mandatory test passed, 1 otherwise
        """
        return 0 if all(o.status in ("passed", "skipped", "environment") for o in self.outcomes) else 1
