# Bakery - KiCad Plugin - AI Coding Agent Instructions

## Project Overview
KiCad plugin to localize all KiCad symbols and footprints. Built in Python using KiCad's pcbnew/eeschema APIs.

**Purpose**: Automate the process of copying global library symbols and footprints into project-local libraries, eliminating external dependencies.

**Tech Stack**: 
- Python 3.x (KiCad's embedded Python)
- KiCad pcbnew API (for PCB/footprints)
- KiCad eeschema API (for schematics/symbols)
- wxPython for UI dialogs

## Architecture
```
Bakery KiCad Plugin
├── Plugin Entry Point (ActionPlugin interface)
│   └── bakery_plugin.py
├── Footprint Localizer (processes footprints and 3D models)
│   └── footprint_localizer.py
├── Library Manager (creates/manages local libraries)
│   └── library_manager.py
├── S-Expression Parser (parses KiCad file format)
│   └── sexpr_parser.py
├── UI Components (logging and configuration dialogs)
│   └── ui_components.py
├── Backup Manager (file backup utilities)
│   └── backup_manager.py
└── Constants (configuration and messages)
    └── constants.py
```

### Major Components
- **Plugin Core** (`bakery_plugin.py`): Main ActionPlugin class registered with KiCad, orchestrates the localization process
- **Footprint Localizer** (`footprint_localizer.py`): Scans PCB/schematics, copies footprints and 3D models to project
- **Library Manager** (`library_manager.py`): Creates/updates fp-lib-table, manages library metadata
- **S-Expression Parser** (`sexpr_parser.py`): Parses and serializes KiCad S-expression format
- **UI Components** (`ui_components.py`): Logger window with progress bar, configuration dialog
- **Backup Manager** (`backup_manager.py`): Creates timestamped backups before file modifications
- **Constants** (`constants.py`): Centralized configuration values and UI messages

## Project-Specific Conventions

### Code Style
- Follow PEP 8 for Python code
- Class names: `PascalCase` (e.g., `BakeryPlugin`, `SymbolLocalizer`)
- Functions/methods: `snake_case` (e.g., `localize_symbols`, `copy_footprint`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `PLUGIN_VERSION`, `DEFAULT_LIB_NAME`)
- KiCad API objects use KiCad's naming (e.g., `GetBoard()`, `GetFootprints()`)

### Docstring Format (Doxygen Style)
Use Doxygen-style docstrings for all classes, functions, and methods:

```python
def copy_footprint(source_path, dest_path, footprint_name):
    """
    @brief Copy a footprint from global library to local project library
    
    @param source_path: Absolute path to source .kicad_mod file
    @param dest_path: Absolute path to destination .pretty folder
    @param footprint_name: Name of the footprint to copy
    
    @return True if copy successful, False otherwise
    
    @throws IOError if source file not found
    @throws PermissionError if cannot write to destination
    """
    pass

class SymbolLocalizer:
    """
    @brief Handles localization of schematic symbols from global to local libraries
    
    Scans .kicad_sch files, identifies external symbol references, and copies
    them to project-local .kicad_sym files.
    """
    pass
```

**Doxygen Tags to Use:**
- `@brief` - Short description (first line)
- `@param` - Parameter description
- `@return` - Return value description
- `@throws` / `@exception` - Exceptions that may be raised
- `@note` - Additional notes or warnings
- `@see` - Cross-references to related functions/classes

### Error Handling
- Use try/except for KiCad API calls (can fail if board/schematic not loaded)
- Show user-friendly wx.MessageBox dialogs for errors
- Log detailed errors to KiCad's scripting console
- Never crash KiCad - always catch exceptions at plugin boundaries

### Testing Strategy
- Manual testing within KiCad required (no easy unit test framework)
- Test with various KiCad project structures
- Verify symbol/footprint integrity after localization
- Test on both Windows and Linux (if applicable)

## Development Workflows

### Setup
```bash
# Install to KiCad plugins directory

# Windows (Quick Install):
install.bat

# Windows (Manual):
# Copy to %USERPROFILE%\Documents\KiCad\9.0\scripting\plugins\Bakery

# Linux:
cp -r Bakery ~/.kicad/9.0/scripting/plugins/

# macOS:
cp -r Bakery ~/Library/Preferences/kicad/9.0/scripting/plugins/

# Restart KiCad to load the plugin
```

### Running the Project
```bash
# The plugin runs within KiCad:
# 1. Open KiCad PCB Editor (pcbnew)
# 2. Tools > External Plugins > Bakery - Localize Symbols, Footprints, and 3d Models
# 3. Configure options in dialog (library name, backups, etc.)
# 4. Plugin executes and shows progress window

# To reload after changes:
# - Close and reopen KiCad (or use Plugin and Content Manager)

# Files structure:
- `__init__.py` - Plugin registration and metadata
- `bakery_plugin.py` - Main ActionPlugin class
- `footprint_localizer.py` - Footprint and 3D model localization logic
- `library_manager.py` - Library creation and management
- `sexpr_parser.py` - S-expression parsing utilities
- `ui_components.py` - Logger window and configuration dialog
- `backup_manager.py` - File backup handling
- `constants.py` - Configuration constants
- `Bakery_Icon.png` - Plugin icon (24x24px)
- `metadata.json` - Plugin metadata for KiCad 9.0+ Plugin Manager
```

## Integration Points

### KiCad Python API (pcbnew)
- **Purpose**: Interact with PCB files, footprints, and libraries
- **Key classes**: `BOARD`, `FOOTPRINT`, `PCB_IO`, `PLUGIN`
- **Documentation**: KiCad Python API docs (https://docs.kicad.org/doxygen-python/)
- **Import**: `import pcbnew`

### KiCad Schematic API (eeschema)
- **Purpose**: Interact with schematic files and symbols
- **Note**: API is more limited than pcbnew
- **File parsing**: May need to parse `.kicad_sch` as S-expressions


### Testing Changes
1. Save Python files
2. Close KiCad completely
3. Reopen KiCad and load a test project
4. Run plugin from Tools > External Plugins
5. Check Scripting Console for errors

### Accessing KiCad API Documentation
- Doxygen: https://docs.kicad.org/doxygen-python/
- Python console exploration: Use `dir(pcbnew)` to discover available functions
- Example projects: Check KiCad forum and GitHub for plugin examples

### Working with S-Expressions
- KiCad files use S-expression format (Lisp-like syntax)
- Can parse with `pcbnew.SEXPR_PARSER` or custom parser
- Example: `(symbol "Device:R" ...)`

### Plugin Icon
- 24x24px PNG recommended
- Stored as `icon.png` in plugin directory
- Referenced in plugin metadata

---

**KiCad Version Compatibility**: Currently targeting KiCad 8.0+. API may differ in older versions
- **Schematics**: `.kicad_sch` (S-expression, contains symbol references)
- **PCB**: `.kicad_pcb` (S-expression, contains footprint references)
- **Symbol libraries**: Can be in project or global locations
- **Footprint libraries**: `.pretty` folders containing `.kicad_mod` filesod, key endpoints
- Example: **Stripe API**: Payment processing, API keys in env vars, wrapper in `src/payments/`

## Database Schema
<!-- Document key tables/collections and relationships -->
- Add schema overview once database is designed
- Document any important migrations or seeding procedures

## Deployment
<!-- Document deployment process -->
- Environment: [staging/production details]
- CI/CD: [pipeline location and key steps]
- Configuration: [environment-specific settings]

## Common Tasks
<!-- Document frequent operations -->
- Adding a new API endpoint: [steps and file locations]
- Adding a new database model: [steps and conventions]
- Updating dependencies: [process and testing requirements]

---

**Note**: This is a template. Update each section as the project develops with specific examples from the actual codebase.
