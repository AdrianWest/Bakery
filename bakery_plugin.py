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

"""
@brief Main plugin module for Bakery KiCad Plugin

Provides the ActionPlugin interface for KiCad integration. Coordinates the
localization process for footprints, symbols, and 3D models using specialized
manager classes.
"""

import os
from typing import Dict, Any
import pcbnew
import wx


from .constants import (
    PLUGIN_NAME, PLUGIN_CATEGORY, PLUGIN_DESCRIPTION,
    ERROR_NO_BOARD, ERROR_PROJECT_NOT_SAVED, CONFIRM_LOCALIZATION,
    CONFIG_LOCAL_LIB_NAME, CONFIG_SYMBOL_LIB_NAME, CONFIG_SYMBOL_DIR_NAME,
    CONFIG_MODELS_DIR_NAME, CONFIG_CREATE_BACKUPS, DEFAULT_LOCAL_LIB_NAME,
    DEFAULT_SYMBOL_LIB_NAME, DEFAULT_SYMBOL_DIR_NAME, DEFAULT_MODELS_DIR_NAME,
    PROGRESS_STEP_SCAN_PCB, PROGRESS_STEP_SCAN_SCHEMATICS, PROGRESS_STEP_SCAN_SYMBOLS,
    PROGRESS_STEP_COPY_FOOTPRINTS, PROGRESS_STEP_COPY_SYMBOLS, PROGRESS_STEP_COPY_3D_MODELS,
    PROGRESS_STEP_UPDATE_PCB, PROGRESS_STEP_UPDATE_SCHEMATICS,
    PROGRESS_STEP_UPDATE_LIB_TABLE, PROGRESS_STEP_UPDATE_SYM_LIB_TABLE,
    SUCCESS_LOCALIZATION_COMPLETE
)
from .ui_components import BakeryLogger, ConfigDialog
from .footprint_localizer import FootprintLocalizer
from .symbol_localizer import SymbolLocalizer
from .library_manager import LibraryManager


class BakeryPlugin(pcbnew.ActionPlugin):
    """
    @brief Main plugin class for Bakery - localizes KiCad footprints and 3D models
    
    Provides ActionPlugin interface for KiCad integration. Coordinates the
    localization process using specialized manager classes.
    """
    
    def __init__(self):
        """
        @brief Initialize the plugin with default configuration
        """
        super(BakeryPlugin, self).__init__()
        self.defaults()  # Initialize plugin metadata
        self.logger = None
        self.config = {
            CONFIG_SYMBOL_LIB_NAME: DEFAULT_SYMBOL_LIB_NAME,
            CONFIG_SYMBOL_DIR_NAME: DEFAULT_SYMBOL_DIR_NAME,
            CONFIG_LOCAL_LIB_NAME: DEFAULT_LOCAL_LIB_NAME,
            CONFIG_MODELS_DIR_NAME: DEFAULT_MODELS_DIR_NAME,
            CONFIG_CREATE_BACKUPS: True
        }
    
    def defaults(self):
        """
        @brief Initialize plugin metadata for KiCad registration
        
        Sets plugin name, category, description, toolbar visibility, and icon path.
        Called by KiCad during plugin loading.
        
        @note This method is required by the ActionPlugin interface
        """
        self.name = PLUGIN_NAME
        self.category = PLUGIN_CATEGORY
        self.description = PLUGIN_DESCRIPTION
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "Bakery_Icon.png")
    
    def Run(self):
        """
        @brief Execute when plugin is run from KiCad
        
        Main entry point for the plugin. Handles configuration, validation,
        and orchestrates the localization process.
        """
        try:
            # Get the current board
            board = pcbnew.GetBoard()
            
            if not board:
                wx.MessageBox(
                    ERROR_NO_BOARD,
                    "Bakery Plugin",
                    wx.OK | wx.ICON_WARNING
                )
                return
            
            # Get project path
            project_path = board.GetFileName()
            if not project_path:
                wx.MessageBox(
                    ERROR_PROJECT_NOT_SAVED,
                    "Bakery Plugin",
                    wx.OK | wx.ICON_WARNING
                )
                return
            
            project_dir = os.path.dirname(project_path)
            
            # Show configuration dialog
            config_dlg = ConfigDialog(None, self.config)
            if config_dlg.ShowModal() != wx.ID_OK:
                config_dlg.Destroy()
                return
            
            # Update configuration
            self.config = config_dlg.get_config()
            config_dlg.Destroy()
            
            # Show confirmation dialog
            result = wx.MessageBox(
                CONFIRM_LOCALIZATION,
                "Bakery - Localize Libraries",
                wx.YES_NO | wx.ICON_QUESTION
            )
            
            if result != wx.YES:
                return
            
            # Create logger window
            self.logger = BakeryLogger(None)
            
            try:
                # Show logger as modeless first for progress updates
                self.logger.Show()
                wx.GetApp().Yield()
                
                self.run_localization(board, project_path, project_dir)
                
            except Exception as e:
                self.logger.error(f"Error during localization: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
            
            finally:
                self.logger.enable_close()
                # Switch to modal to wait for user to close
                if self.logger:
                    self.logger.ShowModal()
                    self.logger.Destroy()
            
        except Exception as e:
            wx.MessageBox(
                f"Error running Bakery plugin:\n\n{str(e)}",
                "Bakery Plugin Error",
                wx.OK | wx.ICON_ERROR
            )
            print(f"Bakery Plugin Error: {e}")
            import traceback
            traceback.print_exc()
    
    def run_localization(self, board, project_path: str, project_dir: str):
        """
        @brief Execute the localization process
        
        @param board: KiCad BOARD object
        @param project_path: Path to the PCB file
        @param project_dir: Project directory path
        """
        self.logger.info("Starting localization process...")
        self.logger.info(f"Project: {project_path}")
        self.logger.info(f"Configuration: Library={self.config[CONFIG_LOCAL_LIB_NAME]}, "
                        f"Symbols={self.config[CONFIG_SYMBOL_LIB_NAME]}, "
                        f"Models={self.config[CONFIG_MODELS_DIR_NAME]}, "
                        f"Backups={self.config[CONFIG_CREATE_BACKUPS]}")
        
        # Create localizers
        fp_localizer = FootprintLocalizer(self.logger)
        sym_localizer = SymbolLocalizer(self.logger)
        lib_manager = LibraryManager(self.logger)
        
        # === FOOTPRINT LOCALIZATION ===
        
        # Step 1: Scan for footprints
        self.logger.set_progress(5, 100, PROGRESS_STEP_SCAN_PCB)
        pcb_footprints = fp_localizer.scan_pcb_footprints(board)
        
        self.logger.set_progress(10, 100, PROGRESS_STEP_SCAN_SCHEMATICS)
        sch_footprints = fp_localizer.scan_schematic_footprints(project_dir)
        
        # Combine footprints from both sources
        all_footprints = pcb_footprints.union(sch_footprints)
        self.logger.info(f"Total unique footprints found: {len(all_footprints)}")
        
        # Step 2: Copy footprints
        self.logger.set_progress(20, 100, PROGRESS_STEP_COPY_FOOTPRINTS)
        copied_footprints = []
        if all_footprints:
            copied_footprints = fp_localizer.copy_footprints(
                all_footprints,
                project_dir,
                self.config[CONFIG_LOCAL_LIB_NAME]
            )
        
        # Step 3: Localize 3D models
        if copied_footprints:
            self.logger.set_progress(30, 100, PROGRESS_STEP_COPY_3D_MODELS)
            fp_localizer.localize_3d_models(
                copied_footprints,
                project_dir,
                self.config[CONFIG_MODELS_DIR_NAME]
            )
            
            # Step 4: Update footprint library table
            self.logger.set_progress(40, 100, PROGRESS_STEP_UPDATE_LIB_TABLE)
            lib_manager.update_fp_lib_table(project_dir, self.config[CONFIG_LOCAL_LIB_NAME])
            
            # Step 5: Update PCB references
            self.logger.set_progress(45, 100, PROGRESS_STEP_UPDATE_PCB)
            fp_localizer.update_pcb_references(
                board,
                copied_footprints,
                project_path,
                self.config[CONFIG_LOCAL_LIB_NAME],
                self.config[CONFIG_CREATE_BACKUPS]
            )
            
            # Step 6: Update schematic footprint references
            self.logger.set_progress(50, 100, PROGRESS_STEP_UPDATE_SCHEMATICS)
            fp_localizer.update_schematic_references(
                copied_footprints,
                project_dir,
                self.config[CONFIG_LOCAL_LIB_NAME],
                self.config[CONFIG_CREATE_BACKUPS]
            )
        else:
            self.logger.info("No footprints to copy")
        
        # === SYMBOL LOCALIZATION ===
        
        # Step 7: Scan for symbols
        self.logger.set_progress(55, 100, PROGRESS_STEP_SCAN_SYMBOLS)
        all_symbols = sym_localizer.scan_schematic_symbols(project_dir)
        self.logger.info(f"Total unique symbols found: {len(all_symbols)}")
        
        # Step 8: Copy symbols
        copied_symbols = []
        if all_symbols:
            self.logger.set_progress(65, 100, PROGRESS_STEP_COPY_SYMBOLS)
            copied_symbols = sym_localizer.copy_symbols(
                all_symbols,
                project_dir,
                self.config[CONFIG_SYMBOL_LIB_NAME],
                self.config[CONFIG_SYMBOL_DIR_NAME]
            )
            
            if copied_symbols:
                # Step 9: Update symbol library table
                self.logger.set_progress(80, 100, PROGRESS_STEP_UPDATE_SYM_LIB_TABLE)
                sym_localizer.update_sym_lib_table(
                    project_dir,
                    self.config[CONFIG_SYMBOL_LIB_NAME],
                    self.config[CONFIG_SYMBOL_DIR_NAME]
                )
                
                # Step 10: Update schematic symbol references
                self.logger.set_progress(90, 100, "Updating Symbol References")
                sym_localizer.update_schematic_references(
                    copied_symbols,
                    project_dir,
                    self.config[CONFIG_SYMBOL_LIB_NAME],
                    self.config[CONFIG_CREATE_BACKUPS]
                )
            else:
                self.logger.info("No symbols to copy")
        else:
            self.logger.info("No symbols found in schematics")
        
        # Complete
        self.logger.set_progress(100, 100, "Complete")
        self.logger.success(SUCCESS_LOCALIZATION_COMPLETE)
        
        if copied_footprints or copied_symbols:
            self.logger.info(f"Copied {len(copied_footprints)} footprints and {len(copied_symbols)} symbols to local libraries.")
            self.logger.info(f"All references have been updated to use local libraries.")
        else:
            self.logger.info("All footprints and symbols were already in local libraries.")
        
        # Show backup information
        all_backups = []
        if copied_footprints:
            all_backups.extend(fp_localizer.backup_manager.get_backups())
        if copied_symbols:
            all_backups.extend(sym_localizer.backup_manager.get_backups())
        
        if all_backups:
            self.logger.info(f"Backups created: {len(all_backups)} file(s)")
            for backup in all_backups:
                self.logger.info(f"  - {os.path.basename(backup)}")


