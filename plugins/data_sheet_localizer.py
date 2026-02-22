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
@file data_sheet_localizer.py

@brief Datasheet localization for Bakery plugin

Handles localization of component datasheets:
- Scanning symbols for datasheet references (URLs or local file paths)
- Downloading datasheets from internet URLs (http://, https://)
- Copying local datasheet files to project directory
- Updating datasheet references to point to local copies
- Preserving original datasheet file structure

@section description_datasheet_localizer Detailed Description
This module provides the DataSheetLocalizer class which manages datasheet
localization. It scans symbol libraries (.kicad_sym) to find datasheet 
properties which can be either:
- Internet URLs (e.g., "http://www.vishay.com/docs/88503/1n4001.pdf") - downloaded
- Local file paths (e.g., "C:\\Datasheets\\file.pdf") - copied

Downloads or copies the datasheets to a local project directory, and updates 
all references to use local paths with ${KIPRJMOD} variable. In KiCad, 
datasheets are stored in symbol definitions, not footprints.

@section notes_datasheet_localizer Notes
- Scans symbol libraries for datasheet properties
- Handles both URL downloads (http://, https://) and local file copying
- Only processes PDF format datasheets (.pdf extension) - non-PDF files are skipped
- Updates paths to use ${KIPRJMOD} variable for portability
- Creates organized datasheet directory structure
- Automatically deduplicates references to avoid copying same datasheet multiple times
"""

import os
import shutil
from typing import List, Optional, Callable, Set, Tuple
from urllib.parse import urlparse

from .constants import (
    EXTENSION_SYMBOL_LIB, EXTENSION_FOOTPRINT,
    SEXPR_PROPERTY, ENV_VAR_KIPRJMOD
)
from .base_localizer import BaseLocalizer
from .utils import expand_kicad_path, safe_read_file


class DataSheetLocalizer(BaseLocalizer):
    """!
    @brief Handles localization of component datasheets from URLs and global locations
    
    Scans symbol libraries for datasheet references (URLs or paths), downloads or 
    copies them to project-local directory, and updates all references. In KiCad,
    datasheets are stored in symbol definitions.
    
    Inherits common functionality from BaseLocalizer.
    
    @section methods Methods
    - :py:meth:`~DataSheetLocalizer.__init__`
    - :py:meth:`~DataSheetLocalizer.scan_symbol_datasheets`
    - :py:meth:`~DataSheetLocalizer.copy_datasheets`
    - :py:meth:`~DataSheetLocalizer.download_datasheet`
    - :py:meth:`~DataSheetLocalizer.update_symbol_references`
    - :py:meth:`~DataSheetLocalizer.localize_all_datasheets`
    
    @section attributes Attributes
    - project_dir (str): Project directory path
    - datasheet_dir (str): Local datasheet directory name
    - logger (Callable): Logger object with info/warning/error methods
    """
    
    def __init__(
        self,
        project_dir: str,
        datasheet_dir: str = "Data_Sheets",
        logger: Optional[Callable] = None
    ):
        """
        @brief Initialize the datasheet localizer
        
        @param project_dir: Path to the project directory
        @param datasheet_dir: Name of the local datasheet directory (default: "Data_Sheets")
        @param logger: Optional logger object with info/warning/error methods
        """
        super().__init__(logger)
        self.project_dir = project_dir
        self.datasheet_dir = datasheet_dir
        self.datasheet_dir_path = os.path.join(project_dir, datasheet_dir)
        
    def scan_symbol_datasheets(self, symbol_lib_path: str) -> List[Tuple[str, str]]:
        """
        @brief Scan a symbol library file for datasheet references
        
        Parses symbol library and extracts all datasheet property values.
        Returns list of (symbol_name, datasheet_ref) tuples. Datasheets
        in KiCad are stored in symbol definitions.
        
        Note: In schematic files, datasheet format is:
        (property "Datasheet" "http://www.vishay.com/docs/88503/1n4001.pdf")
        
        Multiple instances of the same component will have duplicate datasheet
        references. This method should deduplicate URLs to avoid copying the
        same datasheet multiple times.
        
        @param symbol_lib_path: Path to .kicad_sym file
        
        @return List of tuples (symbol_name, datasheet_reference) with duplicates removed
        """
        self.log("info", f"Scanning symbol library for datasheets: {symbol_lib_path}")
        datasheets = []
        
        # TODO: Implement symbol library parsing for datasheet properties
        # Parse .kicad_sym file using S-expression parser
        # Find (symbol ...) entries
        # Within each symbol, find (property "Datasheet" "value") entries
        # Extract symbol names and datasheet values
        # Filter out empty datasheets ("" or "~")
        # Filter out non-PDF datasheets (only process .pdf files)
        # Use a set to track unique datasheet URLs to avoid duplicates
        
        return datasheets
    
    def copy_datasheets(
        self,
        datasheets: List[Tuple[str, str]],
        progress_callback: Optional[Callable] = None
    ) -> int:
        """
        @brief Copy or download datasheets to local project directory
        
        Creates datasheet directory if needed, then:
        - Downloads PDF files from internet URLs (http://, https://)
        - Copies local file paths to the project directory
        
        Automatically deduplicates URLs to avoid copying the same datasheet 
        multiple times (e.g., when multiple component instances reference 
        the same datasheet URL).
        
        @param datasheets: List of (component_name, datasheet_ref) tuples
        @param progress_callback: Optional callback for progress updates
        
        @return Number of datasheets successfully copied/downloaded
        """
        self.log("info", f"Copying datasheets to: {self.datasheet_dir_path}")
        
        # Create datasheet directory if it doesn't exist
        if not os.path.exists(self.datasheet_dir_path):
            os.makedirs(self.datasheet_dir_path)
            self.log("info", f"Created datasheet directory: {self.datasheet_dir}")
        
        # Use set to track unique datasheet URLs/paths to avoid duplicates
        unique_datasheets = {}  # {datasheet_url: component_name}
        for comp_name, datasheet_ref in datasheets:
            if datasheet_ref not in unique_datasheets:
                unique_datasheets[datasheet_ref] = comp_name
        
        self.log("info", f"Found {len(datasheets)} total references, {len(unique_datasheets)} unique datasheets")
        
        copied_count = 0
        
        # TODO: Implement datasheet copying logic
        # For each unique datasheet reference:
        #   - Check if reference ends with .pdf (case-insensitive) - skip if not PDF
        #   - Determine if it's a URL (starts with http:// or https://) or local file path
        #   - If URL: 
        #       * Verify URL ends with .pdf
        #       * Download PDF from internet to local directory
        #       * Extract filename from URL or generate from component name
        #       * Save to ${KIPRJMOD}/Data_Sheets/
        #   - If local file path: 
        #       * Verify file has .pdf extension
        #       * Expand KiCad path variables (${KIPRJMOD}, etc.)
        #       * Copy file to local directory
        #       * Preserve original filename
        #   - Track successful copies/downloads
        #   - Build mapping of old refs to new local paths for update step
        #   - Log skipped non-PDF datasheets
        
        return copied_count
    
    def download_datasheet(self, url: str, dest_path: str) -> bool:
        """
        @brief Download a datasheet PDF from a URL
        
        Downloads PDF files from internet URLs (http://, https://) to the
        local project directory. This handles web-hosted datasheets that
        need to be downloaded for offline project portability.
        
        Only processes URLs ending with .pdf extension - non-PDF URLs are skipped.
        
        @param url: Internet URL to download from (e.g., "http://www.vishay.com/docs/88503/1n4001.pdf")
        @param dest_path: Destination file path in local project
        
        @return True if download successful, False otherwise
        
        @throws Exception if download fails
        """
        self.log("info", f"Downloading datasheet from: {url}")
        
        # TODO: Implement URL download logic
        # Verify URL ends with .pdf (case-insensitive) before downloading
        # Use urllib.request or requests library to download file
        # Handle HTTP errors gracefully (404, timeouts, etc.)
        # Verify file was downloaded successfully
        # Check if downloaded file is a valid PDF (magic bytes)
        
        return False
    
    def update_symbol_references(
        self,
        symbol_lib_path: str,
        datasheet_map: dict
    ) -> bool:
        """
        @brief Update datasheet references in symbol library to point to local copies
        
        @param symbol_lib_path: Path to .kicad_sym file
        @param datasheet_map: Dictionary mapping old refs to new local paths
        
        @return True if update successful, False otherwise
        """
        self.log("info", f"Updating datasheet references in: {symbol_lib_path}")
        
        # TODO: Implement symbol library update logic
        # Read symbol library content
        # Replace old datasheet references with ${KIPRJMOD}/Datasheets/... paths
        # Create backup before modifying
        # Write updated content back to file
        
        return False
    
    def localize_all_datasheets(
        self,
        symbol_libs: List[str],
        progress_callback: Optional[Callable] = None
    ) -> Tuple[int, int]:
        """
        @brief Main entry point to localize all datasheets in the project
        
        Scans all symbol libraries for datasheet references, copies/downloads 
        datasheets, and updates all references. In KiCad, datasheets are stored
        in symbol definitions.
        
        @param symbol_libs: List of symbol library paths to scan
        @param progress_callback: Optional callback for progress updates
        
        @return Tuple of (datasheets_copied, references_updated)
        """
        self.log("info", "Starting datasheet localization process")
        
        all_datasheets = []
        
        # Scan symbol libraries for datasheets
        for symbol_lib in symbol_libs:
            if os.path.exists(symbol_lib):
                datasheets = self.scan_symbol_datasheets(symbol_lib)
                all_datasheets.extend(datasheets)
        
        self.log("info", f"Found {len(all_datasheets)} datasheet references in symbols")
        
        # Copy/download datasheets
        copied_count = self.copy_datasheets(all_datasheets, progress_callback)
        
        # TODO: Update all references in symbol library files
        updated_count = 0
        
        self.log("success", f"Datasheet localization complete: {copied_count} copied, {updated_count} references updated")
        
        return (copied_count, updated_count)
