# Bakery v1.0.2 - PCM Compliance Update

## Overview

This maintenance release addresses KiCad Plugin and Content Manager (PCM) metadata validation issues and improves the release automation process. No functional changes to the plugin itself.

## What's New in v1.0.2

### PCM Metadata Fixes
- **Removed invalid tags** - Cleaned up metadata.json to include only PCM-compliant tags ("pcbnew" and "library")
- **Fixed UTF-8 encoding** - Removed BOM (Byte Order Mark) from metadata.json files that was causing validation errors
- **Schema compliance** - Ensured full compliance with KiCad PCM v1 schema

### Release Automation Improvements
- **Automatic version updates** - create_release.bat now automatically updates version number in metadata.json
- **Automatic URL generation** - Download URL is now generated automatically during release process
- **Streamlined workflow** - Reduced manual steps in release checklist

## Installation

### Via KiCad Plugin and Content Manager (Recommended)
1. Open KiCad
2. Go to **Plugin and Content Manager**
3. Search for "Bakery"
4. Click Install

### Manual Installation
```batch
install.bat
```

Or copy to your KiCad plugins directory and restart KiCad.

## Upgrading from v1.0.1

Simply install v1.0.2 through the Plugin and Content Manager, or run the install script. All settings and functionality remain the same.

## Full Feature List

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

## System Requirements

- KiCad 8.0 or later
- Python 3.8+ (bundled with KiCad)
- Windows, Linux, or macOS

## Support

- **Issues**: https://github.com/AdrianWest/Bakery/issues
- **Repository**: https://github.com/AdrianWest/Bakery
- **Documentation**: See README.md

## Changes Since v1.0.1

See [CHANGELOG.md](CHANGELOG.md) for complete details.

### Changed
- PCM metadata validation improvements
- UTF-8 encoding without BOM for metadata.json files
- Release automation enhancements
- Updated PCM_RELEASE_CHECKLIST.md

### Fixed
- UTF-8 BOM issue causing PCM validation errors
- Invalid tag schema violations in KiCad PCM

---

**Release Date**: January 19, 2026  
**License**: GPL-3.0  
**Download**: [Bakery-1.0.2.zip](https://github.com/AdrianWest/Bakery/releases/download/v1.0.2/Bakery-1.0.2.zip)
