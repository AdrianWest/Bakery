"""!
@file synthetic.py

@brief Synthetic fixture generators for functional test cases not reachable
    from the four shipped projects.

@section description_synthetic Detailed Description
`Functional Test/test_spec.md` Section 16.7 lists test cases that cannot be
exercised by FT-01..04 alone and requires implementers to add small
synthetic fixtures rather than skip them. This module builds those
synthetic fixtures by cloning an existing working copy and applying a
targeted mutation, so each case still runs Bakery against a realistic
project instead of a hand-built minimal one.

@section notes_synthetic Notes
- Every function here copies from a working copy already produced by
  `start-manuel-test.bat` (never from `Functional Test` directly) into a new
  directory under `C:\\GIT_HUB\\testing`, preserving the "never run Bakery
  directly against a project below Functional Test" rule from Section 3.
- Only the synthetic cases that are pure filesystem mutations are
  implemented here (TC-17, TC-28, TC-33, TC-34). Cases that require a
  modified *global* KiCad library, a corrupted global install, or live
  network fault injection (TC-08, TC-09, TC-10, TC-12, TC-24) are
  intentionally out of scope for this module; see the suite README's
  coverage notes for how to add them in an environment where the global
  libraries can be safely mutated.
"""

import shutil
import time
import zipfile
from pathlib import Path

from . import config


def _clone_working_copy(source_project_dir: Path, synthetic_name: str) -> Path:
    """
    @brief Clone an existing working copy into a new synthetic project
        directory

    @param source_project_dir: An already-restored working copy under
        config.TESTING_WORKSPACE
    @param synthetic_name: Directory name for the new synthetic project
    @return Path to the new synthetic project directory
    """
    destination = config.TESTING_WORKSPACE / synthetic_name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source_project_dir, destination)
    return destination


def make_missing_library_tables_fixture(source_project_dir: Path) -> Path:
    """
    @brief Build the TC-28 fixture: a project with no fp-lib-table/sym-lib-table

    @param source_project_dir: An already-restored working copy
    @return Path to the synthetic project directory
    """
    destination = _clone_working_copy(source_project_dir, "TC-28-no-lib-tables")
    for table_name in ("fp-lib-table", "sym-lib-table"):
        table_path = destination / table_name
        if table_path.exists():
            table_path.unlink()
    return destination


def make_corrupt_symbol_library_fixture(source_project_dir: Path, symbol_dir_name: str, symbol_lib_name: str) -> Path:
    """
    @brief Build the TC-17 fixture: an existing but invalid MySymbols.kicad_sym

    @param source_project_dir: An already-restored working copy
    @param symbol_dir_name: Configured symbol directory name (e.g. "MySym")
    @param symbol_lib_name: Configured symbol library name (e.g. "MySymbols")
    @return Path to the synthetic project directory
    """
    destination = _clone_working_copy(source_project_dir, "TC-17-corrupt-symbol-lib")
    symbol_dir = destination / symbol_dir_name
    symbol_dir.mkdir(parents=True, exist_ok=True)
    corrupt_lib_path = symbol_dir / f"{symbol_lib_name}.kicad_sym"
    corrupt_lib_path.write_text("(this is not )) a valid kicad_symbol_lib(((", encoding="utf-8")
    return destination


def make_all_hidden_project_fixture(source_project_dir: Path) -> Path:
    """
    @brief Build the TC-34 fixture: a project directory containing only
        hidden files

    @param source_project_dir: An already-restored working copy (only its
        directory name is reused; contents are replaced)
    @return Path to the synthetic project directory
    """
    destination = config.TESTING_WORKSPACE / "TC-34-all-hidden"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    hidden_file = destination / ".hidden-placeholder"
    hidden_file.write_text("", encoding="utf-8")
    try:
        import ctypes

        ctypes.windll.kernel32.SetFileAttributesW(str(hidden_file), 0x02)  # FILE_ATTRIBUTE_HIDDEN
    except Exception:
        pass
    return destination


def make_duplicate_backup_race_fixture(project_dir: Path, project_name: str) -> Path:
    """
    @brief Pre-create a backup archive with the current timestamp to force
        the TC-33 FileExistsError path on the next Bakery run

    @param project_dir: Working copy project directory
    @param project_name: Project base name used in the backup file name
    @return Path to the pre-created archive
    """
    backup_dir = project_dir / f"{project_name}-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime(config.__dict__.get("PROJECT_BACKUP_TIMESTAMP_FORMAT", "%Y-%m-%d_%H%M%S"))
    archive_path = backup_dir / f"{project_name}-{timestamp}.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("placeholder.txt", "pre-existing backup for TC-33")
    return archive_path
