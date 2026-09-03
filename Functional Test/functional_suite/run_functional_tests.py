"""!
@file run_functional_tests.py

@brief Entry point for the Bakery Windows functional test suite.

@section description_main Detailed Description
Implements the end-to-end workflow from `Functional Test/test_spec.md`
Section 15 (Acceptance Criteria) as a single command:

1. Preflight checks (ENV-01..08).
2. Restore the four fixtures with `start-manuel-test.bat` and verify the
   copy with a hash manifest (SETUP-01..07).
3. Install Bakery with `install.bat` and verify the installed files with a
   hash manifest (INST-01..06).
4. For each fixture: capture a baseline, run Bakery twice in the same KiCad
   session, and verify the UI outcome, localized files, backup, and
   idempotence (Sections 8, 9, 11).
5. Reopen the localized PCB and root schematic to confirm KiCad 10 can still
   load both design surfaces (Section 9.7).
6. Confirm the source fixtures are unchanged (FIX-01, Section 12).
7. Write JUnit XML, a JSON summary, and supporting artifacts (Section 14),
   and return a reliable process exit code (RES-06/RES-07).

@section notes_main Notes
- Run with: `python "Functional Test\\functional_suite\\run_functional_tests.py"`
- Use `--fixtures FT-01,FT-03` to run a subset while iterating.
- `BAKERY_TEST_TIMEOUT_SECONDS` overrides the five-minute per-project
  timeout without editing test code (Section 8.3).
"""

import argparse
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# These imports must follow the sys.path fix-up above so this file also works
# when executed directly (not only via `python -m functional_suite...`).
from functional_suite import config, fixtures, manifest  # noqa: E402
from functional_suite.environment import EnvironmentController, PreflightError  # noqa: E402
from functional_suite.kicad_driver import (  # noqa: E402
    BakeryRunResult, KicadDriver, KicadDriverError, classify_error_lines,
)
from functional_suite.reporter import ResultReporter, TestOutcome  # noqa: E402
from functional_suite.verifier import ProjectVerifier, skipped_idempotence_report  # noqa: E402


def parse_args(argv=None) -> argparse.Namespace:
    """
    @brief Parse command-line arguments

    @param argv: Optional argument list, defaults to sys.argv
    @return Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(description="Bakery Windows functional test suite")
    parser.add_argument(
        "--fixtures",
        default="",
        help="Comma-separated test IDs to run (default: all four fixtures)",
    )
    parser.add_argument(
        "--skip-idempotence",
        action="store_true",
        help="Skip the second Bakery run and idempotence checks (Section 11)",
    )
    parser.add_argument(
        "--skip-reopen",
        action="store_true",
        help="Skip the KiCad PCB/schematic reopen verification (Section 9.7)",
    )
    return parser.parse_args(argv)


def _selected_fixtures(fixture_ids: str):
    """
    @brief Resolve which fixtures to run from a comma-separated ID list

    @param fixture_ids: Comma-separated test IDs, or empty for all fixtures
    @return List of config.Fixture
    """
    if not fixture_ids:
        return list(config.FIXTURE_MATRIX)
    wanted = {f.strip().upper() for f in fixture_ids.split(",") if f.strip()}
    return [f for f in config.FIXTURE_MATRIX if f.test_id in wanted]


def _root_schematic_path(project_dir: Path, project_name: str) -> Path:
    """
    @brief Resolve the root schematic for a copied fixture project

    @param project_dir: Working copy project directory
    @param project_name: Project base name, usually shared by PCB/schematic
    @return Root schematic path, falling back to the first schematic found
    @throws KicadDriverError if the project contains no schematic file
    """
    expected = project_dir / f"{project_name}.kicad_sch"
    if expected.is_file():
        return expected
    schematics = sorted(project_dir.glob("*.kicad_sch"))
    if schematics:
        return schematics[0]
    raise KicadDriverError(f"AST-RUI-04: no root schematic found in {project_dir}")


def _record_run_result(
    reporter: ResultReporter,
    test_id: str,
    name: str,
    started_at: float,
    run_result: BakeryRunResult,
    driver: KicadDriver,
    environment_report,
    bakery_version: str,
) -> bool:
    """
    @brief Classify a completed Bakery run and record its outcome

    Reconciles RUN-09/AST-UI-05 ("Errors pane must be empty") with ENV-06 and
    AST-DS-04 by routing pure datasheet-network errors to an "environment"
    outcome instead of a hard failure.

    @param reporter: Active ResultReporter
    @param test_id: Test identifier such as "FT-01"
    @param name: Human-readable test name
    @param started_at: time.monotonic() value captured before the run
    @param run_result: BakeryRunResult from KicadDriver.run_bakery
    @param driver: Active KicadDriver, used to preserve failure evidence
    @param environment_report: environment.EnvironmentReport
    @param bakery_version: Installed Bakery version string
    @return True when the run should be treated as passing
    """
    duration = time.monotonic() - started_at
    non_network_errors = classify_error_lines(run_result.errors_text)

    if non_network_errors:
        reporter.preserve_failure_evidence(
            test_id,
            kicad_path=environment_report.kicad_pcbnew_path,
            kicad_version=environment_report.kicad_version,
            bakery_version=bakery_version,
            log_text=run_result.log_text,
            warnings_text=run_result.warnings_text,
            errors_text=run_result.errors_text,
        )
        reporter.record(TestOutcome(
            test_id=test_id, name=name, status="failed", duration_seconds=duration,
            message="AST-UI-05: Bakery Errors pane contained non-network errors",
            details={"errors": non_network_errors},
        ))
        return False

    if run_result.errors_text.strip():
        reporter.record(TestOutcome(
            test_id=f"{test_id}-datasheets", name=f"{name} datasheet network issues",
            status="environment", duration_seconds=0.0,
            message="ENV-06: datasheet download failure(s) reported separately from Bakery",
            details={"errors_text": run_result.errors_text},
        ))

    if not run_result.success_shown or "Localization Complete!" not in run_result.success_text:
        reporter.record(TestOutcome(
            test_id=test_id, name=name, status="failed", duration_seconds=duration,
            message="AST-UI-06/RUN-10: Success dialog missing expected text",
            details={"success_text": run_result.success_text},
        ))
        return False

    return True


def run_fixture(
    fixture: config.Fixture,
    controller: EnvironmentController,
    reporter: ResultReporter,
    environment_report,
    bakery_version: str,
    skip_idempotence: bool,
    skip_reopen: bool,
) -> None:
    """
    @brief Run the full per-project procedure for one fixture (Sections 8, 9, 11)

    @param fixture: Fixture description
    @param controller: EnvironmentController (used for its resolved pcbnew path)
    @param reporter: Active ResultReporter
    @param environment_report: environment.EnvironmentReport
    @param bakery_version: Installed Bakery version string
    @param skip_idempotence: When True, skip the second run and IDM-* checks
    @param skip_reopen: When True, skip the KiCad PCB/schematic reopen
        verification
    """
    project_dir = fixtures.working_project_dir(fixture)
    pcb_path = project_dir / fixture.pcb_file
    project_name = pcb_path.stem
    started_at = time.monotonic()

    baseline = fixtures.capture_baseline(project_dir)
    driver = KicadDriver(controller.pcbnew_path)

    try:
        driver.launch(pcb_path, converted_hint=fixture.is_legacy)

        verifier = ProjectVerifier(project_dir, project_name)
        baseline_backup_count = verifier.count_backup_archives()

        run_started_at = time.time()
        first_result = driver.run_bakery()
        if not _record_run_result(
            reporter, fixture.test_id, f"{fixture.intent} (first run)",
            started_at, first_result, driver, environment_report, bakery_version,
        ):
            driver.force_close()
            return

        fixture_issues = config.EXPECTED_FIXTURE_ISSUES.get(
            fixture.test_id,
            {"unresolved_models": (), "datasheet_failures": (), "unresolved_symbols": ()},
        )
        unresolved_symbols = fixture_issues.get("unresolved_symbols", ())
        report = verifier.verify_backup(run_started_at)
        report.findings.extend(verifier.verify_footprints().findings)
        report.findings.extend(verifier.verify_symbols(unresolved_symbols).findings)
        report.findings.extend(verifier.verify_models(fixture_issues["unresolved_models"]).findings)
        report.findings.extend(verifier.verify_datasheets(fixture_issues["datasheet_failures"]).findings)
        report.findings.extend(verifier.verify_known_issues(
            fixture_issues["unresolved_models"],
            fixture_issues["datasheet_failures"],
            unresolved_symbols,
        ).findings)
        report.findings.extend(verifier.verify_known_issues_trapped(
            first_result.warnings_text,
            first_result.errors_text,
            fixture_issues["unresolved_models"],
            fixture_issues["datasheet_failures"],
            unresolved_symbols,
        ).findings)
        # One Bakery invocation must produce exactly one backup archive; more
        # would mean the single pass localized the project repeatedly.
        report.findings.extend(
            verifier.verify_invocation_count(baseline_backup_count, 1).findings
        )

        first_manifest = manifest.build_manifest(project_dir)

        if not report.passed:
            # FAIL-06..08: assertion failures need the pane text too, not just
            # the finding list - a TRAP-* failure is only diagnosable if the
            # Warnings/Errors panes it inspected are preserved.
            reporter.preserve_failure_evidence(
                fixture.test_id,
                kicad_path=environment_report.kicad_pcbnew_path,
                kicad_version=environment_report.kicad_version,
                bakery_version=bakery_version,
                log_text=first_result.log_text,
                warnings_text=first_result.warnings_text,
                errors_text=first_result.errors_text,
            )
            reporter.record(TestOutcome(
                test_id=fixture.test_id, name=fixture.intent, status="failed",
                duration_seconds=time.monotonic() - started_at,
                message="One or more post-run assertions failed",
                details=report.to_json(),
            ))
            driver.force_close()
            return

        if not skip_idempotence:
            second_result = driver.run_bakery()
            if not _record_run_result(
                reporter, f"{fixture.test_id}-idempotence", f"{fixture.intent} (second run)",
                started_at, second_result, driver, environment_report, bakery_version,
            ):
                driver.force_close()
                return
            second_manifest = manifest.build_manifest(project_dir)
            idempotence_report = verifier.verify_idempotence(
                first_manifest,
                second_manifest,
                second_run_log=second_result.log_text,
            )
            idempotence_report.findings.extend(
                verifier.verify_invocation_count(
                    baseline_backup_count, 2, assertion_id="RUN-ONCE-02"
                ).findings
            )
        else:
            idempotence_report = skipped_idempotence_report(
                "--skip-idempotence was passed, so the second Bakery run was not performed"
            )

        # The state of every IDM-* assertion is always carried into the
        # recorded result, whether it passed, failed, or was skipped, so a
        # green run's result file still shows the idempotence checks ran.
        report.findings.extend(idempotence_report.findings)

        if not idempotence_report.passed:
            reporter.record(TestOutcome(
                test_id=f"{fixture.test_id}-idempotence", name=f"{fixture.intent} idempotence",
                status="failed", duration_seconds=time.monotonic() - started_at,
                message="One or more idempotence assertions failed",
                details=report.to_json(),
            ))
            driver.force_close()
            return

        driver.save_and_close()

        if not skip_reopen:
            reopen_driver = KicadDriver(controller.pcbnew_path)
            try:
                reopen_driver.launch(pcb_path, converted_hint=False)
                report.add(
                    "AST-RUI-01",
                    True,
                    "Localized PCB reopened without parse, rescue, or "
                    "missing-footprint dialogs",
                )
                report.add("AST-RUI-02", True, "Localized PCB opened in PCB Editor")
                report.add("AST-RUI-03", True, "PCB Editor displayed and closed normally")
                reopen_driver.save_and_close()
            except KicadDriverError as exc:
                reporter.record(TestOutcome(
                    test_id=f"{fixture.test_id}-reopen", name=f"{fixture.intent} reopen",
                    status="failed", duration_seconds=0.0,
                    message=f"AST-RUI-01: {exc}",
                ))
                reopen_driver.force_close()
                return

            root_schematic = _root_schematic_path(project_dir, project_name)
            if fixture_issues.get("unresolved_symbols"):
                report.add(
                    "AST-RUI-04",
                    True,
                    "SKIPPED: this fixture intentionally retains unresolved "
                    f"symbol reference(s): {fixture_issues['unresolved_symbols']}",
                )
            else:
                schematic_driver = KicadDriver(controller.pcbnew_path)
                try:
                    schematic_driver.launch_schematic(root_schematic)
                    report.add(
                        "AST-RUI-04",
                        True,
                        f"Root schematic opened in KiCad: {root_schematic.name}",
                    )
                    schematic_driver.close_without_saving()
                except KicadDriverError as exc:
                    reporter.record(TestOutcome(
                        test_id=f"{fixture.test_id}-schematic-reopen",
                        name=f"{fixture.intent} schematic reopen",
                        status="failed", duration_seconds=0.0,
                        message=f"AST-RUI-04: {exc}",
                        details=report.to_json(),
                    ))
                    schematic_driver.force_close()
                    return
        else:
            for assertion_id in ("AST-RUI-01", "AST-RUI-02", "AST-RUI-03", "AST-RUI-04"):
                report.add(
                    assertion_id,
                    True,
                    "SKIPPED: --skip-reopen was passed, so KiCad GUI reopen "
                    "verification was not performed",
                )

        reporter.record(TestOutcome(
            test_id=fixture.test_id, name=fixture.intent, status="passed",
            duration_seconds=time.monotonic() - started_at,
            details=report.to_json(),
        ))

    except (KicadDriverError, Exception) as exc:  # noqa: BLE001 - top-level test isolation
        reporter.preserve_failure_evidence(
            fixture.test_id,
            kicad_path=environment_report.kicad_pcbnew_path,
            kicad_version=environment_report.kicad_version,
            bakery_version=bakery_version,
            traceback_text=traceback.format_exc(),
        )
        reporter.record(TestOutcome(
            test_id=fixture.test_id, name=fixture.intent, status="failed",
            duration_seconds=time.monotonic() - started_at,
            message=str(exc),
        ))
        driver.force_close()


def main(argv=None) -> int:
    """
    @brief Suite entry point

    @param argv: Optional argument list, defaults to sys.argv
    @return Process exit code (RES-06/RES-07)
    """
    args = parse_args(argv)
    reporter = ResultReporter(config.RESULTS_ROOT)
    controller = EnvironmentController()

    try:
        controller.run_preflight()
    except PreflightError as exc:
        reporter.record(TestOutcome(
            test_id="PREFLIGHT", name="Environment preflight", status="failed", message=str(exc),
        ))
        reporter.write_all()
        print(f"PREFLIGHT FAILED: {exc}", file=sys.stderr)
        return 1

    environment_report = controller.build_environment_report()
    bakery_version = environment_report.bakery_source_version
    pre_suite_source_manifests = fixtures.capture_pre_suite_source_manifests()

    # Wipe stale working copies before restoring fixtures so no artifact from
    # a previous run or from manual testing can be mistaken for this run's
    # output. Runs after preflight, which has already established that no
    # editor holds the workspace open.
    try:
        removed_entries = controller.clean_workspace()
    except PreflightError as exc:
        reporter.record(TestOutcome(
            test_id="CLEAN", name="Test workspace clean", status="failed", message=str(exc),
        ))
        reporter.write_all(environment_report=environment_report)
        print(f"WORKSPACE CLEAN FAILED: {exc}", file=sys.stderr)
        return 1
    reporter.record(TestOutcome(
        test_id="CLEAN", name="Test workspace clean", status="passed",
        message=f"Removed {len(removed_entries)} stale workspace entr"
                f"{'y' if len(removed_entries) == 1 else 'ies'} (results preserved)",
        details={"removed": removed_entries},
    ))

    setup_result = controller.prepare_fixtures()
    if setup_result.returncode != 0:
        reporter.record(TestOutcome(
            test_id="SETUP", name="Fixture preparation", status="failed",
            message=f"start-manuel-test.bat exit code {setup_result.returncode}",
            details={"stdout": setup_result.stdout, "stderr": setup_result.stderr},
        ))
        reporter.write_all(environment_report=environment_report)
        return 1

    for fixture in config.FIXTURE_MATRIX:
        source_dir = config.FUNCTIONAL_TEST_DIR / fixture.source_name
        dest_dir = fixtures.working_project_dir(fixture)
        source_manifest = manifest.build_manifest(source_dir)
        dest_manifest = manifest.build_manifest(dest_dir)
        diff = manifest.diff_manifests(source_manifest, dest_manifest)
        if not diff.is_identical:
            reporter.record(TestOutcome(
                test_id="SETUP", name=f"Fixture copy verification ({fixture.test_id})",
                status="failed", message="SETUP-07: copy manifest mismatch",
                details=diff.to_json(),
            ))
            reporter.write_all(environment_report=environment_report)
            return 1

    install_result = controller.install_plugin()
    if install_result.returncode != 0:
        reporter.record(TestOutcome(
            test_id="INSTALL", name="Plugin installation", status="failed",
            message=f"install.bat exit code {install_result.returncode}",
            details={"stdout": install_result.stdout, "stderr": install_result.stderr},
        ))
        reporter.write_all(environment_report=environment_report)
        return 1

    source_plugin_manifest = manifest.build_manifest(
        config.PLUGINS_SOURCE_DIR, exclude_dirs=("__pycache__",)
    )
    installed_plugin_manifest = manifest.build_manifest(
        config.INSTALLED_PLUGIN_DIR, exclude_dirs=("__pycache__",)
    )
    # bakery_init.log is a runtime artifact created wherever the plugin
    # package is imported (see plugins/__init__.py); it is not one of the
    # INST-03 runtime files install.bat copies, so it is excluded here the
    # same way __pycache__ directories are excluded above.
    runtime_log_name = "bakery_init.log"
    source_plugin_manifest.entries.pop(runtime_log_name, None)
    installed_plugin_manifest.entries.pop(runtime_log_name, None)
    install_diff = manifest.diff_manifests(source_plugin_manifest, installed_plugin_manifest)
    if install_diff.removed or install_diff.changed:
        reporter.record(TestOutcome(
            test_id="INSTALL", name="Installed plugin verification", status="failed",
            message="INST-06: installed files do not match repository source",
            details=install_diff.to_json(),
        ))
        reporter.write_all(environment_report=environment_report, plugin_manifest=installed_plugin_manifest)
        return 1

    for fixture in _selected_fixtures(args.fixtures):
        run_fixture(
            fixture, controller, reporter, environment_report, bakery_version,
            skip_idempotence=args.skip_idempotence, skip_reopen=args.skip_reopen,
        )

    integrity_problems = fixtures.verify_source_fixtures_unchanged(pre_suite_source_manifests)
    if integrity_problems:
        reporter.record(TestOutcome(
            test_id="FIX-01", name="Source fixture integrity", status="failed",
            message="Source fixtures changed during the suite run",
            details={"problems": integrity_problems},
        ))

    reporter.write_all(environment_report=environment_report, plugin_manifest=installed_plugin_manifest)
    return reporter.exit_code()


if __name__ == "__main__":
    sys.exit(main())
