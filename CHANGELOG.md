# Changelog

All notable changes to the Bakery KiCad plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Code of Conduct (CODE_OF_CONDUCT.md) referenced in README Contributing section
- **New base_localizer.py module** - Base class for all localizers with shared functionality
  - Common logging, file lock detection, and schematic update methods
  - Template methods for consistent behavior across all localizers
  - 198 lines of reusable code

### Changed
- README requirements updated to correctly state "KiCad 8.0 or later" (was incorrectly "9.0 or later")
- Symbol library version format updated to 20241209 (was 20211014)
- **Major refactoring to eliminate code duplication (Code Review Issue #8)**
  - Created BaseLocalizer abstract base class with shared functionality
  - FootprintLocalizer now inherits from BaseLocalizer
  - SymbolLocalizer now inherits from BaseLocalizer
  - Eliminated duplicate methods:
    - log() method removed from both child classes
    - is_file_locked() consolidated in base class
    - find_schematic_files() moved to base class
    - update_schematic_file() centralized with generic implementation
    - replace_references_in_content() shared method for text replacements
  - Simplified update_schematic_references() in both localizers (~100 lines reduced to ~40)
  - Reduced total code duplication by ~150 lines
  - Improved maintainability, consistency, and extensibility
  - Maintains full backward compatibility with existing code

### Fixed
- Symbol library file handling when file doesn't exist or is empty
  - Added validation to detect empty or corrupted symbol library files
  - Properly creates new library structure if existing file is invalid
  - Enhanced logging in write_symbol_library() to track symbol writing progress
  - Now handles edge cases where library file exists but contains only whitespace

### Added (Previous)
- Symbol localization from global to project libraries
- Symbol library table (sym-lib-table) management
- Comprehensive Doxygen-style documentation for all modules and classes
- File-level docstrings with @file, @brief, and @section tags
- Class-level docstrings with @section methods and @section attributes
- Utility module (utils.py) for shared functionality
- KiCad Plugin Manager (PCM) release checklist (PCM_RELEASE_CHECKLIST.md)
- High-resolution plugin icon (256x256 pixels)
- File lock detection to prevent schematic modification while files are open in editor
- Upfront schematic file lock checking before starting localization process
- Completion dialog showing summary of copied items when process finishes
- Helper methods in FootprintLocalizer: copy_single_model() and update_footprint_model_paths()
- **Support for hierarchical schematics (tested)** - Recursively finds all .kicad_sch files in subdirectories

### Changed
- Updated all class docstrings to use Doxygen format with `!` marker
- Enhanced documentation with detailed descriptions and notes sections
- Improved project structure documentation in README
- Updated roadmap to reflect symbol localization as implemented
- Updated metadata.json for KiCad PCM compliance:
  - Changed identifier to proper reverse-domain format (com.github.adrianwest.bakery)
  - Updated license to standard identifier (GPL-3.0)
  - Added comprehensive description and tags
  - Added repository URL and version compatibility range
  - Added placeholders for download hash and file sizes
- Plugin icon changed from Bakery_Icon.png to Bakery_Icon_256x256.png for better quality
- Updated install.bat to copy new 256x256 icon
- Improved S-expression parser cache to use proper LRU eviction with OrderedDict
- Refactored nested try-except blocks in 3D model localization for better maintainability
- Progress bar now resets to 0 after completion

### Removed
- Unused functions from utils.py: safe_write_file(), update_library_table()
- Unused constants: LOG_FONT_FAMILY, SEXPR_REFERENCE, SEXPR_VALUE
- Unused error messages: ERROR_FILE_NOT_FOUND, ERROR_PERMISSION_DENIED, SUCCESS_BACKUP_CREATED
- Dead code cleanup (~75 lines removed)

### Fixed
- Missing constant imports in library_manager.py:
  - KICAD_ENV_FOOTPRINT_DIR, KICAD_ENV_3DMODEL_DIR, KICAD_ENV_SYMBOL_DIR
  - KICAD_VERSION_FALLBACK
- Missing constant imports in symbol_localizer.py:
  - PROGRESS_STEP_COPY_SYMBOLS
  - PROGRESS_STEP_UPDATE_SYM_LIB_TABLE
- Missing constant imports in footprint_localizer.py:
  - PROGRESS_STEP_SCAN_PCB, PROGRESS_STEP_SCAN_SCHEMATICS
  - PROGRESS_STEP_COPY_3D_MODELS
  - PROGRESS_STEP_UPDATE_PCB, PROGRESS_STEP_UPDATE_SCHEMATICS
  - ENV_VAR_KIPRJMOD
- README now accurately reflects current implementation (symbols fully implemented)
- Syntax errors in constants.py and utils.py introduced during code cleanup

## [1.0.0] - 2026-01-11

### Added
- Footprint localization from global to project libraries
- 3D model localization with automatic path updates
- Interactive configuration dialog for library names and options
- Progress bar with step-by-step status updates
- Separate logging panes for warnings and errors
- Automatic backup creation before file modifications
- Support for both PCB and schematic file updates
- Environment variable expansion for KiCad 8 and 9 compatibility
- Comprehensive error handling and reporting
- Project-local fp-lib-table management

### Architecture
- Modular design with separated concerns:
  - `bakery_plugin.py` - Main ActionPlugin interface
  - `footprint_localizer.py` - Footprint and 3D model operations
  - `symbol_localizer.py` - Symbol localization operations
  - `library_manager.py` - Library table management
  - `sexpr_parser.py` - S-expression parsing utilities
  - `ui_components.py` - User interface components
  - `backup_manager.py` - File backup handling
  - `constants.py` - Configuration constants
  - `utils.py` - Shared utility functions

### Fixed
- License consistency (GPL-3.0 across all files)
- Metadata accuracy in metadata.json
- Import error handling for development environments
- Path safety validation
- Race conditions in file operations

## [Planned for Future Versions]

- Additional features based on user feedback

---

[1.0.0]: https://github.com/bakery-kicad/Bakery/releases/tag/v1.0.0
