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
@file footprint_localizer.py

@brief Footprint localization for Bakery plugin

Handles localization of PCB footprints and 3D models:
- Scanning PCB and schematics for footprint references
- Copying footprints to local project libraries
- Localizing 3D model files
- Updating footprint references in PCB and schematics

@section description_footprint_localizer Detailed Description
This module provides the FootprintLocalizer class which manages footprint and
3D model localization. It scans both PCB (.kicad_pcb) and schematic (.kicad_sch)
files to find all footprint references, copies .kicad_mod files to local .pretty
libraries, and localizes associated 3D models (STEP, WRL, etc.).

@section notes_footprint_localizer Notes
- Scans both PCB and schematic files for comprehensive coverage
- Preserves 3D model file formats and structure
- Updates model paths to use ${KIPRJMOD} variable
"""

import os
import shutil
import glob
from datetime import datetime
from typing import List, Tuple, Optional, Callable, Set

from .constants import (
    EXTENSION_FOOTPRINT, EXTENSION_FOOTPRINT_LIB, EXTENSION_PCB,
    EXTENSION_SCHEMATIC, SEXPR_FOOTPRINT, SEXPR_PROPERTY, SEXPR_MODEL,
    PROGRESS_STEP_COPY_FOOTPRINTS
)
from .sexpr_parser import SExpressionParser
from .library_manager import LibraryManager
from .backup_manager import BackupManager
from .utils import (
    expand_kicad_path, safe_read_file, find_schematic_files,
    scan_schematics_for_items
)


class FootprintLocalizer:
    """!
    @brief Handles localization of footprints and 3D models from global to local libraries
    
    Scans PCB and schematic files, identifies external footprint references, copies
    them to project-local libraries, and updates all references.
    
    @section methods Methods
    - :py:meth:`~FootprintLocalizer.__init__`
    - :py:meth:`~FootprintLocalizer.log`
    - :py:meth:`~FootprintLocalizer.scan_pcb_footprints`
    - :py:meth:`~FootprintLocalizer.scan_schematic_footprints`
    - :py:meth:`~FootprintLocalizer.copy_footprints`
    - :py:meth:`~FootprintLocalizer.localize_3d_models`
    - :py:meth:`~FootprintLocalizer.update_pcb_references`
    - :py:meth:`~FootprintLocalizer.update_schematic_references`
    
    @section attributes Attributes
    - logger (Callable): Logger object with info/warning/error methods
    - parser (SExpressionParser): S-expression parser instance
    - lib_manager (LibraryManager): Library manager instance
    - backup_manager (BackupManager): File backup manager instance
    """
    
    def __init__(self, logger: Optional[Callable] = None):
        """
        @brief Initialize the footprint localizer
        
        @param logger: Optional logger object with info/warning/error methods
        """
        self.logger = logger
        self.parser = SExpressionParser()
        self.lib_manager = LibraryManager(logger)
        self.backup_manager = BackupManager(logger)
    
    def log(self, level: str, message: str) -> None:
        """
        @brief Internal logging helper
        
        @param level: Log level (info, warning, error, success)
        @param message: Message to log
        """
        if self.logger:
            method = getattr(self.logger, level, None)
            if method:
                method(message)
    
    def scan_pcb_footprints(self, board) -> Set[Tuple[str, str]]:
        """
        @brief Scan PCB for footprint references
        
        @param board: KiCad BOARD object
        @return Set of (library, footprint) tuples
        """
        footprints = set()
        
        self.log('info', PROGRESS_STEP_SCAN_PCB + "...")
        
        # Count footprints
        fp_count = sum(1 for _ in board.GetFootprints())
        self.log('info', f"Found {fp_count} footprints on the PCB")
        
        # Get footprints
        for fp in board.GetFootprints():
            try:
                fpid = fp.GetFPID()
                fp_name = fpid.GetLibItemName().__str__()
                lib_name = fpid.GetLibNickname().__str__()
                
                if lib_name and fp_name:
                    footprints.add((lib_name, fp_name))
                    self.log('info', f"  - {lib_name}:{fp_name}")
                    
            except AttributeError as e:
                self.log('error', f"Error reading footprint: {e}")
                continue
        
        return footprints
    
    def scan_schematic_footprints(self, project_dir: str) -> Set[Tuple[str, str]]:
        """
        @brief Scan schematic files for footprint references
        """
        return scan_schematics_for_items(
            project_dir,
            self.parser,
            self.parser.find_footprints,
            self.logger,
            "Scanning schematics for footprints"
        )
    
    def copy_footprints(self, footprints: Set[Tuple[str, str]], project_dir: str, 
                       local_lib_name: str) -> List[Tuple[str, str, str, str]]:
        """
        @brief Copy footprints to local library
        
        @param footprints: Set of (library, footprint) tuples to copy
        @param project_dir: Project directory path
        @param local_lib_name: Name of local library
        @return List of (lib_name, fp_name, source_path, dest_path) tuples for copied footprints
        """
        self.log('info', PROGRESS_STEP_COPY_FOOTPRINTS + "...")
        
        # Create local library
        local_lib_path = self.lib_manager.create_local_footprint_library(
            project_dir, local_lib_name)
        
        # Filter out footprints already in local library
        footprints_to_copy = set()
        skipped_count = 0
        
        for lib_name, fp_name in footprints:
            if lib_name == local_lib_name:
                self.log('info', f"→ Skipping {lib_name}:{fp_name} (already in local library)")
                skipped_count += 1
            else:
                footprints_to_copy.add((lib_name, fp_name))
        
        if skipped_count > 0:
            self.log('info', f"Skipped {skipped_count} footprints already in {local_lib_name}")
        
        # Copy footprints
        copied_count = 0
        failed_count = 0
        copied_footprints = []
        
        for lib_name, fp_name in footprints_to_copy:
            try:
                # Find source footprint path
                lib_path = self.lib_manager.find_footprint_library_path(lib_name)
                
                if not lib_path:
                    self.log('warning', f"✗ Could not find library: {lib_name}")
                    failed_count += 1
                    continue
                
                source_fp_path = os.path.join(lib_path, f"{fp_name}{EXTENSION_FOOTPRINT}")
                
                if os.path.exists(source_fp_path):
                    # Destination path in local library
                    dest_fp_path = os.path.join(local_lib_path, f"{fp_name}{EXTENSION_FOOTPRINT}")
                    
                    # Copy the footprint file
                    shutil.copy2(source_fp_path, dest_fp_path)
                    self.log('info', f"✓ Copied {lib_name}:{fp_name}")
                    copied_count += 1
                    copied_footprints.append((lib_name, fp_name, source_fp_path, dest_fp_path))
                else:
                    self.log('warning', f"✗ Could not find source for {lib_name}:{fp_name}")
                    failed_count += 1
                    
            except Exception as e:
                self.log('error', f"✗ Failed to copy {lib_name}:{fp_name}: {str(e)}")
                failed_count += 1
        
        self.log('success', f"Copied {copied_count} footprints to {local_lib_name}{EXTENSION_FOOTPRINT_LIB}")
        if failed_count > 0:
            self.log('warning', f"{failed_count} footprints could not be copied")
        
        return copied_footprints
    
    def localize_3d_models(self, copied_footprints: List[Tuple[str, str, str, str]], 
                          project_dir: str, models_dir_name: str) -> Tuple[int, int]:
        """
        @brief Copy 3D models associated with footprints to local project folder
        
        @param copied_footprints: List of (lib_name, fp_name, source_path, dest_path) tuples
        @param project_dir: Project directory path
        @param models_dir_name: Name of 3D models directory
        @return Tuple of (copied_count, failed_count)
        """
        if not copied_footprints:
            self.log('info', "No footprints were copied, skipping 3D model localization")
            return (0, 0)
        
        self.log('info', PROGRESS_STEP_COPY_3D_MODELS + "...")
        
        # Create 3D Models folder
        models_dir = os.path.join(project_dir, models_dir_name)
        os.makedirs(models_dir, exist_ok=True)
        self.log('info', f"Using 3D models folder: {models_dir}")
        
        copied_models = {}
        footprints_to_update = []
        total_models = 0
        copied_count = 0
        failed_count = 0
        
        # Process each copied footprint
        for lib_name, fp_name, source_fp_path, dest_fp_path in copied_footprints:
            self.log('info', f"Checking {fp_name} for 3D models...")
            
            # Extract 3D model references
            try:
                with open(source_fp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                sexpr = self.parser.parse(content)
                model_paths = self.parser.find_3d_models(sexpr)
            except Exception as e:
                self.log('warning', f"Could not parse footprint for 3D models: {e}")
                continue
            
            if not model_paths:
                self.log('info', f"  No 3D models found in {fp_name}")
                continue
            
            self.log('info', f"  Found {len(model_paths)} 3D model(s)")
            total_models += len(model_paths)
            
            old_model_paths = []
            new_model_paths = []
            
            for model_path in model_paths:
                self.log('info', f"    Model: {model_path}")
                
                # Expand environment variables
                expanded_path = self.lib_manager.expand_path(model_path)
                model_filename = os.path.basename(expanded_path)
                
                if os.path.exists(expanded_path):
                    # Check if already copied
                    if model_path in copied_models:
                        self.log('info', f"      ✓ Already copied: {model_filename}")
                        old_model_paths.append(model_path)
                        new_model_paths.append(copied_models[model_path])
                    else:
                        # Copy the model file
                        dest_model_path = os.path.join(models_dir, model_filename)
                        
                        try:
                            shutil.copy2(expanded_path, dest_model_path)
                            self.log('info', f"      ✓ Copied to {dest_model_path}")
                            copied_count += 1
                            
                            # Store relative path
                            relative_model_path = f"${{{ENV_VAR_KIPRJMOD}}}/{models_dir_name}/{model_filename}"
                            copied_models[model_path] = relative_model_path
                            old_model_paths.append(model_path)
                            new_model_paths.append(relative_model_path)
                            
                        except Exception as e:
                            self.log('error', f"      ✗ Failed to copy {model_filename}: {str(e)}")
                            failed_count += 1
                else:
                    self.log('warning', f"      ✗ Model file not found: {expanded_path}")
                    failed_count += 1
            
            # Queue footprint for updating
            if old_model_paths:
                footprints_to_update.append((dest_fp_path, old_model_paths, new_model_paths))
        
        # Update footprint files
        if footprints_to_update:
            self.log('info', f"Updating {len(footprints_to_update)} footprint(s) to reference local 3D models...")
            
            for dest_fp_path, old_paths, new_paths in footprints_to_update:
                try:
                    with open(dest_fp_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Replace old model paths with new local paths
                    for old_path, new_path in zip(old_paths, new_paths):
                        content = content.replace(f'"{old_path}"', f'"{new_path}"')
                    
                    with open(dest_fp_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.log('info', f"  ✓ Updated {os.path.basename(dest_fp_path)}")
                    
                except Exception as e:
                    self.log('error', f"  ✗ Failed to update {os.path.basename(dest_fp_path)}: {str(e)}")
        
        # Summary
        if total_models > 0:
            self.log('success', f"3D model localization complete:")
            self.log('info', f"  • {copied_count} unique models copied to {models_dir_name} folder")
            self.log('info', f"  • {len(footprints_to_update)} footprints updated with local paths")
            if failed_count > 0:
                self.log('warning', f"  • {failed_count} models could not be copied")
        else:
            self.log('info', "No 3D models found in footprints")
        
        return (copied_count, failed_count)
    
    def update_pcb_references(self, board, copied_footprints: List[Tuple[str, str, str, str]], 
                             project_path: str, local_lib_name: str, 
                             create_backup: bool = True) -> int:
        """
        @brief Update PCB footprint references to use local library
        
        @param board: KiCad BOARD object
        @param copied_footprints: List of copied footprints
        @param project_path: Path to PCB file
        @param local_lib_name: Name of local library
        @param create_backup: Whether to create backup before modifying
        @return Number of updated references
        
        @throws IOError if backup or save fails
        """
        if not copied_footprints:
            self.log('info', "No footprints to update in PCB")
            return 0
        
        self.log('info', PROGRESS_STEP_UPDATE_PCB + "...")
        
        # Create backup
        if create_backup:
            try:
                self.backup_manager.create_backup(project_path)
            except Exception as e:
                self.log('error', f"Failed to create PCB backup: {e}")
                raise
        
        # Import pcbnew here to handle development environment
        try:
            import pcbnew
        except ImportError:
            self.log('error', "pcbnew module not available")
            raise
        
        # Create mapping
        footprint_map = {}
        for lib_name, fp_name, _, _ in copied_footprints:
            footprint_map[(lib_name, fp_name)] = local_lib_name
        
        # Update footprints
        updated_count = 0
        
        for fp in board.GetFootprints():
            try:
                fpid = fp.GetFPID()
                fp_name = fpid.GetLibItemName().__str__()
                lib_name = fpid.GetLibNickname().__str__()
                
                if (lib_name, fp_name) in footprint_map:
                    new_fpid = pcbnew.LIB_ID(local_lib_name, fp_name)
                    fp.SetFPID(new_fpid)
                    updated_count += 1
                    self.log('info', f"  ✓ Updated {lib_name}:{fp_name} → {local_lib_name}:{fp_name}")
                    
            except Exception as e:
                self.log('warning', f"Could not update footprint: {str(e)}")
        
        if updated_count > 0:
            try:
                board.Save(project_path)
                self.log('success', f"Updated {updated_count} footprint references in PCB")
                self.log('info', "PCB saved successfully")
            except Exception as e:
                self.log('error', f"Failed to save PCB: {str(e)}")
                raise
        else:
            self.log('info', "No footprint references needed updating")
        
        return updated_count
    
    def update_schematic_references(self, copied_footprints: List[Tuple[str, str, str, str]], 
                                   project_dir: str, local_lib_name: str,
                                   create_backup: bool = True) -> int:
        """
        @brief Update schematic footprint references to use local library
        
        @param copied_footprints: List of copied footprints
        @param project_dir: Project directory path
        @param local_lib_name: Name of local library
        @param create_backup: Whether to create backups before modifying
        @return Total number of updated references
        
        @throws IOError if backup or save fails
        """
        if not copied_footprints:
            self.log('info', "No footprints to update in schematics")
            return 0
        
        self.log('info', PROGRESS_STEP_UPDATE_SCHEMATICS + "...")
        
        # Create mapping
        footprint_map = {}
        for lib_name, fp_name, _, _ in copied_footprints:
            old_ref = f"{lib_name}:{fp_name}"
            new_ref = f"{local_lib_name}:{fp_name}"
            footprint_map[old_ref] = new_ref
        
        # Find schematic files
        schematic_files = glob.glob(os.path.join(project_dir, f"*{EXTENSION_SCHEMATIC}"))
        
        if not schematic_files:
            self.log('warning', "No schematic files found")
            return 0
        
        total_updated = 0
        
        for sch_file in schematic_files:
            self.log('info', f"Processing {os.path.basename(sch_file)}...")
            
            # Create backup
            if create_backup:
                try:
                    self.backup_manager.create_backup(sch_file)
                except Exception as e:
                    self.log('error', f"Failed to create backup for {sch_file}: {e}")
                    raise
            
            try:
                # Read the schematic file
                with open(sch_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                file_updated = 0
                
                # Replace footprint references
                for old_ref, new_ref in footprint_map.items():
                    old_pattern = f'({SEXPR_PROPERTY} "{SEXPR_FOOTPRINT}" "{old_ref}"'
                    new_pattern = f'({SEXPR_PROPERTY} "{SEXPR_FOOTPRINT}" "{new_ref}"'
                    
                    if old_pattern in content:
                        count = content.count(old_pattern)
                        content = content.replace(old_pattern, new_pattern)
                        file_updated += count
                        self.log('info', f"  ✓ Updated {count} instance(s) of {old_ref} → {new_ref}")
                
                # Write back if changed
                if content != original_content:
                    with open(sch_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.log('success', f"  Updated {file_updated} footprint reference(s)")
                    total_updated += file_updated
                else:
                    self.log('info', f"  No updates needed")
                    
            except Exception as e:
                self.log('error', f"Failed to update {os.path.basename(sch_file)}: {str(e)}")
                raise
        
        if total_updated > 0:
            self.log('success', f"Updated {total_updated} total footprint reference(s) in schematic files")
        else:
            self.log('info', "No footprint references needed updating in schematics")
        
        return total_updated

