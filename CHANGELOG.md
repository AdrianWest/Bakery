# Changelog

All notable changes to the Bakery KiCad plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Symbol localization from global to project libraries
- Symbol library table (sym-lib-table) management
- Comprehensive Doxygen-style documentation for all modules and classes
- File-level docstrings with @file, @brief, and @section tags
- Class-level docstrings with @section methods and @section attributes
- Utility module (utils.py) for shared functionality

### Changed
- Updated all class docstrings to use Doxygen format with `!` marker
- Enhanced documentation with detailed descriptions and notes sections
- Improved project structure documentation in README
- Updated roadmap to reflect symbol localization as implemented

### Fixed
- Missing imports for KICAD_ENV_FOOTPRINT_DIR, KICAD_ENV_3DMODEL_DIR, KICAD_ENV_SYMBOL_DIR in library_manager.py
- README now accurately reflects current implementation (symbols fully implemented)

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

- Support for hierarchical schematics

---

[1.0.0]: https://github.com/bakery-kicad/Bakery/releases/tag/v1.0.0
