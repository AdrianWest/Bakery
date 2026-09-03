"""!
@file fixtures.py

@brief Fixture discovery and baseline helpers for the functional test suite.

@section description_fixtures Detailed Description
Provides the "discover only these four fixture directories" behavior
required by `Functional Test/test_spec.md` Section 4, plus the pre-run
baseline capture required by Section 8.1 (BASE-01..03).

@section notes_fixtures Notes
- Fixture discovery never lists `Functional Test` directly; it only resolves
  the four named entries from `config.FIXTURE_MATRIX`, so `test_spec.md` and
  any other stray file under `Functional Test` is never mistaken for a
  fixture (SETUP-03).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from . import config, manifest


@dataclass
class ProjectBaseline:
    """!
    @brief Pre-run baseline captured for one working project (BASE-01..03).

    @section attributes Attributes
    - project_manifest (manifest.Manifest): Full recursive project manifest.
    - pcb_hash (str): SHA-256 of the .kicad_pcb file, empty if absent.
    - schematic_hashes (Dict[str, str]): SHA-256 per .kicad_sch file name.
    - fp_lib_table_hash (str): SHA-256 of fp-lib-table, empty if absent.
    - sym_lib_table_hash (str): SHA-256 of sym-lib-table, empty if absent.
    """

    project_manifest: manifest.Manifest
    pcb_hash: str
    schematic_hashes: Dict[str, str]
    fp_lib_table_hash: str
    sym_lib_table_hash: str


def working_project_dir(fixture: config.Fixture) -> Path:
    """
    @brief Resolve the working copy directory for a fixture

    @param fixture: Fixture description from config.FIXTURE_MATRIX
    @return Path below config.TESTING_WORKSPACE
    """
    return config.TESTING_WORKSPACE / fixture.working_name


def capture_baseline(project_dir: Path) -> ProjectBaseline:
    """
    @brief Capture the pre-run baseline for one working project (BASE-01..03)

    @param project_dir: Working copy project directory
    @return Populated ProjectBaseline

    @throws FileNotFoundError if project_dir does not exist
    """
    project_manifest = manifest.build_manifest(project_dir)

    pcb_files = list(project_dir.glob("*.kicad_pcb"))
    pcb_hash = manifest.hash_file(pcb_files[0]) if pcb_files else ""

    schematic_hashes = {
        sch.name: manifest.hash_file(sch) for sch in project_dir.glob("*.kicad_sch")
    }

    fp_lib_table = project_dir / "fp-lib-table"
    sym_lib_table = project_dir / "sym-lib-table"
    fp_lib_table_hash = manifest.hash_file(fp_lib_table) if fp_lib_table.is_file() else ""
    sym_lib_table_hash = manifest.hash_file(sym_lib_table) if sym_lib_table.is_file() else ""

    return ProjectBaseline(
        project_manifest=project_manifest,
        pcb_hash=pcb_hash,
        schematic_hashes=schematic_hashes,
        fp_lib_table_hash=fp_lib_table_hash,
        sym_lib_table_hash=sym_lib_table_hash,
    )


def verify_source_fixtures_unchanged(pre_suite_manifests: Dict[str, manifest.Manifest]) -> List[str]:
    """
    @brief Compare source fixture manifests before and after a suite run
        (FIX-01)

    @param pre_suite_manifests: Mapping of fixture.source_name to the
        manifest captured before the suite ran
    @return List of human-readable descriptions of any change; empty when
        every source fixture is unchanged
    """
    problems: List[str] = []
    for fixture in config.FIXTURE_MATRIX:
        source_dir = config.FUNCTIONAL_TEST_DIR / fixture.source_name
        before = pre_suite_manifests.get(fixture.source_name)
        if before is None:
            continue
        after = manifest.build_manifest(source_dir)
        diff = manifest.diff_manifests(before, after)
        if not diff.is_identical:
            problems.append(
                f"{fixture.source_name}: added={diff.added}, "
                f"removed={diff.removed}, changed={diff.changed}"
            )
    return problems


def capture_pre_suite_source_manifests() -> Dict[str, manifest.Manifest]:
    """
    @brief Capture every source fixture's manifest before the suite runs

    @return Mapping of fixture.source_name to its Manifest
    """
    return {
        fixture.source_name: manifest.build_manifest(
            config.FUNCTIONAL_TEST_DIR / fixture.source_name
        )
        for fixture in config.FIXTURE_MATRIX
    }
