# Bakery - KiCad Plugin

**Localize all KiCad symbols, footprints, and 3D models to project libraries**

## Overview

Bakery is a KiCad plugin that automates the process of copying global library symbols, footprints, and 3D models into project-local libraries. This ensures:
- **Project portability**: No external library dependencies
- **Version stability**: Libraries won't change if global libraries are updated
- **Self-contained projects**: Everything needed is in the project folder

## Installation

### Windows - Quick Install (Recommended)

1. Download or clone this repository
2. Run `install.bat` - this will automatically copy the plugin to your KiCad plugins directory
3. Restart KiCad

### Manual Installation

1. Download or clone this repository
2. Copy the `Bakery` folder to your KiCad plugins directory:
   - **Windows**: `%USERPROFILE%\Documents\KiCad\9.0\scripting\plugins\`
   - **Linux**: `~/.kicad/9.0/scripting/plugins/`
   - **macOS**: `~/Library/Preferences/kicad/9.0/scripting/plugins/`
3. Restart KiCad

### Via KiCad Plugin Manager (Future)

Once published to the KiCad Plugin and Content Manager, you can install directly from KiCad.

## Usage

1. Open your KiCad project and PCB file in pcbnew
2. Go to **Tools** > **External Plugins** > **Bakery - Localize Symbols, Footprints, and 3d Models**
3. Configure options in the dialog:
   - Local library name for footprints (default: "MyLib")
   - Symbol library name (default: "MySymbols")
   - Symbol directory name (default: "Symbols")
   - 3D models folder name (default: "3D Models")
   - Enable/disable automatic backups
4. Confirm the operation
5. The plugin will:
   - Create local `.pretty` folders for footprints
   - Create local symbol library (`.kicad_sym`) in Symbols directory
   - Create local `3D Models` folder for 3D models
   - Copy all used symbols, footprints, and their associated 3D models
   - Update `fp-lib-table` and `sym-lib-table` to include local libraries
   - Update references in both PCB and schematic files to point to local libraries
   - Create backups of modified files (if enabled)

## Project Structure After Localization

```
YourProject/
├── YourProject.kicad_pro
├── YourProject.kicad_pcb
├── YourProject.kicad_sch
├── fp-lib-table              # Updated with local footprint library
├── sym-lib-table             # Updated with local symbol library
├── MyLib.pretty/             # Local footprint library
│   ├── Footprint1.kicad_mod
│   └── Footprint2.kicad_mod
├── Symbols/                  # Local symbol libraries
│   └── MySymbols.kicad_sym  # Local symbol library
└── 3D Models/                # Local 3D models
    ├── model1.step
    └── model2.wrl
```

## Development

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for development guidelines and architecture details.

### Project Architecture

```
Bakery/
├── __init__.py              # Plugin registration and metadata
├── bakery_plugin.py         # Main plugin class (ActionPlugin interface)
├── constants.py             # Configuration constants and messages
├── ui_components.py         # Logger window and configuration dialog
├── footprint_localizer.py   # Footprint and 3D model localization
├── symbol_localizer.py      # Symbol localization
├── library_manager.py       # Footprint library table management
├── sexpr_parser.py          # S-expression parser
├── backup_manager.py        # File backup utilities
├── utils.py                 # Shared utility functions
└── metadata.json            # Plugin metadata for KiCad Plugin Manager
```

### Testing

1. Make changes to the Python files
2. Restart KiCad completely
3. Open a test project
4. Run the plugin from **Tools** > **External Plugins**
5. Check the log window for detailed output

## Features

✅ **Symbol Localization**: Automatically copies all symbols from global libraries to your project
✅ **Footprint Localization**: Automatically copies all footprints from global libraries to your project
✅ **3D Model Localization**: Copies associated 3D models and updates paths
✅ **Automatic Reference Updates**: Updates PCB, schematics, and library tables
✅ **Dual Scanning**: Scans both PCB and schematic files for complete coverage
✅ **Backup Creation**: Creates timestamped backups before modifying files
✅ **Progress Tracking**: Visual progress bar with step-by-step status
✅ **Detailed Logging**: Separate panes for info, warnings, and errors
✅ **Configurable**: Choose library names, directories, and backup options
✅ **Path Safety**: Validates all file operations to prevent data loss
✅ **KiCad 8 & 9 Support**: Compatible with both KiCad version 8 and 9

## Requirements

- KiCad 9.0 or later
- Python 3.x (bundled with KiCad)
- wxPython (bundled with KiCad)

## Configuration

When you run Bakery, you can configure:
- **Local Footprint Library Name**: Name for the local footprint library (default: "MyLib")
- **Symbol Library Name**: Name for the local symbol library file (default: "MySymbols")
- **Symbol Directory Name**: Name for the symbol library directory (default: "Symbols")
- **3D Models Folder**: Name for the 3D models folder (default: "3D Models")
- **Create Backups**: Whether to backup files before modification (recommended)

## License

GNU General Public License v3.0 - see LICENSE file

## Contributing

Contributions welcome! Please open an issue or pull request.

## Roadmap

### Version 1.0 (Released)
- [x] Symbol localization from global to project libraries
- [x] Footprint localization from global to project libraries
- [x] 3D model localization with path updates
- [x] Dual scanning (PCB and schematic files)
- [x] Progress dialog with detailed logging (info/warning/error panes)
- [x] Configuration dialog for all options
- [x] PCB and schematic file updates
- [x] Symbol and footprint library table management
- [x] Automatic timestamped backup creation
- [x] KiCad 8 & 9 environment variable compatibility

### Planned for Future Versions
- [ ] Support for hierarchical schematics
