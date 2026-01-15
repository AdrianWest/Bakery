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
PLUGIN_VERSION = "0.2.0"
PLUGIN_NAME = "Bakery - Localize Symbols, Footprints, and 3D Models"
PLUGIN_CATEGORY = "Library Management"
PLUGIN_DESCRIPTION = "Localize all symbols and footprints to project libraries"

# UI Constants
LOGGER_WINDOW_SIZE = (900, 700)
CONFIG_DIALOG_SIZE = (450, 400)

# Color schemes
COLOR_WARNING_BG = (255, 252, 240)  # Light yellow
COLOR_ERROR_BG = (255, 240, 240)    # Light red

# Font settings
LOG_FONT_SIZE = 9

# Library naming
DEFAULT_LOCAL_LIB_NAME = "MyLib"
DEFAULT_SYMBOL_LIB_NAME = "MySymbols"
DEFAULT_SYMBOL_DIR_NAME = "MySym"
DEFAULT_MODELS_DIR_NAME = "3D Models"

# File extensions
EXTENSION_FOOTPRINT = ".kicad_mod"
EXTENSION_FOOTPRINT_LIB = ".pretty"
EXTENSION_SYMBOL = ".kicad_sym"
EXTENSION_SCHEMATIC = ".kicad_sch"
EXTENSION_PCB = ".kicad_pcb"
EXTENSION_FP_LIB_TABLE = "fp-lib-table"
EXTENSION_SYM_LIB_TABLE = "sym-lib-table"

# KiCad version compatibility
KICAD_VERSION_PRIMARY = "9.0"
KICAD_VERSION_FALLBACK = "8.0"
KICAD_VERSIONS = [KICAD_VERSION_PRIMARY, KICAD_VERSION_FALLBACK]

# Environment variables
ENV_VAR_PREFIX_PRIMARY = "KICAD9_"
ENV_VAR_PREFIX_FALLBACK = "KICAD8_"
ENV_VAR_PREFIX_GENERIC = "KICAD_"
ENV_VAR_KIPRJMOD = "KIPRJMOD"

# Common KiCad environment variables
KICAD_ENV_FOOTPRINT_DIR = "FOOTPRINT_DIR"
KICAD_ENV_3DMODEL_DIR = "3DMODEL_DIR"
KICAD_ENV_SYMBOL_DIR = "SYMBOL_DIR"

# Backup settings
BACKUP_SUFFIX = ".bak"
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

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

# Library type
LIBRARY_TYPE_KICAD = "KiCad"

# Progress tracking
PROGRESS_STEP_SCAN_PCB = "Scanning PCB"
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
ERROR_BACKUP_FAILED = "Failed to create backup file"

# Success messages
SUCCESS_LOCALIZATION_COMPLETE = "Localization complete!"

# Confirmation messages
CONFIRM_LOCALIZATION = (
    "This will copy all global symbols, footprints, and 3D models to local project libraries.\n\n"
    "A backup will be created before modifying any files.\n\n"
    "Continue?"
)

# Config keys
CONFIG_LOCAL_LIB_NAME = "local_lib_name"
CONFIG_SYMBOL_LIB_NAME = "symbol_lib_name"
CONFIG_SYMBOL_DIR_NAME = "symbol_dir_name"
CONFIG_MODELS_DIR_NAME = "models_dir_name"
CONFIG_CREATE_BACKUPS = "create_backups"
