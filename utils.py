"""
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
"""

"""!
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
- Supports both KiCad 8 and 9 environment variable formats
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

