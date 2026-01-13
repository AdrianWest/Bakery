# Bakery - KiCad Plugin

**Localize all KiCad symbols and footprints to project libraries**

## Overview

Bakery is a KiCad plugin that automates the process of copying global library symbols and footprints into project-local libraries. This ensures:
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
   - **Windows**: `%APPDATA%\kicad\9.0\scripting\plugins\`
   - **Linux**: `~/.kicad/9.0/scripting/plugins/`
   - **macOS**: `~/Library/Preferences/kicad/9.0/scripting/plugins/`
3. Restart KiCad

### Via KiCad Plugin Manager (Future)

Once published to the KiCad Plugin and Content Manager, you can install directly from KiCad.

## Usage

1. Open your KiCad project and PCB file in pcbnew
2. Go to **Tools** > **External Plugins** > **Bakery - Localize Symbols, Footprints, and 3d Models**
3. Configure options in the dialog (library name, backups, etc.)
4. Confirm the operation
5. The plugin will:
   - Create local `.pretty` folders for footprints
   - Create local `3D Models` folder for 3D models
   - Copy all used footprints and their associated 3D models
   - Update references in both PCB and schematic files to point to local libraries
   - Create backups of modified files (if enabled)

## Project Structure After Localization

```
YourProject/
├── YourProject.kicad_pro
├── YourProject.kicad_pcb
├── YourProject.kicad_sch
├── fp-lib-table              # Updated with local library
├── MyLib.pretty/             # Local footprint library
│   ├── Footprint1.kicad_mod
│   └── Footprint2.kicad_mod
└── 3D Models/                # Local 3D models
    ├── model1.step
    └── model2.wrl
```

## Development

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for development guidelines and architecture details.

### Project Architecture

```
Bakery/
├── bakery_plugin.py         # Main plugin class (ActionPlugin interface)
├── constants.py             # Configuration constants
├── ui_components.py         # Logger and configuration dialog
├── footprint_localizer.py   # Footprint and 3D model handling
├── library_manager.py       # Library table management
├── sexpr_parser.py          # S-expression parser
└── backup_manager.py        # File backup utilities
```

### Testing

1. Make changes to the Python files
2. Restart KiCad completely
3. Open a test project
4. Run the plugin from **Tools** > **External Plugins**
5. Check the log window for detailed output

## Features

✅ **Footprint Localization**: Automatically copies all footprints from global libraries to your project
✅ **3D Model Localization**: Copies associated 3D models and updates paths
✅ **Automatic Reference Updates**: Updates both PCB and schematic files
✅ **Backup Creation**: Creates backups before modifying files
✅ **Progress Tracking**: Visual progress bar and detailed logging
✅ **Configurable**: Choose library names and options via dialog

## Requirements

- KiCad 9.0 or later
- Python 3.x (bundled with KiCad)
- wxPython (bundled with KiCad)

## Configuration

When you run Bakery, you can configure:
- **Local Library Name**: Name for the local footprint library (default: "MyLib")
- **3D Models Folder**: Name for the 3D models folder (default: "3D Models")
- **Create Backups**: Whether to backup files before modification (recommended)

## License

GNU General Public License v3.0 - see LICENSE file

## Contributing

Contributions welcome! Please open an issue or pull request.

## Roadmap

- [x] Footprint localization
- [x] 3D model localization
- [x] Progress dialog and detailed logging
- [x] Configuration options (library naming, backups)
- [x] PCB and schematic file updates
- [x] Automatic backup creation
- [ ] Symbol localization (planned for v2.0)
- [ ] Support for hierarchical schematics
- [ ] Batch processing multiple projects
- [ ] Undo/rollback functionality
