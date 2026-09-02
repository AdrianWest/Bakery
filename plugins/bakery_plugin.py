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
@file bakery_plugin.py

@brief Main plugin module for Bakery KiCad Plugin

Provides the ActionPlugin interface for KiCad integration. Coordinates the
localization process for footprints, symbols, and 3D models using specialized
manager classes.

@section description_bakery_plugin Detailed Description
This module implements the BakeryPlugin class which serves as the entry point
for the KiCad plugin system. It orchestrates the complete localization workflow
by coordinating FootprintLocalizer, SymbolLocalizer, and LibraryManager components.

@section notes_bakery_plugin Notes
- Registered as KiCad ActionPlugin via pcbnew.ActionPlugin interface
- Requires KiCad 10.0 or later
- Must be installed in KiCad's scripting/plugins directory
"""

import os
import pcbnew
import wx


from .constants import (
    PLUGIN_NAME, PLUGIN_CATEGORY, PLUGIN_DESCRIPTION,
    ERROR_NO_BOARD, ERROR_PROJECT_NOT_SAVED, CONFIRM_LOCALIZATION,
    CONFIG_LOCAL_LIB_NAME, CONFIG_SYMBOL_LIB_NAME, CONFIG_SYMBOL_DIR_NAME,
    CONFIG_MODELS_DIR_NAME, CONFIG_DATASHEETS_DIR_NAME,
    DEFAULT_LOCAL_LIB_NAME, DEFAULT_SYMBOL_LIB_NAME, DEFAULT_SYMBOL_DIR_NAME,
    DEFAULT_MODELS_DIR_NAME, DEFAULT_DATASHEETS_DIR_NAME,
    PROGRESS_STEP_SCAN_PCB, PROGRESS_STEP_SCAN_SCHEMATICS, PROGRESS_STEP_SCAN_SYMBOLS,
    PROGRESS_STEP_BACKUP_PROJECT,
    PROGRESS_STEP_COPY_FOOTPRINTS, PROGRESS_STEP_COPY_SYMBOLS, PROGRESS_STEP_COPY_3D_MODELS,
    PROGRESS_STEP_UPDATE_PCB, PROGRESS_STEP_UPDATE_SCHEMATICS,
    PROGRESS_STEP_UPDATE_LIB_TABLE, PROGRESS_STEP_UPDATE_SYM_LIB_TABLE,
    SUCCESS_LOCALIZATION_COMPLETE, PROGRESS_INITIAL, PROGRESS_BAR_RANGE,
    PROGRESS_PCT_BACKUP_PROJECT, PROGRESS_PCT_SCAN_PCB,
    PROGRESS_PCT_SCAN_SCHEMATICS, PROGRESS_PCT_COPY_FOOTPRINTS,
    PROGRESS_PCT_COPY_3D_MODELS, PROGRESS_PCT_UPDATE_LIB_TABLE, PROGRESS_PCT_UPDATE_PCB,
    PROGRESS_PCT_UPDATE_SCHEMATICS, PROGRESS_PCT_SCAN_SYMBOLS, PROGRESS_PCT_COPY_SYMBOLS,
    PROGRESS_PCT_UPDATE_SYM_LIB_TABLE, PROGRESS_PCT_UPDATE_SYMBOL_REFS, PROGRESS_COMPLETE
)
from .ui_components import BakeryLogger, ConfigDialog
from .footprint_localizer import FootprintLocalizer
from .symbol_localizer import SymbolLocalizer
from .data_sheet_localizer import DataSheetLocalizer
from .library_manager import LibraryManager
from .backup_manager import BackupManager
from .utils import find_schematic_files


class BakeryPlugin(pcbnew.ActionPlugin):
    """!
    @brief Main plugin class for Bakery - localizes KiCad symbols, footprints, and 3D models
    
    Provides ActionPlugin interface for KiCad integration. Coordinates the
    localization process using specialized manager classes.
    
    @section methods Methods
    - :py:meth:`~BakeryPlugin.__init__`
    - :py:meth:`~BakeryPlugin.defaults`
    - :py:meth:`~BakeryPlugin.Run`
    - :py:meth:`~BakeryPlugin.run_localization`
    
    @section attributes Attributes
    - logger (BakeryLogger): Logger window instance
    - config (dict): Configuration dictionary with library names and options
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
            CONFIG_DATASHEETS_DIR_NAME: DEFAULT_DATASHEETS_DIR_NAME
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
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "resources", "Bakery_Icon.png")
    
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
            dialog_result = config_dlg.ShowModal()
            if dialog_result != wx.ID_OK:
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
                        f"Datasheets={self.config[CONFIG_DATASHEETS_DIR_NAME]}")

        self.logger.set_progress(
            PROGRESS_PCT_BACKUP_PROJECT,
            PROGRESS_BAR_RANGE,
            PROGRESS_STEP_BACKUP_PROJECT
        )
        project_name = os.path.splitext(os.path.basename(project_path))[0]
        BackupManager(self.logger).create_project_backup(
            project_dir,
            project_name
        )

        fp_localizer = FootprintLocalizer(self.logger)
        sym_localizer = SymbolLocalizer(self.logger)
        lib_manager = LibraryManager(self.logger)

        if not self._schematics_are_available(fp_localizer, project_dir):
            return

        copied_footprints = self._localize_footprints(
            board,
            project_path,
            project_dir,
            fp_localizer,
            lib_manager
        )
        copied_symbols = self._localize_symbols(project_dir, sym_localizer)
        datasheets_processed = self._localize_datasheets(
            project_dir,
            board
        )
        try:
            board.Save(project_path)
            self.logger.info("Final PCB save completed successfully")
        except Exception as error:
            self.logger.error(f"Failed to save final PCB state: {error}")
            raise
        fp_localizer.update_pcb_model_paths(
            project_path,
            project_dir,
            self.config[CONFIG_MODELS_DIR_NAME]
        )

        self._complete_localization(
            copied_footprints,
            copied_symbols,
            datasheets_processed
        )

    def _schematics_are_available(
        self,
        fp_localizer: FootprintLocalizer,
        project_dir: str
    ) -> bool:
        """
        @brief Ensure schematic files are not locked by an editor

        @param fp_localizer: Footprint localizer used for lock detection
        @param project_dir: Project directory path
        @return True when localization may continue
        """
        self.logger.info("Checking for open schematic files...")
        locked_files = fp_localizer.check_schematic_locks(project_dir)
        if not locked_files:
            return True

        self.logger.warning(
            "The following schematic file(s) are currently open: "
            + ", ".join(locked_files)
        )
        self.logger.error(
            "Please close all schematic editors before running this plugin"
        )
        wx.MessageBox(
            "Cannot proceed - schematic files are open:\n\n"
            + "\n".join(locked_files)
            + "\n\nPlease close the schematic editor and try again.",
            "Schematic Files Locked",
            wx.OK | wx.ICON_WARNING
        )
        return False

    def _localize_footprints(
        self,
        board,
        project_path: str,
        project_dir: str,
        fp_localizer: FootprintLocalizer,
        lib_manager: LibraryManager
    ) -> list:
        """
        @brief Run footprint and 3D model localization

        @param board: KiCad BOARD object
        @param project_path: PCB file path
        @param project_dir: Project directory path
        @param fp_localizer: Footprint localization service
        @param lib_manager: Library table management service
        @return Copied footprint records
        """
        self.logger.set_progress(PROGRESS_PCT_SCAN_PCB, PROGRESS_BAR_RANGE, PROGRESS_STEP_SCAN_PCB)
        pcb_footprints = fp_localizer.scan_pcb_footprints(board)
        self.logger.set_progress(PROGRESS_PCT_SCAN_SCHEMATICS, PROGRESS_BAR_RANGE, PROGRESS_STEP_SCAN_SCHEMATICS)
        sch_footprints = fp_localizer.scan_schematic_footprints(project_dir)
        all_footprints = pcb_footprints.union(sch_footprints)
        self.logger.info(f"Total unique footprints found: {len(all_footprints)}")

        self.logger.set_progress(PROGRESS_PCT_COPY_FOOTPRINTS, PROGRESS_BAR_RANGE, PROGRESS_STEP_COPY_FOOTPRINTS)
        copied_footprints = []
        if all_footprints:
            copied_footprints = fp_localizer.copy_footprints(
                all_footprints,
                project_dir,
                self.config[CONFIG_LOCAL_LIB_NAME]
            )

        if not copied_footprints:
            self.logger.info("No footprints to copy")
            return []

        self.logger.set_progress(PROGRESS_PCT_COPY_3D_MODELS, PROGRESS_BAR_RANGE, PROGRESS_STEP_COPY_3D_MODELS)
        fp_localizer.localize_3d_models(
            copied_footprints,
            project_dir,
            self.config[CONFIG_MODELS_DIR_NAME]
        )
        self.logger.set_progress(PROGRESS_PCT_UPDATE_LIB_TABLE, PROGRESS_BAR_RANGE, PROGRESS_STEP_UPDATE_LIB_TABLE)
        if not lib_manager.update_fp_lib_table(
            project_dir,
            self.config[CONFIG_LOCAL_LIB_NAME]
        ):
            raise RuntimeError(
                "Footprint library table update failed; references were not changed"
            )
        self.logger.set_progress(PROGRESS_PCT_UPDATE_PCB, PROGRESS_BAR_RANGE, PROGRESS_STEP_UPDATE_PCB)
        fp_localizer.update_pcb_references(
            board,
            copied_footprints,
            project_path,
            self.config[CONFIG_LOCAL_LIB_NAME]
        )
        self.logger.set_progress(PROGRESS_PCT_UPDATE_SCHEMATICS, PROGRESS_BAR_RANGE, PROGRESS_STEP_UPDATE_SCHEMATICS)
        fp_localizer.update_schematic_references(
            copied_footprints,
            project_dir,
            self.config[CONFIG_LOCAL_LIB_NAME]
        )
        return copied_footprints

    def _localize_symbols(
        self,
        project_dir: str,
        sym_localizer: SymbolLocalizer
    ) -> list:
        """
        @brief Run symbol localization

        @param project_dir: Project directory path
        @param sym_localizer: Symbol localization service
        @return Copied symbol records
        """
        self.logger.set_progress(PROGRESS_PCT_SCAN_SYMBOLS, PROGRESS_BAR_RANGE, PROGRESS_STEP_SCAN_SYMBOLS)
        all_symbols = sym_localizer.scan_schematic_symbols(project_dir)
        self.logger.info(f"Total unique symbols found: {len(all_symbols)}")
        if not all_symbols:
            self.logger.info("No symbols found in schematics")
            return []

        self.logger.set_progress(PROGRESS_PCT_COPY_SYMBOLS, PROGRESS_BAR_RANGE, PROGRESS_STEP_COPY_SYMBOLS)
        copied_symbols = sym_localizer.copy_symbols(
            all_symbols,
            project_dir,
            self.config[CONFIG_SYMBOL_LIB_NAME],
            self.config[CONFIG_SYMBOL_DIR_NAME]
        )
        if not copied_symbols:
            self.logger.info("No symbols to copy")
            return []

        self.logger.set_progress(PROGRESS_PCT_UPDATE_SYM_LIB_TABLE, PROGRESS_BAR_RANGE, PROGRESS_STEP_UPDATE_SYM_LIB_TABLE)
        if not sym_localizer.update_sym_lib_table(
            project_dir,
            self.config[CONFIG_SYMBOL_LIB_NAME],
            self.config[CONFIG_SYMBOL_DIR_NAME]
        ):
            raise RuntimeError(
                "Symbol library table update failed; references were not changed"
            )
        self.logger.set_progress(PROGRESS_PCT_UPDATE_SYMBOL_REFS, PROGRESS_BAR_RANGE, "Updating Symbol References")
        sym_localizer.update_schematic_references(
            copied_symbols,
            project_dir,
            self.config[CONFIG_SYMBOL_LIB_NAME]
        )
        return copied_symbols

    def _localize_datasheets(
        self,
        project_dir: str,
        board
    ) -> int:
        """
        @brief Run datasheet localization for local symbols and schematics

        @param project_dir: Project directory path
        @param board: Active KiCad BOARD object
        @return Number of datasheets processed
        """

        symbol_lib_path = os.path.join(
            project_dir,
            self.config[CONFIG_SYMBOL_DIR_NAME],
            f"{self.config[CONFIG_SYMBOL_LIB_NAME]}.kicad_sym"
        )
        symbol_libs = [symbol_lib_path] if os.path.exists(symbol_lib_path) else []
        schematic_files = find_schematic_files(project_dir)

        self.logger.info("Starting datasheet localization...")
        datasheet_localizer = DataSheetLocalizer(
            project_dir,
            self.config[CONFIG_DATASHEETS_DIR_NAME],
            self.logger
        )
        processed, files_updated = datasheet_localizer.localize_all_datasheets(
            symbol_libs,
            schematic_files,
            board=board
        )
        self.logger.info(
            f"Datasheet localization complete: {processed} datasheets "
            f"processed, {files_updated} files updated"
        )
        return processed

    def _complete_localization(
        self,
        copied_footprints: list,
        copied_symbols: list,
        datasheets_processed: int
    ) -> None:
        """
        @brief Report localization results and show the completion dialog

        @param copied_footprints: Copied footprint records
        @param copied_symbols: Copied symbol records
        @param datasheets_processed: Number of processed datasheets
        """
        footprint_copy_count = sum(
            1
            for record in copied_footprints
            if len(record) >= 5 and record[3] != record[4]
        )
        symbol_copy_count = sum(
            1
            for record in copied_symbols
            if len(record) >= 4 and record[3] is not None
        )

        self.logger.set_progress(PROGRESS_COMPLETE, PROGRESS_BAR_RANGE, "Complete")
        self.logger.success(SUCCESS_LOCALIZATION_COMPLETE)

        if footprint_copy_count or symbol_copy_count:
            self.logger.info(
                f"Copied {footprint_copy_count} footprints and "
                f"{symbol_copy_count} symbols to local libraries."
            )
            if datasheets_processed > 0:
                self.logger.info(f"Processed {datasheets_processed} datasheets.")
            self.logger.info(f"All references have been updated to use local libraries.")
        else:
            self.logger.info("All footprints and symbols were already in local libraries.")

        self.logger.set_progress(PROGRESS_INITIAL, PROGRESS_BAR_RANGE, "")
        completion_msg = (
            f"Localization Complete!\n\n"
            f"• {footprint_copy_count} footprints copied\n"
            f"• {symbol_copy_count} symbols copied\n"
        )
        if datasheets_processed > 0:
            completion_msg += f"• {datasheets_processed} datasheets processed\n"
        completion_msg += (
            "\nAll references have been updated to use local libraries."
        )
        
        wx.MessageBox(
            completion_msg,
            "Bakery - Success",
            wx.OK | wx.ICON_INFORMATION
        )
