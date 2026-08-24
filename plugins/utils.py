"""!
Copyright (C) 2026 Adrian West

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
@file utils.py

@brief Utility functions shared across Bakery plugin modules

This module provides common utilities for:
- Path expansion and validation
- File operations with safety checks
- Input validation

@section description_utils Detailed Description
This module contains shared utility functions used throughout the Bakery plugin.
It provides safe file reading, path expansion with environment variables,
schematic file discovery, and library table management functions.

@section notes_utils Notes
- All file operations include error handling
- Path validation prevents directory traversal attacks
- Runtime resolution supports KiCad 10 (KICAD10_*) path variables only.
  Legacy KICAD9_* tokens found in existing project files are normalized to
  the KICAD10_* equivalent as input migration; KiCad 8/9 installations are
  never discovered or read from at runtime.
"""

import os
import re
import hashlib
import stat
import tempfile
from typing import Callable, Optional, Union
from .constants import (
    LIBRARY_TYPE_KICAD, MAX_FILE_SIZE_BYTES, ENV_VAR_PREFIX_PRIMARY,
    LEGACY_ENV_VAR_PREFIXES, SEXPR_DESCR, SEXPR_LIB, SEXPR_NAME,
    SEXPR_OPTIONS, SEXPR_TYPE, SEXPR_URI
)
from .sexpr_parser import SExpressionParseError, SExpressionParser


# Maximum file size to read into memory (50MB)
MAX_FILE_SIZE = MAX_FILE_SIZE_BYTES


def log_message(logger: Optional[Callable], level: str, message: str) -> None:
    """
    @brief Send a message to a logger method when available

    @param logger: Optional logger object with level-named methods
    @param level: Logger method name such as info, warning, error, or success
    @param message: Message to send
    """
    if logger:
        method = getattr(logger, level, None)
        if method:
            method(message)


class LoggerMixin:
    """!
    @brief Provide consistent logger dispatch for Bakery service classes.
    """

    logger: Optional[Callable]

    def log(self, level: str, message: str) -> None:
        """
        @brief Send a message through the configured logger

        @param level: Logger method name such as info, warning, error, or success
        @param message: Message to send
        """
        log_message(self.logger, level, message)


class ParserLoggerMixin(LoggerMixin):
    """!
    @brief Provide shared parser and logger initialization for Bakery services.
    """

    def __init__(self, logger: Optional[Callable] = None):
        """
        @brief Initialize a service with a logger and S-expression parser

        @param logger: Optional logger object with level-named methods
        """
        self.logger = logger
        self.parser = SExpressionParser()


def get_kicad_table_paths(table_name: str, project_dir: Optional[str] = None) -> list:
    """
    @brief Return KiCad library-table candidates in project/configuration order

    @param table_name: Table filename, such as fp-lib-table or sym-lib-table
    @param project_dir: Optional project directory whose table takes precedence
    @return Ordered list of candidate table paths
    """
    candidates = []
    if project_dir:
        candidates.append(os.path.join(project_dir, table_name))

    config_home = os.environ.get('KICAD_CONFIG_HOME')
    if config_home:
        candidates.append(os.path.join(config_home, '10.0', table_name))

    candidates.extend([
        os.path.join(os.environ.get('APPDATA', ''), 'kicad', '10.0', table_name),
        os.path.join(os.environ.get('USERPROFILE', ''), 'Documents', 'KiCad', '10.0', table_name),
        os.path.join(os.path.expanduser('~'), '.config', 'kicad', '10.0', table_name),
        os.path.join(os.path.expanduser('~'), 'Library', 'Preferences', 'kicad', '10.0', table_name),
    ])
    return list(dict.fromkeys(candidates))


def resolve_library_path(
    table_name: str,
    lib_name: str,
    parser,
    logger: Optional[Callable] = None,
    project_dir: Optional[str] = None
) -> Optional[str]:
    """
    @brief Resolve a library nickname through KiCad library tables

    Searches project and user tables in precedence order and follows delegated
    KiCad tables without revisiting a table.

    @param table_name: KiCad library table filename
    @param lib_name: Library nickname to resolve
    @param parser: SExpressionParser-compatible parser
    @param logger: Optional logger object
    @param project_dir: Optional project directory whose table takes precedence
    @return Expanded library path, or None when the nickname cannot be resolved
    """
    pending_tables = get_kicad_table_paths(table_name, project_dir)
    visited_tables = set()

    while pending_tables:
        table_path = pending_tables.pop(0)
        if table_path in visited_tables or not os.path.exists(table_path):
            continue
        visited_tables.add(table_path)
        log_message(logger, 'info', f"Checking {table_name}: {table_path}")

        try:
            table_sexpr = parser.parse(safe_read_file(table_path))
        except (OSError, UnicodeError, SExpressionParseError) as error:
            log_message(
                logger,
                'warning',
                f"Could not read {table_name} at {table_path}: {error}"
            )
            continue

        library_uri = parser.find_library_path(table_sexpr, lib_name)
        if library_uri:
            try:
                return expand_kicad_path(library_uri, project_dir)
            except KicadPathResolutionError as error:
                log_message(
                    logger,
                    'warning',
                    f"Could not resolve path for '{lib_name}': {error}"
                )
                return None

        delegate_uri = parser.find_library_path(table_sexpr, "KiCad")
        if delegate_uri:
            try:
                delegated_table = expand_kicad_path(delegate_uri, project_dir)
            except KicadPathResolutionError as error:
                log_message(
                    logger,
                    'warning',
                    f"Could not resolve delegated {table_name}: {error}"
                )
            else:
                pending_tables.insert(0, delegated_table)

    log_message(
        logger,
        'warning',
        f"Library '{lib_name}' not found in {table_name}"
    )
    return None


def update_library_table(
    table_path: str,
    table_tag: str,
    lib_name: str,
    library_uri: str,
    parser,
    logger: Optional[Callable] = None,
    description: str = ""
) -> bool:
    """
    @brief Add or update a library entry in a KiCad library table

    @param table_path: Destination fp-lib-table or sym-lib-table path
    @param table_tag: Root S-expression tag for the table
    @param lib_name: Library nickname
    @param library_uri: Unquoted KiCad URI for the library
    @param parser: SExpressionParser-compatible parser
    @param logger: Optional logger object
    @param description: Optional library description
    @return True when the table was updated successfully
    """
    try:
        if os.path.exists(table_path):
            table_sexpr = parser.parse(safe_read_file(table_path))
            if not (
                isinstance(table_sexpr, list)
                and table_sexpr
                and table_sexpr[0] == table_tag
            ):
                log_message(
                    logger,
                    'error',
                    f"Invalid KiCad library table: {table_path}"
                )
                return False
        else:
            table_sexpr = [table_tag]

        quoted_uri = f'"{library_uri}"'
        for entry in table_sexpr[1:]:
            if not isinstance(entry, list) or not entry or entry[0] != SEXPR_LIB:
                continue

            entry_name = None
            uri_index = None
            for index, field in enumerate(entry):
                if not isinstance(field, list) or len(field) < 2:
                    continue
                if field[0] == SEXPR_NAME:
                    entry_name = field[1].strip('"').strip("'")
                elif field[0] == SEXPR_URI:
                    uri_index = index

            if entry_name != lib_name:
                continue

            if uri_index is None:
                entry.append([SEXPR_URI, quoted_uri])
            else:
                entry[uri_index] = [SEXPR_URI, quoted_uri]
            break
        else:
            table_sexpr.append([
                SEXPR_LIB,
                [SEXPR_NAME, f'"{lib_name}"'],
                [SEXPR_TYPE, f'"{LIBRARY_TYPE_KICAD}"'],
                [SEXPR_URI, quoted_uri],
                [SEXPR_OPTIONS, '""'],
                [SEXPR_DESCR, f'"{description}"']
            ])

        atomic_write_file(table_path, parser.to_string(table_sexpr))
        log_message(
            logger,
            'info',
            f"Library '{lib_name}' updated in {os.path.basename(table_path)}"
        )
        return True
    except (OSError, UnicodeError, SExpressionParseError, TypeError, IndexError) as error:
        log_message(
            logger,
            'error',
            f"Failed to update {os.path.basename(table_path)}: {error}"
        )
        return False


def validate_library_name(name: str) -> bool:
    """
    @brief Validate library name contains only safe characters
    
    @param name: Library name to validate
    @return True if valid, False otherwise
    
    Library names must not contain path separators or special characters
    that could cause filesystem issues.
    """
    if not name or not name.strip():
        return False
    # Disallow path separators and special chars
    return not re.search(r'[<>:"/\\|?*\x00-\x1f]', name)


def validate_path_safety(path: str, project_dir: str) -> bool:
    """
    @brief Ensure path is within project directory for security
    
    @param path: Path to validate
    @param project_dir: Project directory (boundary)
    @return True if path is safe, False otherwise
    
    Prevents path traversal attacks by ensuring the resolved path
    is within the project directory boundary.
    """
    try:
        abs_path = os.path.realpath(path)
        abs_project = os.path.realpath(project_dir)
        common_path = os.path.commonpath([abs_path, abs_project])
        return os.path.normcase(common_path) == os.path.normcase(abs_project)
    except (OSError, ValueError):
        return False


def make_localized_item_name(source_library: str, item_name: str) -> str:
    """
    @brief Build a deterministic collision-safe local library item name

    @param source_library: Original library nickname
    @param item_name: Original symbol or footprint name
    @return Length-bounded filesystem-safe name with a stable source hash
    """
    safe_library = re.sub(
        r'[^A-Za-z0-9_.-]+',
        '_',
        source_library
    ).strip('._') or "library"
    safe_item = re.sub(
        r'[<>:"/\\|?*\x00-\x1f]+',
        '_',
        item_name
    ).strip('. ') or "item"
    digest = hashlib.sha256(
        f"{source_library}\0{item_name}".encode('utf-8')
    ).hexdigest()[:10]
    return f"{safe_library[:48]}__{safe_item[:120]}_{digest}"


def make_collision_safe_filename(filename: str, source_key: str) -> str:
    """
    @brief Add a stable source hash to a destination filename

    @param filename: Preferred destination filename
    @param source_key: Stable source path or URL used to distinguish assets
    @return Filename with a deterministic short hash before the extension
    """
    stem, extension = os.path.splitext(filename)
    safe_stem = re.sub(
        r'[<>:"/\\|?*\x00-\x1f]+',
        '_',
        stem
    ).strip('. ') or "asset"
    digest = hashlib.sha256(source_key.encode('utf-8')).hexdigest()[:10]
    return f"{safe_stem}_{digest}{extension}"


class KicadPathResolutionError(Exception):
    """
    @brief Raised when a KiCad path variable cannot be resolved to a concrete path

    Callers must catch this at the localization boundary, log the unresolved
    variable, surface it through the existing warning/error UI, and skip only
    the affected asset rather than using a partially-expanded or literal
    "${VAR}" path.
    """

    def __init__(self, path: str, variable: str):
        """
        @brief Initialize an unresolved KiCad path error

        @param path: Original path containing the unresolved variable
        @param variable: Variable name that could not be resolved
        """
        self.path = path
        self.variable = variable
        super().__init__(f"Could not resolve KiCad path variable '${{{variable}}}' in path: {path}")


def _normalize_legacy_kicad_var(var_name: str) -> str:
    """
    @brief Normalize a legacy versioned KiCad path-variable name to the KICAD10_* equivalent

    This is input-token normalization only (e.g. for KICAD9_* tokens found in
    existing project files); it never triggers a lookup of an older KiCad
    installation's environment or configuration.

    @param var_name: Raw variable name found inside ${...}
    @return Normalized KICAD10_* variable name, or var_name unchanged if not legacy
    """
    for legacy_prefix in LEGACY_ENV_VAR_PREFIXES:
        if var_name.startswith(legacy_prefix):
            return ENV_VAR_PREFIX_PRIMARY + var_name[len(legacy_prefix):]
    return var_name


def _expand_via_kicad_native_api(var_name: str) -> Optional[str]:
    """
    @brief Tier-2 resolver: ask KiCad's own path-expansion API

    Used for values configured only in KiCad's Configure Paths dialog, which
    are internal to KiCad and not guaranteed to exist in os.environ. Returns
    None (rather than raising) if pcbnew is unavailable or the variable is
    still unresolved, so the caller can fall through to the failure contract.

    @param var_name: Normalized (KICAD10_*) variable name
    @return Expanded value, or None if unavailable
    """
    try:
        import pcbnew
    except ImportError:
        return None

    try:
        project = None
        try:
            board = pcbnew.GetBoard()
            project = board.GetProject() if board else None
        except Exception:
            project = None

        token = f"${{{var_name}}}"
        expanded = str(pcbnew.ExpandEnvVarSubstitutions(token, project))
        if expanded and expanded != token:
            return expanded
    except Exception:
        pass

    return None


def expand_kicad_path(path: str, project_dir: Optional[str] = None) -> str:
    """
    @brief Expand KiCad environment variables in path
    
    @param path: Path with potential environment variables
    @param project_dir: Optional project directory for ${KIPRJMOD}
    @return Expanded path

    @throws KicadPathResolutionError if a non-KIPRJMOD variable cannot be
            resolved through any tier. Never returns a path that still
            contains an unresolved "${...}" reference.

    Resolution order for each ${VAR} (matching KiCad's documented precedence):
    1. ${KIPRJMOD} is expanded directly from project_dir if supplied.
    2. Legacy versioned tokens (e.g. ${KICAD9_FOOTPRINT_DIR}) are normalized
       to the KICAD10_* equivalent.
    3. An explicitly set os.environ value (KiCad's documented override).
    4. KiCad's native path-expansion API, for values set only in Configure Paths.
    5. KicadPathResolutionError, if still unresolved.
    """
    expanded_path = path
    
    # Handle ${KIPRJMOD}
    if project_dir and "${KIPRJMOD}" in expanded_path:
        expanded_path = expanded_path.replace("${KIPRJMOD}", project_dir)
    
    # Find all remaining environment variable references
    env_vars = re.findall(r'\$\{([^}]+)\}', expanded_path)
    
    for var in env_vars:
        if var == "KIPRJMOD":
            # No project_dir was supplied; KIPRJMOD is not a global lookup failure.
            continue

        normalized_var = _normalize_legacy_kicad_var(var)

        env_value = os.environ.get(normalized_var)

        if not env_value:
            env_value = _expand_via_kicad_native_api(normalized_var)

        if env_value:
            expanded_path = expanded_path.replace(f"${{{var}}}", env_value)
        else:
            raise KicadPathResolutionError(path, var)
    
    # Handle file:// URIs
    if expanded_path.startswith("file://"):
        expanded_path = expanded_path[7:]
    
    return expanded_path


def safe_read_file(path: str, encoding: str = 'utf-8', max_size: Optional[int] = None) -> str:
    """
    @brief Safely read a file with size limit check
    
    @param path: Path to file
    @param encoding: File encoding (default: utf-8)
    @param max_size: Maximum file size in bytes (default: MAX_FILE_SIZE)
    @return File contents
    
    @throws ValueError if file is too large
    @throws OSError if file cannot be read
    """
    if max_size is None:
        max_size = MAX_FILE_SIZE
    
    size = os.path.getsize(path)
    if size > max_size:
        raise ValueError(f"File too large: {size} bytes (max: {max_size})")
    
    with open(path, 'r', encoding=encoding) as f:
        return f.read()


def atomic_write_file(
    path: str,
    content: Union[str, bytes],
    encoding: str = 'utf-8'
) -> None:
    """
    @brief Atomically replace a file with text or binary content

    Writes to a temporary file in the destination directory and then replaces
    the destination, preventing partially-written KiCad files.

    @param path: Destination file path
    @param content: Text or binary content to write
    @param encoding: Text encoding used when content is a string

    @throws OSError if the temporary file cannot be written or replaced
    @throws UnicodeError if text cannot be encoded
    """
    destination = os.path.abspath(path)
    destination_dir = os.path.dirname(destination)
    existing_mode = None
    if os.path.exists(destination):
        existing_mode = stat.S_IMODE(os.stat(destination).st_mode)
    file_descriptor, temp_path = tempfile.mkstemp(
        dir=destination_dir,
        prefix=f".{os.path.basename(destination)}.",
        suffix=".tmp"
    )

    try:
        if isinstance(content, bytes):
            with os.fdopen(file_descriptor, 'wb') as temp_file:
                temp_file.write(content)
        else:
            with os.fdopen(file_descriptor, 'w', encoding=encoding) as temp_file:
                temp_file.write(content)
        if existing_mode is not None:
            os.chmod(temp_path, existing_mode)
        os.replace(temp_path, destination)
    finally:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def find_schematic_files(project_dir: str) -> list:
    """
    @brief Find all schematic files in project directory including hierarchical sheets
    
    @param project_dir: Project directory path
    @return List of schematic file paths (sorted for consistency)
    
    Searches recursively for all .kicad_sch files to support hierarchical schematics.
    Hierarchical sheets may be in subdirectories within the project.
    """
    import glob
    # Search recursively for all .kicad_sch files (supports hierarchical schematics)
    schematic_files = glob.glob(os.path.join(project_dir, "**", "*.kicad_sch"), recursive=True)
    return sorted(schematic_files)  # Sort for consistent processing order


def scan_schematics_for_items(
    project_dir: str,
    parser,
    extract_func,
    logger=None,
    progress_msg: str = "Scanning schematics"
):
    """
    @brief Generic schematic scanning function
    
    @param project_dir: Project directory path
    @param parser: SExpressionParser instance
    @param extract_func: Function to extract items from parsed sexpr
    @param logger: Optional logger object
    @param progress_msg: Progress message to log
    @return Set of extracted items
    
    Scans all schematic files and extracts items using provided function.
    """
    items = set()
    log_message(logger, 'info', f"{progress_msg}...")
    
    schematic_files = find_schematic_files(project_dir)
    log_message(logger, 'info', f"Found {len(schematic_files)} schematic file(s)")
    
    for sch_file in schematic_files:
        log_message(logger, 'info', f"  Parsing {os.path.basename(sch_file)}")
        try:
            sexpr = parse_file_with_sexpr(sch_file, parser)
            file_items = extract_func(sexpr)
            items.update(file_items)
            
            for item in file_items:
                # Handle both tuples and single items
                if isinstance(item, tuple):
                    log_message(logger, 'info', f"    - {':'.join(str(x) for x in item)}")
                else:
                    log_message(logger, 'info', f"    - {item}")
                    
        except Exception as e:
            log_message(
                logger,
                'warning',
                f"Could not parse {os.path.basename(sch_file)}: {str(e)}"
            )
    
    return items


def parse_file_with_sexpr(file_path: str, parser):
    """
    @brief Read and parse a file as S-expression
    
    @param file_path: Path to file
    @param parser: SExpressionParser instance
    @return Parsed S-expression
    
    @throws Exception if file cannot be read or parsed
    """
    content = safe_read_file(file_path)
    return parser.parse(content)
