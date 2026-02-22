# Bakery - KiCad Plugin

**Localize all KiCad symbols, footprints, and 3D models to project libraries**

---

## ⚠️ **IMPORTANT: Use Version Control!** ⚠️

### **This plugin makes extensive changes to your schematic and PCB files.**

### **Put your KiCad project on a Git repository BEFORE running this plugin!**

**Why?**
- Bakery modifies `.kicad_sch` and `.kicad_pcb` files extensively
- The easiest way to recover from an unwanted conversion is to revert from Git
- Backups are created automatically, but Git gives you full project history

**Quick Git setup (if you don't have one):**
```bash
cd /path/to/your/project
git init
git add .
git commit -m "Before Bakery localization"
```

---

## Overview

Bakery is a KiCad plugin that automates the process of copying global library symbols, footprints, and 3D models into project-local libraries. The plugin **"bakes in"** all external dependencies, converting references from global libraries to local project files. This ensures:
- **Project portability**: No external library dependencies - everything is baked into your project
- **Version stability**: Libraries won't change if global libraries are updated
- **Self-contained projects**: All files and dependencies are contained in the project folder
- **Complete independence**: Share projects without worrying about missing libraries

## Installation
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
✅ **KiCad 9 Support**: Compatible with both KiCad version 9

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

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## Roadmap

### Version 1.0 (In Development - Unreleased)
- [x] Symbol localization from global to project libraries
- [x] Footprint localization from global to project libraries
- [x] 3D model localization with path updates
- [x] Dual scanning (PCB and schematic files)
- [x] Progress dialog with detailed logging (info/warning/error panes)
- [x] Configuration dialog for all options
- [x] PCB and schematic file updates
- [x] Symbol and footprint library table management
- [x] Automatic timestamped backup creation
- [x] KiCad 9 environment variable compatibility
- [x] Comprehensive Doxygen documentation
- [x] Support for hierarchical schematics (tested)
- [x] Full testing and bug fixes

### Planned for Future Versions
- [ ] Additional features based on user feedback

## Testing

### Unit Tests

Run the comprehensive unit test suite (151 tests covering all modules):

```bash
cd "Unit Test"
python run_tests.py              # Run all tests
python run_tests.py -v           # Verbose output
python run_tests.py --coverage   # With coverage report (requires: pip install coverage)
python run_tests.py --list       # List all available tests
```

**Test Coverage:**
- ✅ 151 tests across 10 test modules
- ✅ All modules covered: constants, utils, sexpr_parser, backup_manager, library_manager, base_localizer, footprint_localizer, symbol_localizer, ui_components, bakery_plugin
- ✅ 0 failures, 0 errors, 0 skipped

See [Unit Test/README.md](Unit%20Test/README.md) for detailed testing documentation.

### Manual Testing in KiCad

**Test Projects:**

Two functional test projects are provided in `Functional Test/`:
- **Ki-Test 01** - Should report 1 expected error (missing 3D model file)
- **Ki-Test 02** - Should complete with no errors

**Testing Procedure:**

1. Copy test projects from `C:\GIT_HUB\Bakery\Functional Test` to your KiCad projects folder
2. Make changes to the Bakery Python files (if developing)
3. Restart KiCad completely
4. Open a test project (e.g., Ki-Test 01)
5. Run the plugin from **Tools** > **External Plugins** > **Bakery - Localize Symbols, Footprints, and 3d Models**
6. Check the log window for detailed output

**Expected Results:**
- **Ki-Test 01**: Should report 1 error:
  ```
  ✗ Model file not found: C:\Program Files\KiCad\9.0\share\kicad\3dmodels\Button_Switch_THT.3dshapes\KSA_Tactile_SPST.step
  • 1 models could not be copied
  ```
- **Ki-Test 02**: Should complete with no errors

**Verification Checklist:**

After running the plugin, verify the following:

**In the Schematic (`.kicad_sch`):**
- [ ] All symbol `lib_id` fields now reference the local library (e.g., `"MySymbols:R"` instead of `"Device:R"`)
- [ ] Symbol properties are preserved (reference designators, values, etc.)
- [ ] Schematic visual appearance is unchanged
- [ ] No missing symbols or broken references

**In the PCB (`.kicad_pcb`):**
- [ ] All footprint `fp_text` references updated to local library (e.g., `"MyLib:R_0805"`)
- [ ] 3D model paths updated to `${KIPRJMOD}/3D Models/` for copied models
- [ ] Footprint positions, rotations, and layers unchanged
- [ ] Copper traces, zones, and routing intact
- [ ] PCB visual appearance identical to before

**In the Project Files:**
- [ ] `fp-lib-table` contains entry for local footprint library
- [ ] `sym-lib-table` contains entry for local symbol library
- [ ] Local libraries created: `MyLib.pretty/`, `Symbols/MySymbols.kicad_sym`, `3D Models/`
- [ ] Backup files created with timestamps (if enabled)
- [ ] All footprints copied to `MyLib.pretty/`
- [ ] All symbols present in `Symbols/MySymbols.kicad_sym`
- [ ] 3D models copied to `3D Models/` folder

**Functional Tests:**
- [ ] Open schematic - no missing symbol warnings
- [ ] Open PCB - no missing footprint warnings
- [ ] 3D viewer shows models correctly (except intentionally missing ones)
- [ ] New Symbol libaries should open in the editor without error
- [ ] New Footprint libaries should open in the editor without error
- [ ] DRC (Design Rule Check) runs without new errors
- [ ] ERC (Electrical Rule Check) runs without new errors
- [ ] Project can be opened on a different computer without KiCad global libraries
