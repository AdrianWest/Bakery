"""
Copyright (C) 2026 Bakery Contributors

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
"""

"""
@brief Utility functions shared across Bakery plugin modules

This module provides common utilities for:
- Path expansion and validation
- File operations with safety checks
- Input validation
"""

import os
import re
from typing import Optional


# Maximum file size to read into memory (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


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
        # Resolve to absolute paths
        abs_path = os.path.realpath(path)
        abs_project = os.path.realpath(project_dir)
        
        # Check if path is within project directory
        return abs_path.startswith(abs_project)
    except Exception:
        return False


def expand_kicad_path(path: str, project_dir: Optional[str] = None) -> str:
    """
    @brief Expand KiCad environment variables in path
    
    @param path: Path with potential environment variables
    @param project_dir: Optional project directory for ${KIPRJMOD}
    @return Expanded path
    
    Supports common KiCad environment variables including:
    - ${KIPRJMOD} - Project directory
    - ${KICAD9_*} - KiCad 9.x variables  
    - ${KICAD8_*} - KiCad 8.x variables
    - ${KICAD_*} - Generic KiCad variables
    """
    expanded_path = path
    
    # Handle ${KIPRJMOD}
    if project_dir and "${KIPRJMOD}" in expanded_path:
        expanded_path = expanded_path.replace("${KIPRJMOD}", project_dir)
    
    # Find all environment variable references
    import re
    env_vars = re.findall(r'\$\{([^}]+)\}', expanded_path)
    
    for var in env_vars:
        # Try to get the environment variable value
        env_value = os.environ.get(var)
        if env_value:
            expanded_path = expanded_path.replace(f"${{{var}}}", env_value)
    
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


def safe_write_file(path: str, content: str, encoding: str = 'utf-8', project_dir: Optional[str] = None) -> None:
    """
    @brief Safely write to a file with path validation
    
    @param path: Path to write to
    @param content: Content to write
    @param encoding: File encoding (default: utf-8)
    @param project_dir: Optional project directory for safety validation
    
    @throws ValueError if path is unsafe
    @throws OSError if file cannot be written
    """
    if project_dir and not validate_path_safety(path, project_dir):
        raise ValueError(f"Unsafe path (outside project directory): {path}")
    
    with open(path, 'w', encoding=encoding) as f:
        f.write(content)


def find_schematic_files(project_dir: str) -> list:
    """
    @brief Find all schematic files in project directory
    
    @param project_dir: Project directory path
    @return List of schematic file paths
    """
    import glob
    return glob.glob(os.path.join(project_dir, "*.kicad_sch"))


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
    def log(level, msg):
        if logger:
            method = getattr(logger, level, None)
            if method:
                method(msg)
    
    items = set()
    log('info', f"{progress_msg}...")
    
    schematic_files = find_schematic_files(project_dir)
    log('info', f"Found {len(schematic_files)} schematic file(s)")
    
    for sch_file in schematic_files:
        log('info', f"  Parsing {os.path.basename(sch_file)}")
        try:
            sexpr = parse_file_with_sexpr(sch_file, parser)
            file_items = extract_func(sexpr)
            items.update(file_items)
            
            for item in file_items:
                # Handle both tuples and single items
                if isinstance(item, tuple):
                    log('info', f"    - {':'.join(str(x) for x in item)}")
                else:
                    log('info', f"    - {item}")
                    
        except Exception as e:
            log('warning', f"Could not parse {os.path.basename(sch_file)}: {str(e)}")
    
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


def update_library_table(
    table_path: str,
    lib_name: str,
    table_type: str,
    parser,
    logger=None
):
    """
    @brief Generic library table update function
    
    @param table_path: Path to library table file
    @param lib_name: Library name to check/add
    @param table_type: Type identifier for table (e.g., 'fp_lib_table', 'sym_lib_table')
    @param parser: SExpressionParser instance
    @param logger: Optional logger object
    @return Tuple of (sexpr, is_new_table, lib_exists)
    
    Reads existing table or creates new one. Returns parsed structure
    and flags indicating whether table is new and if library already exists.
    """
    from .constants import SEXPR_NAME
    
    def log(level, msg):
        if logger:
            method = getattr(logger, level, None)
            if method:
                method(msg)
    
    if os.path.exists(table_path):
        log('info', f"Found existing {table_type}")
        content = safe_read_file(table_path)
        
        # Check if library already exists
        if f'({SEXPR_NAME} "{lib_name}")' in content or f"({SEXPR_NAME} '{lib_name}')" in content:
            log('info', f"Library '{lib_name}' already exists in {table_type}")
            return None, False, True
        
        sexpr = parser.parse(content)
        return sexpr, False, False
    else:
        log('info', f"Creating new {table_type}")
        return None, True, False
