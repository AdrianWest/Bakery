"""!
@file markdown_report.py

@brief Render a release-ready Markdown report from the suite's JSON results.

@section description_markdown_report Detailed Description
Turns the machine-oriented artifacts written by `reporter.py` (`summary.json`
plus `environment.json`) into a human-readable `report.md` suitable for
pasting onto a Bakery release page. The renderer is deliberately a pure
transformation of the recorded JSON: it never re-runs tests, never inspects
the workspace, and derives every number it prints from the result data, so
the report can be regenerated for any historical run.

The report answers, in order: did it pass, what was it run against, which
fixtures were exercised, what did the assertions cover, which known-bad
inputs were deliberately tolerated, and (when relevant) what failed.

@section notes_markdown_report Notes
- Written during `ResultReporter.write_all`, so a `report.md` accompanies
  every run's JSON automatically.
- Also usable standalone to re-render an older run:
  `python -m functional_suite.markdown_report <results-dir>`
- Assertion IDs are grouped by their documented prefixes; any unrecognised
  prefix is still counted under "Other" rather than being dropped, so a new
  assertion family can never silently vanish from the report.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Assertion ID prefix -> human-readable grouping used in the coverage table.
# Order matters: the first matching prefix wins, so the more specific
# "AST-DS" style prefixes are listed before any shorter prefix that could
# also match.
ASSERTION_GROUPS: Tuple[Tuple[str, str], ...] = (
    ("AST-BKP", "Backup archive"),
    ("AST-FPT", "Footprint localization"),
    ("AST-SYM", "Symbol localization"),
    ("AST-MDL", "3D model localization"),
    ("AST-DS", "Datasheet localization"),
    ("AST-LIB", "Library table"),
    ("AST-RUI", "Reopen in KiCad"),
    ("AST-UI", "Bakery UI state"),
    ("IDM", "Idempotence (second run)"),
    ("RUN-ONCE", "Single-pass execution"),
    ("KNOWN", "Known-issue persistence"),
    ("TRAP", "Known-issue detection"),
)

STATUS_ICONS = {
    "passed": "✅",
    "failed": "❌",
    "skipped": "⏭️",
    "environment": "🌐",
}


def _format_os_version(raw: str) -> str:
    """
    @brief Present the recorded OS version in human-readable form

    `environment.json` stores the raw `repr()` of `sys.getwindowsversion()`
    (spec RES-03), which is accurate but unreadable on a release page. This
    reformats it for display only; the recorded JSON is left untouched.

    @param raw: Raw os_version string from environment.json
    @return Friendly version string, or the original when it cannot be parsed
    """
    text = str(raw)
    if "getwindowsversion" not in text:
        return text
    fields = {}
    for key in ("major", "minor", "build"):
        match = re.search(rf"{key}=(\d+)", text)
        if match:
            fields[key] = int(match.group(1))
    if "build" not in fields:
        return text
    # Windows 11 reports major=10; the build number is what distinguishes it.
    product = "Windows 11" if fields["build"] >= 22000 else f"Windows {fields.get('major', '')}".strip()
    return f"{product} (build {fields['build']})"


def _escape_cell(value: str) -> str:
    """
    @brief Make a string safe to embed in a Markdown table cell

    Pipes would otherwise split a cell into extra columns, and embedded
    newlines would terminate the table row early; both appear in real
    assertion messages and captured error text.

    @param value: Raw string value
    @return Escaped single-line string
    """
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", "").strip()


def _group_for(assertion_id: str) -> str:
    """
    @brief Map an assertion ID to its coverage-table group

    @param assertion_id: Assertion identifier such as "AST-MDL-03" or
        "TRAP-DS-example.com/x.pdf"
    @return Human-readable group name, or "Other" when no prefix matches
    """
    for prefix, label in ASSERTION_GROUPS:
        if assertion_id.startswith(prefix):
            return label
    return "Other"


def _collect_findings(results: List[Dict]) -> List[Dict]:
    """
    @brief Flatten every assertion finding across all recorded tests

    @param results: The "results" list from summary.json
    @return List of finding dicts, each with an added "test_id" key
    """
    findings = []
    for result in results:
        details = result.get("details") or {}
        for finding in details.get("findings", []) or []:
            enriched = dict(finding)
            enriched["test_id"] = result.get("test_id", "")
            findings.append(enriched)
    return findings


def _format_duration(seconds: float) -> str:
    """
    @brief Format a duration in seconds for display

    @param seconds: Duration in seconds
    @return Compact human-readable duration such as "1m 04s" or "12.3s"
    """
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return "-"
    if value <= 0:
        return "-"
    if value < 60:
        return f"{value:.1f}s"
    minutes, remainder = divmod(int(round(value)), 60)
    return f"{minutes}m {remainder:02d}s"


def _verdict(summary: Dict) -> Tuple[str, str]:
    """
    @brief Derive the overall run verdict

    @param summary: Parsed summary.json content
    @return Tuple of (icon, headline text)
    """
    if summary.get("failed", 0):
        return "❌", "FAILED"
    return "✅", "PASSED"


def _render_summary_section(summary: Dict) -> List[str]:
    """
    @brief Render the headline verdict and totals table

    @param summary: Parsed summary.json content
    @return List of Markdown lines
    """
    icon, headline = _verdict(summary)
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    env_issues = summary.get("environment_issues", summary.get("environment", 0)) or 0

    findings = _collect_findings(summary.get("results", []))
    failed_findings = [f for f in findings if not f.get("passed", True)]
    total_seconds = sum(
        float(r.get("duration_seconds", 0) or 0) for r in summary.get("results", [])
    )

    lines = [
        f"## {icon} Result: **{headline}**",
        "",
        f"**{len(findings)} assertions** across **{total} test entries** — "
        f"{len(failed_findings)} assertion failures.",
        "",
        "| Metric | Count |",
        "|---|---|",
        f"| Test entries | {total} |",
        f"| Passed | {passed} |",
        f"| Failed | {failed} |",
        f"| Skipped | {skipped} |",
        f"| Environment-classified | {env_issues} |",
        f"| Assertions evaluated | {len(findings)} |",
        f"| Assertion failures | {len(failed_findings)} |",
        f"| Total fixture runtime | {_format_duration(total_seconds)} |",
        "",
    ]
    if env_issues:
        lines += [
            "> **Environment-classified entries are not failures.** Per spec "
            "ENV-06/AST-DS-04, datasheet downloads blocked by the remote host "
            "(HTTP 403/404) are recorded separately so an unreachable vendor "
            "website cannot be mistaken for a Bakery defect.",
            "",
        ]
    return lines


def _render_environment_section(environment: Optional[Dict]) -> List[str]:
    """
    @brief Render the "tested against" environment table

    @param environment: Parsed environment.json content, or None
    @return List of Markdown lines
    """
    if not environment:
        return []
    rows = (
        ("Bakery version", environment.get("bakery_source_version", "")),
        ("KiCad version", environment.get("kicad_version", "")),
        ("KiCad executable", environment.get("kicad_pcbnew_path", "")),
        ("Python", (environment.get("python_version", "") or "").split(" ")[0]),
        ("Operating system", _format_os_version(environment.get("os_version", ""))),
        ("pywinauto available", environment.get("pywinauto_available", "")),
    )
    lines = ["## Environment", "", "| Item | Value |", "|---|---|"]
    for label, value in rows:
        if value == "" or value is None:
            continue
        lines.append(f"| {label} | `{_escape_cell(value)}` |")
    lines.append("")
    return lines


def _render_fixture_section(summary: Dict) -> List[str]:
    """
    @brief Render the per-fixture results table

    Only entries that carry assertion findings are treated as fixture runs;
    setup/clean/datasheet bookkeeping entries are summarised separately so
    the headline table stays focused on the four real projects.

    @param summary: Parsed summary.json content
    @return List of Markdown lines
    """
    lines = [
        "## Fixture results",
        "",
        "| Fixture | Status | Assertions | Failed | Duration |",
        "|---|---|---|---|---|",
    ]
    any_fixture = False
    for result in summary.get("results", []):
        details = result.get("details") or {}
        findings = details.get("findings") or []
        if not findings:
            continue
        any_fixture = True
        failed = [f for f in findings if not f.get("passed", True)]
        icon = STATUS_ICONS.get(result.get("status", ""), "")
        lines.append(
            f"| **{_escape_cell(result.get('test_id', ''))}** — "
            f"{_escape_cell(result.get('name', ''))} | {icon} "
            f"{_escape_cell(result.get('status', ''))} | {len(findings)} | "
            f"{len(failed)} | {_format_duration(result.get('duration_seconds', 0))} |"
        )
    if not any_fixture:
        lines.append("| _No fixture runs recorded_ | | | | |")
    lines.append("")
    return lines


def _render_pipeline_section(summary: Dict) -> List[str]:
    """
    @brief Render the non-fixture pipeline steps (clean/setup/install)

    @param summary: Parsed summary.json content
    @return List of Markdown lines
    """
    rows = []
    for result in summary.get("results", []):
        details = result.get("details") or {}
        if details.get("findings"):
            continue
        if result.get("status") == "environment":
            continue
        icon = STATUS_ICONS.get(result.get("status", ""), "")
        rows.append(
            f"| {_escape_cell(result.get('test_id', ''))} | "
            f"{_escape_cell(result.get('name', ''))} | {icon} "
            f"{_escape_cell(result.get('status', ''))} | "
            f"{_escape_cell(result.get('message', '') or '-')} |"
        )
    if not rows:
        return []
    return ["## Pipeline steps", "", "| Step | Name | Status | Notes |", "|---|---|---|---|"] + rows + [""]


def _render_coverage_section(summary: Dict) -> List[str]:
    """
    @brief Render the assertion coverage table grouped by assertion family

    @param summary: Parsed summary.json content
    @return List of Markdown lines
    """
    findings = _collect_findings(summary.get("results", []))
    if not findings:
        return []

    totals: Dict[str, List[int]] = {}
    for finding in findings:
        group = _group_for(finding.get("assertion_id", ""))
        bucket = totals.setdefault(group, [0, 0])
        bucket[0] += 1
        if not finding.get("passed", True):
            bucket[1] += 1

    ordered = [label for _, label in ASSERTION_GROUPS if label in totals]
    ordered += sorted(set(totals) - set(ordered))

    lines = ["## Assertion coverage", "", "| Area | Assertions | Passed | Failed |", "|---|---|---|---|"]
    for label in ordered:
        count, failed = totals[label]
        icon = "❌" if failed else "✅"
        lines.append(f"| {label} | {count} | {count - failed} | {icon} {failed} |")
    lines.append("")
    return lines


def _render_known_issues_section(summary: Dict) -> List[str]:
    """
    @brief Render the known/expected fixture issues and their detection

    These are the intentionally-unresolvable references baked into the
    fixtures. The report lists them explicitly so a release reader can see
    exactly what was tolerated and confirm each one was still actively
    detected and reported by Bakery rather than silently ignored.

    @param summary: Parsed summary.json content
    @return List of Markdown lines
    """
    trapped: Dict[str, List[Tuple[str, bool]]] = {}
    for finding in _collect_findings(summary.get("results", [])):
        assertion_id = finding.get("assertion_id", "")
        if not assertion_id.startswith("TRAP-"):
            continue
        parts = assertion_id.split("-", 2)
        if len(parts) < 3:
            continue
        kind = {"MDL": "3D model", "DS": "Datasheet URL", "SYM": "Symbol"}.get(parts[1], parts[1])
        trapped.setdefault(finding.get("test_id", ""), []).append(
            (f"{kind}: `{parts[2]}`", bool(finding.get("passed", True)))
        )
    if not trapped:
        return []

    lines = [
        "## Known fixture issues (deliberately tolerated)",
        "",
        "The test fixtures intentionally contain permanently-unresolvable "
        "references — a missing 3D model file, dead or bot-blocked vendor "
        "datasheet URLs, and one project with dangling symbol references. "
        "These exercise Bakery's warning/error handling and are **expected**.",
        "",
        "Each is verified twice: the reference must still be present and "
        "unresolved after the run, **and** Bakery must have actively reported "
        "it in the Warnings/Errors pane. A build that silently skipped one of "
        "these would fail the run.",
        "",
        "| Fixture | Known issue | Reported by Bakery |",
        "|---|---|---|",
    ]
    for test_id in sorted(trapped):
        for label, passed in trapped[test_id]:
            icon = "✅ yes" if passed else "❌ **no**"
            lines.append(f"| {_escape_cell(test_id)} | {_escape_cell(label)} | {icon} |")
    lines.append("")
    return lines


def _render_failures_section(summary: Dict) -> List[str]:
    """
    @brief Render detailed failure information, when anything failed

    @param summary: Parsed summary.json content
    @return List of Markdown lines, empty when the run was clean
    """
    failed_results = [r for r in summary.get("results", []) if r.get("status") == "failed"]
    failed_findings = [f for f in _collect_findings(summary.get("results", [])) if not f.get("passed", True)]
    if not failed_results and not failed_findings:
        return []

    lines = ["## Failures", ""]
    for result in failed_results:
        lines.append(
            f"### ❌ {_escape_cell(result.get('test_id', ''))} — "
            f"{_escape_cell(result.get('name', ''))}"
        )
        lines += ["", f"{result.get('message', '') or 'No message recorded.'}", ""]
    if failed_findings:
        lines += ["### Failed assertions", "", "| Test | Assertion | Message |", "|---|---|---|"]
        for finding in failed_findings:
            lines.append(
                f"| {_escape_cell(finding.get('test_id', ''))} | "
                f"`{_escape_cell(finding.get('assertion_id', ''))}` | "
                f"{_escape_cell(finding.get('message', ''))} |"
            )
        lines.append("")
    return lines


def _render_environment_issues_section(summary: Dict) -> List[str]:
    """
    @brief Render the environment-classified (network) entries

    @param summary: Parsed summary.json content
    @return List of Markdown lines
    """
    entries = [r for r in summary.get("results", []) if r.get("status") == "environment"]
    if not entries:
        return []
    lines = [
        "<details>",
        "<summary>🌐 Environment-classified entries "
        f"({len(entries)}) — external datasheet fetches blocked by the remote host</summary>",
        "",
        "| Entry | Note |",
        "|---|---|",
    ]
    for entry in entries:
        lines.append(
            f"| {_escape_cell(entry.get('test_id', ''))} | "
            f"{_escape_cell(entry.get('message', ''))} |"
        )
    lines += ["", "</details>", ""]
    return lines


def render_markdown(summary: Dict, environment: Optional[Dict] = None) -> str:
    """
    @brief Render the full Markdown report

    @param summary: Parsed summary.json content
    @param environment: Parsed environment.json content, or None when the
        run failed before the environment report was built
    @return Complete Markdown document as a single string
    """
    icon, headline = _verdict(summary)
    version = (environment or {}).get("bakery_source_version", "")
    title = f"# Bakery Functional Test Report{f' — v{version}' if version else ''}"

    lines = [
        title,
        "",
        f"_Generated {summary.get('generated_at', 'unknown')} by the Bakery "
        "functional test suite (`Functional Test/functional_suite`)._",
        "",
    ]
    lines += _render_summary_section(summary)
    lines += _render_environment_section(environment)
    lines += _render_fixture_section(summary)
    lines += _render_coverage_section(summary)
    lines += _render_known_issues_section(summary)
    lines += _render_failures_section(summary)
    lines += _render_pipeline_section(summary)
    lines += _render_environment_issues_section(summary)
    lines += [
        "---",
        "",
        "<sub>Every fixture is driven through the real KiCad GUI: the project "
        "is opened in `pcbnew.exe`, the Bakery plugin is invoked through its "
        "dialogs, and the resulting files are verified on disk. Each fixture "
        "is then processed a **second** time to prove the operation is "
        "idempotent, and the localized board and root schematic are reopened "
        "in fresh KiCad processes to confirm they still load.</sub>",
        "",
    ]
    return "\n".join(lines)


def write_markdown_report(
    run_dir: Path,
    summary: Dict,
    environment: Optional[Dict] = None,
) -> Path:
    """
    @brief Render and write report.md into a results directory

    @param run_dir: Timestamped results directory for the run
    @param summary: Parsed summary.json content
    @param environment: Parsed environment.json content, or None
    @return Path to the written report.md
    """
    path = Path(run_dir) / "report.md"
    path.write_text(render_markdown(summary, environment), encoding="utf-8")
    return path


def render_from_results_dir(run_dir: Path) -> Path:
    """
    @brief Re-render report.md for an existing results directory

    Allows any historical run to be turned into a release-ready report
    without re-running the suite.

    @param run_dir: Results directory containing summary.json
    @return Path to the written report.md
    @throws FileNotFoundError if summary.json is not present
    """
    run_dir = Path(run_dir)
    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"No summary.json in {run_dir}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    environment = None
    environment_path = run_dir / "environment.json"
    if environment_path.is_file():
        environment = json.loads(environment_path.read_text(encoding="utf-8"))
    return write_markdown_report(run_dir, summary, environment)


def main(argv: Optional[List[str]] = None) -> int:
    """
    @brief CLI entry point for re-rendering a report from existing results

    @param argv: Optional argument list; defaults to sys.argv[1:]. The single
        expected argument is a results directory. When omitted, the most
        recent run under the configured results root is used.
    @return Process exit code (0 on success)
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        run_dir = Path(args[0])
    else:
        from . import config
        candidates = sorted(p for p in config.RESULTS_ROOT.iterdir() if p.is_dir())
        if not candidates:
            print("No result directories found.", file=sys.stderr)
            return 1
        run_dir = candidates[-1]

    try:
        path = render_from_results_dir(run_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
