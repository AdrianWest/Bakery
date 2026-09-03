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
@file constants.py

@brief Configuration constants for Bakery KiCad Plugin

This module defines all constants used throughout the plugin including:
- Plugin metadata (name, version, description)
- UI configuration (window sizes, colors, fonts)
- File extensions and naming conventions
- KiCad version compatibility settings  
- Environment variable names
- S-expression keywords
- Error/success/confirmation messages
- Configuration keys

@section description_constants Detailed Description
Centralized constant definitions for the entire Bakery plugin. All configuration
values, UI strings, file extensions, and KiCad-specific keywords are defined here
to maintain consistency and simplify maintenance.

@section notes_constants Notes
- Update PLUGIN_VERSION when releasing new versions
- UI strings support future internationalization
- KiCad version compatibility handled via environment variable mappings
"""


# Plugin metadata
PLUGIN_VERSION = "2.1.0"
PLUGIN_NAME = "Bakery - Localize Symbols, Footprints, and 3D Models"
PLUGIN_CATEGORY = "Library Management"
PLUGIN_DESCRIPTION = "Localize all symbols and footprints to project libraries"

# UI Constants
LOGGER_WINDOW_SIZE = (900, 850)
CONFIG_DIALOG_SIZE = (520, 610)
CONFIG_BANNER_DISPLAY_WIDTH = 490
CONFIG_BANNER_FILE_NAME = "Banner-No-robot.png"
LOGGER_BANNER_DISPLAY_WIDTH = 850
LOGGER_BANNER_FILE_NAME = "Banner-No-BK.png"
COMPLETION_QR_DISPLAY_WIDTH = 140
COMPLETION_QR_FILE_NAME = "qr-code.png"
COMPLETION_SUPPORT_URL = "https://www.buymeacoffee.com/Adrian_West"
COMPLETION_SUPPORT_MESSAGE = (
    "Bakery is completely free and open source. If you like it or it has "
    "helped you, please consider buying me a coffee."
)

# Color schemes
COLOR_WARNING_BG = (255, 252, 240)  # Light yellow
COLOR_ERROR_BG = (255, 240, 240)    # Light red

# Font settings
LOG_FONT_SIZE = 9

# Progress bar settings
PROGRESS_BAR_RANGE = 100
PROGRESS_INITIAL = 0
PROGRESS_COMPLETE = 100

# Progress step percentages
PROGRESS_PCT_SCAN_PCB = 5
PROGRESS_PCT_BACKUP_PROJECT = 2
PROGRESS_PCT_SCAN_SCHEMATICS = 10
PROGRESS_PCT_COPY_FOOTPRINTS = 20
PROGRESS_PCT_COPY_3D_MODELS = 30
PROGRESS_PCT_UPDATE_LIB_TABLE = 40
PROGRESS_PCT_UPDATE_PCB = 45
PROGRESS_PCT_UPDATE_SCHEMATICS = 50
PROGRESS_PCT_SCAN_SYMBOLS = 55
PROGRESS_PCT_COPY_SYMBOLS = 65
PROGRESS_PCT_UPDATE_SYM_LIB_TABLE = 80
PROGRESS_PCT_UPDATE_SYMBOL_REFS = 90

# File size limits
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB
BYTES_PER_KB = 1024
BYTES_PER_MB = 1024 * 1024

# Cache settings
MAX_CACHE_SIZE = 100

# KiCad file format version
# NOTE: Verify against a real KiCad 10 Symbol Editor save before release (see upgrade.md Checkpoint 1.6/6).
KICAD_SYMBOL_VERSION = '20241209'
KICAD_GENERATOR_NAME = 'kicad_symbol_editor'
KICAD_GENERATOR_VERSION = '10.0'

# Library file structure offset
LIB_SYMBOLS_METADATA_COUNT = 4  # version, generator, generator_version fields plus kicad_symbol_lib tag

# Library naming
DEFAULT_LOCAL_LIB_NAME = "MyLib"
DEFAULT_SYMBOL_LIB_NAME = "MySymbols"
DEFAULT_SYMBOL_DIR_NAME = "MySym"
DEFAULT_MODELS_DIR_NAME = "3D Models"
DEFAULT_DATASHEETS_DIR_NAME = "Data_Sheets"

# KiCad-compatible project ZIP backups
PROJECT_BACKUP_DIRECTORY_SUFFIX = "-backups"
PROJECT_BACKUP_TIMESTAMP_FORMAT = "%Y-%m-%d_%H%M%S"

# File extensions
EXTENSION_FOOTPRINT = ".kicad_mod"
EXTENSION_FOOTPRINT_LIB = ".pretty"
EXTENSION_SYMBOL = ".kicad_sym"
EXTENSION_SCHEMATIC = ".kicad_sch"
EXTENSION_PCB = ".kicad_pcb"
EXTENSION_FP_LIB_TABLE = "fp-lib-table"
EXTENSION_SYM_LIB_TABLE = "sym-lib-table"

# KiCad version compatibility - KiCad 10 only. Bakery does not discover or run
# against KiCad 8/9 installations at runtime; see upgrade.md scope policy.
KICAD_VERSION_PRIMARY = "10.0"
KICAD_VERSIONS = [KICAD_VERSION_PRIMARY]

# Environment variables
ENV_VAR_PREFIX_PRIMARY = "KICAD10_"
ENV_VAR_PREFIX_GENERIC = "KICAD_"
ENV_VAR_KIPRJMOD = "KIPRJMOD"

# Legacy versioned path-variable prefixes accepted only as *input* tokens in
# existing project files (e.g. ${KICAD9_FOOTPRINT_DIR}) and normalized to the
# KICAD10_* equivalent before resolution. Never used to look up a KiCad 9/8
# installation, its environment values, or its configuration directories.
LEGACY_ENV_VAR_PREFIXES = ("KICAD9_",)

# Common KiCad environment variables
KICAD_ENV_FOOTPRINT_DIR = "FOOTPRINT_DIR"
KICAD_ENV_3DMODEL_DIR = "3DMODEL_DIR"
KICAD_ENV_SYMBOL_DIR = "SYMBOL_DIR"

# S-expression keywords
SEXPR_LIB = "lib"
SEXPR_NAME = "name"
SEXPR_TYPE = "type"
SEXPR_URI = "uri"
SEXPR_OPTIONS = "options"
SEXPR_DESCR = "descr"
SEXPR_PROPERTY = "property"
SEXPR_FOOTPRINT = "Footprint"
SEXPR_MODEL = "model"
SEXPR_FP_LIB_TABLE = "fp_lib_table"
SEXPR_SYM_LIB_TABLE = "sym_lib_table"
SEXPR_SYMBOL = "symbol"
SEXPR_LIB_SYMBOLS = "kicad_symbol_lib"
SEXPR_LIB_ID = "lib_id"
SEXPR_DATASHEET = "Datasheet"
SEXPR_EXTENDS = "extends"
SEXPR_VERSION = "version"
SEXPR_GENERATOR = "generator"
SEXPR_GENERATOR_VERSION = "generator_version"

# Library type
LIBRARY_TYPE_KICAD = "KiCad"

# Progress tracking
PROGRESS_STEP_SCAN_PCB = "Scanning PCB"
PROGRESS_STEP_BACKUP_PROJECT = "Backing Up Project"
PROGRESS_STEP_SCAN_SCHEMATICS = "Scanning Schematics"
PROGRESS_STEP_SCAN_SYMBOLS = "Scanning Symbols"
PROGRESS_STEP_COPY_FOOTPRINTS = "Copying Footprints"
PROGRESS_STEP_COPY_SYMBOLS = "Copying Symbols"
PROGRESS_STEP_COPY_3D_MODELS = "Copying 3D Models"
PROGRESS_STEP_UPDATE_PCB = "Updating PCB"
PROGRESS_STEP_UPDATE_SCHEMATICS = "Updating Schematics"
PROGRESS_STEP_UPDATE_LIB_TABLE = "Updating Library Table"
PROGRESS_STEP_UPDATE_SYM_LIB_TABLE = "Updating Symbol Library Table"

# Error messages
ERROR_NO_BOARD = "No board loaded. Please open a PCB file first."
ERROR_PROJECT_NOT_SAVED = "Please save the project before running Bakery."
# Success messages
SUCCESS_LOCALIZATION_COMPLETE = "Localization complete!"

# Confirmation messages
CONFIRM_LOCALIZATION = (
    "This will copy all global symbols, footprints, 3D models, and datasheets to local project libraries.\n\n"
    "Continue?"
)

# Config keys
CONFIG_LOCAL_LIB_NAME = "local_lib_name"
CONFIG_SYMBOL_LIB_NAME = "symbol_lib_name"
CONFIG_SYMBOL_DIR_NAME = "symbol_dir_name"
CONFIG_MODELS_DIR_NAME = "models_dir_name"
CONFIG_DATASHEETS_DIR_NAME = "datasheets_dir_name"
