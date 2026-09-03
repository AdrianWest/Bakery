# Bakery - Release Notes

## v2.1.0 - Portable Project Backups, Datasheets, and Release Validation

### Overview
This release restores mandatory KiCad-compatible project ZIP backups before
localization and expands Bakery's portability coverage for KiCad 10 projects.
It also improves collision-safe localization, datasheet handling, repeat-run
safety, and automated release validation.

### What's New in v2.1.0
- **Mandatory KiCad project backups** - Bakery creates a timestamped
  `<project>-backups/<project>-YYYY-MM-DD_HHMMSS.zip` archive before changing
  project files. Restore backups with KiCad Project Manager's
  **File** > **Unarchive Project...** command.
- **Datasheet localization improvements** - Datasheets are scanned from both
  schematics and PCB files, TI redirect URLs are resolved before download, and
  invalid or truncated PDFs are rejected before replacing local files.
- **Collision-safe local names** - Symbols, footprints, 3D models, and
  datasheets use stable source-hash naming when needed so same-named external
  resources do not overwrite each other.
- **Safer repeat runs** - Already-local symbols, footprints, models, and
  datasheets remain stable on subsequent Bakery runs.
- **Stronger functional release tests** - The Windows KiCad 10 functional suite
  now reopens both the localized PCB and root schematic in KiCad after
  localization and idempotence checks.

### Compatibility
- Bakery v2.1.0 targets **KiCad 10.x**.
- Legacy `${KICAD9_*}` variables in project files are accepted as input and
  normalized to KiCad 10 equivalents when localizing, but Bakery is not a KiCad
  8/9 runtime plugin in this release line.

---

## v2.0.0 - KiCad 10 Support and Backup Policy Update

### Overview
This release targets KiCad 10 and removes the automatic backup option from the plugin configuration. It also fixes the false warning that appeared while processing datasheet updates.

### What's New in v2.0.0
- **KiCad 10 support** - Updated for KiCad 10 project structure and plugin behavior.
- **No automatic backups** - The configuration dialog no longer includes a backup checkbox, and the plugin does not create backups during localization.
- **False warning fixed** - The warning message about failed backup creation no longer appears when backup creation has intentionally been disabled.
- **Datasheet copies remain active** - Datasheets still copy to the project-local `Data_Sheets` folder and references are updated to use `${KIPRJMOD}`.
- **Git-first safety** - The recommended recovery workflow is to use Git or an external version-control/backup process before running the plugin.

### Refactored Areas in v2.0.0
- **Plugin entry and configuration** - Refined the main plugin flow and cleaned up the configuration dialog in `bakery_plugin.py` and `ui_components.py`.
- **Backup policy** - Moved backup handling to a single no-backup default path across `backup_manager.py` and `base_localizer.py`.
- **Datasheet localization flow** - Updated the datasheet update path in `data_sheet_localizer.py` to avoid false backup warnings while continuing to copy files locally.
- **Constants and messaging** - Simplified the plugin messages and config defaults in `constants.py` to match the KiCad 10 behavior and the no-backup policy.
- **Library update logic** - Kept the footprint/symbol localization pipeline aligned with the current KiCad 10 project layout and library table behaviors.

> Note: This release supports a KiCad 10 project that still references 9.x global libraries. Bakery will localize those 9.x library references into the project without requiring the project to be rebuilt from scratch or converted away from its current KiCad 10 format.

---

## v1.1.0 - Datasheet Copy and Icon Enhancement (February 22, 2026)

### Overview
This release adds new functionality to copy component datasheets to the project and enhances icon handling for better visual integration.

### What's New in v1.1.0

#### Datasheet Localization
- **Datasheet copying** - Automatically copies component datasheets referenced in symbols and footprints to project directory
- **Datasheet library management** - Creates and manages project-local datasheet library
- **Path updates** - Updates datasheet references in symbols and footprints to point to local copies
- **Preserves datasheet organization** - Maintains original datasheet file structure when copying

#### Icon Improvements
- **Enhanced icon support** - Improved icon handling and display in KiCad plugin interface
- **Icon localization** - Support for copying component icons to project libraries
- **Better visual integration** - Enhanced plugin icon display in KiCad menus

#### Technical Improvements
- Additional file handling for datasheet and icon resources
- Extended S-expression parser to handle datasheet properties
- Improved progress tracking for datasheet operations

### Installation
Install via KiCad Plugin and Content Manager or use the install.bat script.

### Upgrading from v1.0.2
Simply install v1.1.0 through the Plugin and Content Manager, or run the install script. All settings and functionality from previous versions are preserved.

---

## v1.0.2 - PCM Compliance Update (January 19, 2026)

### Overview
This maintenance release addresses KiCad Plugin and Content Manager (PCM) metadata validation issues, improves the release automation process, and reorganizes project structure. No functional changes to the plugin itself.

### What's New in v1.0.2

#### PCM Metadata Fixes
- **Removed invalid tags** - Cleaned up metadata.json to include only PCM-compliant tags ("pcbnew" and "library")
- **Fixed UTF-8 encoding** - Removed BOM (Byte Order Mark) from metadata.json files that was causing validation errors
- **Schema compliance** - Ensured full compliance with KiCad PCM v1 schema
- **Automatic BOM cleanup** - create_release.bat now automatically removes BOM from metadata files after updates

#### Project Structure Improvements
- **Reorganized resources** - Moved resources folder inside plugins directory for better organization
- **Updated icon path** - Plugin now uses high-resolution 256x256 icon from plugins/resources/
- **Consistent file structure** - Aligns with KiCad plugin best practices

#### Release Automation Enhancements
- **Dual metadata updates** - create_release.bat now updates both root and plugins/metadata.json files
- **Automatic version updates** - Both metadata files get version number synchronized
- **Automatic URL generation** - Download URL is now generated automatically during release process
- **Automatic BOM removal** - UTF-8 BOM cleanup runs after all metadata updates
- **Streamlined workflow** - Reduced manual steps in release checklist

#### Documentation Updates
- **Merged release notes** - Consolidated versioned release notes into single RELEASE_NOTES.md
- **Updated PCM checklist** - Reflects new automation features
- **Updated CHANGELOG** - Complete history of all changes

### Installation
Install via KiCad Plugin and Content Manager or use the install.bat script.

### Upgrading from v1.0.1
Simply install v1.0.2 through the Plugin and Content Manager, or run the install script. All settings and functionality remain the same.

---

## v1.0.1 - Initial Release (January 18, 2026)

## Overview

Bakery is a KiCad plugin that automates the localization of symbols, footprints, and 3D models from global libraries to project-local libraries. This ensures project portability and version stability.

## Features

### Core Functionality
- **Symbol Localization** - Copy symbols from global to project libraries
- **Footprint Localization** - Copy footprints to project .pretty libraries  
- **3D Model Localization** - Copy and update 3D model references
- **Dual Scanning** - Scans both PCB and schematic files for comprehensive coverage
- **Hierarchical Schematic Support** - Recursively processes all schematic files

### User Experience
- **Interactive Configuration Dialog** - Customize library names and backup options
- **Real-time Progress Tracking** - Visual progress bar with step-by-step updates
- **Comprehensive Logging** - Separate panes for info, warnings, and errors
- **Automatic Backups** - Creates timestamped backups before file modifications
- **File Lock Detection** - Prevents modification of files open in editors

### Technical Highlights
- **Comprehensive Unit Test Suite** - 158 tests with 100% pass rate
- **KiCad 8.0 and 9.0 Compatible** - Supports both versions
- **Doxygen Documentation** - Complete API documentation
- **Safe Path Validation** - Prevents directory traversal attacks
- **S-Expression Parser** - With LRU caching for performance

## Installation

### Via Install Script (Windows)
```batch
install.bat
```

### Manual Installation
1. Copy the `plugins` folder contents to:
   - Windows: `%USERPROFILE%\Documents\KiCad\9.0\scripting\plugins\Bakery`
   - Linux: `~/.kicad/9.0/scripting/plugins/Bakery`
   - macOS: `~/Library/Preferences/kicad/9.0/scripting/plugins/Bakery`
2. Restart KiCad

## Usage

1. Open your KiCad PCB project
2. Go to **Tools > External Plugins > Bakery**
3. Configure library names and options
4. Click OK to start localization
5. Review the log for details

## System Requirements

- KiCad 9.0 or later
- Python 3.8+ (bundled with KiCad)
- Windows, Linux, or macOS

## What's Included

- **Complete Plugin Files** - All Python modules and dependencies
- **High-Resolution Icons** - 256x256 plugin icon
- **License** - GPL-3.0
- **Documentation** - README with comprehensive instructions

## Known Limitations

- Requires PCB to be saved before running
- Does not modify source library files (read-only)
- Symbol library table management in development

## Support

- **Issues**: https://github.com/AdrianWest/Bakery/issues
- **Repository**: https://github.com/AdrianWest/Bakery
- **Documentation**: See README.md

## Release Files

- **Bakery-1.0.0.zip** (139 KB)
  - SHA256: `0683e518bd70c163b5bdb5eb50e47960df6e4d1d0f38aadcab104bce12bebd22`
  - Installed Size: 371 KB

## Acknowledgments

Built for the KiCad community to simplify project management and improve portability.
