# Bakery v1.0.1 - Initial Release

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
