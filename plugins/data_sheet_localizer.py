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
- Compares file modification dates when destination file exists - keeps the latest version
- Updates paths to use ${KIPRJMOD} variable for portability
- Creates organized datasheet directory structure
- Automatically deduplicates references to avoid copying same datasheet multiple times
"""

import os
import shutil
import urllib.request
import urllib.error
from typing import List, Optional, Callable, Set, Tuple, Dict
from urllib.parse import urlparse, unquote

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
    - :py:meth:`~DataSheetLocalizer.update_schematic_references`
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
        
        # Read and parse symbol library file
        content = safe_read_file(symbol_lib_path)
        if not content:
            self.log("error", f"Failed to read symbol library: {symbol_lib_path}")
            return datasheets
        
        try:
            # Parse S-expressions
            parsed = self.parser.parse(content)
            if not parsed:
                self.log("warning", f"Failed to parse symbol library: {symbol_lib_path}")
                return datasheets
            
            symbols_found = 0
            datasheets_found = 0
            non_pdf_skipped = 0
            seen_datasheets = set()  # Track unique datasheet URLs
            
            # Find all symbols in the library
            for item in parsed:
                if isinstance(item, list) and len(item) > 0 and item[0] == 'symbol':
                    symbols_found += 1
                    symbol_name = item[1] if len(item) > 1 else "unknown"
                    
                    # Look for datasheet property in this symbol
                    for sub_item in item:
                        if isinstance(sub_item, list) and len(sub_item) >= 3:
                            if sub_item[0] == 'property' and sub_item[1] == 'Datasheet':
                                datasheet_value = sub_item[2]
                                
                                # Filter out empty datasheets
                                if datasheet_value and datasheet_value not in ('', '~'):
                                    # Check if it's a PDF
                                    if datasheet_value.lower().endswith('.pdf'):
                                        # Only add if we haven't seen this datasheet before
                                        if datasheet_value not in seen_datasheets:
                                            datasheets.append((symbol_name, datasheet_value))
                                            seen_datasheets.add(datasheet_value)
                                            datasheets_found += 1
                                    else:
                                        non_pdf_skipped += 1
            
            self.log("info", f"Scanned {symbols_found} symbols")
            self.log("info", f"Found {datasheets_found} unique PDF datasheet references")
            if non_pdf_skipped > 0:
                self.log("info", f"Skipped {non_pdf_skipped} non-PDF datasheets")
                
        except Exception as e:
            self.log("error", f"Error parsing symbol library: {str(e)}")
        
        return datasheets
    
    def copy_datasheets(
        self,
        datasheets: List[Tuple[str, str]],
        progress_callback: Optional[Callable] = None
    ) -> Tuple[int, int]:
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
        
        @return Tuple of (downloaded_count, copied_count) for internet downloads and local file copies
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
        
        downloaded_count = 0
        copied_count = 0
        self.datasheet_map = {}  # Store mapping for reference updates
        
        # Process each unique datasheet reference
        for datasheet_ref, comp_name in unique_datasheets.items():
            self.log("info", f"Processing datasheet: {datasheet_ref}")
            
            # Check if it's a PDF
            if not datasheet_ref.lower().endswith('.pdf'):
                self.log("info", f"Skipping non-PDF datasheet: {datasheet_ref}")
                continue
            
            # Determine if it's a URL or local file path
            is_url = datasheet_ref.startswith('http://') or datasheet_ref.startswith('https://')
            
            # Extract filename from URL or path
            if is_url:
                # Get filename from URL
                parsed_url = urlparse(datasheet_ref)
                filename = os.path.basename(unquote(parsed_url.path))
                if not filename or not filename.endswith('.pdf'):
                    # Generate filename from component name
                    filename = f"{comp_name.replace(':', '_').replace('/', '_')}.pdf"
            else:
                # Local file path - get just the filename
                filename = os.path.basename(datasheet_ref)
            
            dest_path = os.path.join(self.datasheet_dir_path, filename)
            new_ref = f"${{KIPRJMOD}}/{self.datasheet_dir}/{filename}"
            
            if is_url:
                # Download from internet
                self.log("info", f"Identified as URL download: {filename}")
                if self.download_datasheet(datasheet_ref, dest_path):
                    downloaded_count += 1
                    self.datasheet_map[datasheet_ref] = new_ref
                    self.log("success", f"Downloaded: {filename}")
            else:
                # Copy local file
                self.log("info", f"Identified as local file copy: {filename}")
                
                # Expand KiCad path variables
                expanded_path = expand_kicad_path(datasheet_ref, self.project_dir)
                self.log("info", f"Source path: {expanded_path}")
                
                if not os.path.exists(expanded_path):
                    self.log("error", f"Source file not found: {expanded_path}")
                    continue
                
                try:
                    # Check if destination exists and compare dates
                    if os.path.exists(dest_path):
                        source_mtime = os.path.getmtime(expanded_path)
                        dest_mtime = os.path.getmtime(dest_path)
                        
                        if source_mtime <= dest_mtime:
                            self.log("info", f"Destination file is up-to-date: {filename}")
                            copied_count += 1
                            self.datasheet_map[datasheet_ref] = new_ref
                            continue
                        else:
                            self.log("info", f"Source file is newer, copying")
                    
                    # Copy file
                    shutil.copy2(expanded_path, dest_path)
                    copied_count += 1
                    self.datasheet_map[datasheet_ref] = new_ref
                    self.log("success", f"Copied: {filename}")
                    
                except Exception as e:
                    self.log("error", f"Error copying file: {str(e)}")
        
        self.log("info", f"Downloaded {downloaded_count} datasheets from internet, copied {copied_count} from local files")
        return (downloaded_count, copied_count)
    
    def download_datasheet(self, url: str, dest_path: str) -> bool:
        """
        @brief Download a datasheet PDF from a URL
        
        Downloads PDF files from internet URLs (http://, https://) to the
        local project directory. This handles web-hosted datasheets that
        need to be downloaded for offline project portability.
        
        Only processes URLs ending with .pdf extension - non-PDF URLs are skipped.
        
        If destination file already exists, compares dates and keeps the latest version.
        
        @param url: Internet URL to download from (e.g., "http://www.vishay.com/docs/88503/1n4001.pdf")
        @param dest_path: Destination file path in local project
        
        @return True if download successful, False otherwise
        
        @throws Exception if download fails
        """
        self.log("info", f"Downloading datasheet from: {url}")
        
        # Verify URL ends with .pdf
        if not url.lower().endswith('.pdf'):
            self.log("warning", f"URL does not end with .pdf, skipping: {url}")
            return False
        
        try:
            # Check if destination file already exists
            if os.path.exists(dest_path):
                self.log("info", f"Destination file already exists: {dest_path}")
                # Get local file modification time
                local_mtime = os.path.getmtime(dest_path)
                
                # Try to get remote file modification time
                try:
                    req = urllib.request.Request(url, method='HEAD')
                    with urllib.request.urlopen(req, timeout=10) as response:
                        last_modified = response.headers.get('Last-Modified')
                        if last_modified:
                            from email.utils import parsedate_to_datetime
                            remote_mtime = parsedate_to_datetime(last_modified).timestamp()
                            
                            if remote_mtime <= local_mtime:
                                self.log("info", f"Local file is up-to-date, skipping download")
                                return True  # File exists and is current
                            else:
                                self.log("info", f"Remote file is newer, downloading update")
                        else:
                            self.log("info", f"Cannot determine remote file date, re-downloading")
                except Exception as e:
                    self.log("warning", f"Cannot check remote file date: {str(e)}, re-downloading")
            
            # Download the file
            self.log("info", f"Downloading to: {dest_path}")
            urllib.request.urlretrieve(url, dest_path)
            
            # Verify file was downloaded
            if not os.path.exists(dest_path):
                self.log("error", f"File was not downloaded: {dest_path}")
                return False
            
            file_size = os.path.getsize(dest_path)
            self.log("success", f"Downloaded successfully ({file_size} bytes)")
            
            # Verify it's a PDF (check magic bytes)
            try:
                with open(dest_path, 'rb') as f:
                    header = f.read(4)
                    if header != b'%PDF':
                        self.log("warning", f"Downloaded file does not appear to be a PDF")
                    else:
                        self.log("info", f"PDF validation successful")
            except Exception as e:
                self.log("warning", f"Could not validate PDF: {str(e)}")
            
            return True
            
        except urllib.error.HTTPError as e:
            self.log("error", f"HTTP error {e.code} downloading {url}: {str(e)}")
            return False
        except urllib.error.URLError as e:
            self.log("error", f"URL error downloading {url}: {str(e)}")
            return False
        except Exception as e:
            self.log("error", f"Error downloading {url}: {str(e)}")
            return False
    
    def update_schematic_references(
        self,
        schematic_path: str,
        datasheet_map: dict
    ) -> bool:
        """
        @brief Update datasheet references in schematic file to point to local copies
        
        Scans schematic file for (property "Datasheet" "value") entries and replaces
        old datasheet URLs or paths with new local paths using ${KIPRJMOD} variable.
        
        Example: (property "Datasheet" "http://www.vishay.com/docs/88503/1n4001.pdf")
        becomes: (property "Datasheet" "${KIPRJMOD}/Data_Sheets/1n4001.pdf")
        
        @param schematic_path: Path to .kicad_sch file
        @param datasheet_map: Dictionary mapping old refs to new local paths
        
        @return True if update successful, False otherwise
        """
        self.log("info", f"Updating datasheet references in schematic: {schematic_path}")
        
        if not datasheet_map:
            self.log("info", "No datasheet mappings to apply")
            return True
        
        # Read schematic file content
        content = safe_read_file(schematic_path)
        if not content:
            self.log("error", f"Failed to read schematic: {schematic_path}")
            return False
        
        self.log("info", "Starting schematic reference update process")
        
        original_content = content
        updates_made = 0
        
        # Find and replace all datasheet property values
        for old_ref, new_ref in datasheet_map.items():
            if old_ref in content:
                # Count occurrences before replacement
                occurrences = content.count(old_ref)
                content = content.replace(old_ref, new_ref)
                updates_made += occurrences
                self.log("info", f"Updated {occurrences} reference(s): {old_ref} -> {new_ref}")
        
        # Only write if changes were made
        if content == original_content:
            self.log("info", "No datasheet references needed updating in this schematic")
            return True
        
        # Create backup before modifying
        self.log("info", "Creating backup before modifying schematic")
        if not self.backup_manager.create_backup(schematic_path):
            self.log("warning", f"Failed to create backup for: {schematic_path}")
            # Continue anyway as this is not critical
        else:
            self.log("info", "Backup created successfully")
        
        # Write updated content back to file
        try:
            with open(schematic_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log("success", f"Schematic updated successfully: {schematic_path}")
            self.log("info", f"Total references updated in this schematic: {updates_made}")
            return True
        except Exception as e:
            self.log("error", f"Failed to write updated schematic: {str(e)}")
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
        self.log("info", f"Updating datasheet references in symbol library: {symbol_lib_path}")
        
        if not datasheet_map:
            self.log("info", "No datasheet mappings to apply")
            return True
        
        # Read symbol library content
        content = safe_read_file(symbol_lib_path)
        if not content:
            self.log("error", f"Failed to read symbol library: {symbol_lib_path}")
            return False
        
        self.log("info", "Starting reference update process")
        
        original_content = content
        updates_made = 0
        
        # Replace old datasheet references with ${KIPRJMOD}/Data_Sheets/... paths
        for old_ref, new_ref in datasheet_map.items():
            if old_ref in content:
                # Count occurrences before replacement
                occurrences = content.count(old_ref)
                content = content.replace(old_ref, new_ref)
                updates_made += occurrences
                self.log("info", f"Updated {occurrences} reference(s): {old_ref} -> {new_ref}")
        
        # Only write if changes were made
        if content == original_content:
            self.log("info", "No datasheet references needed updating")
            return True
        
        # Create backup before modifying
        self.log("info", "Creating backup before modifying symbol library")
        if not self.backup_manager.create_backup(symbol_lib_path):
            self.log("warning", f"Failed to create backup for: {symbol_lib_path}")
            # Continue anyway as this is not critical
        else:
            self.log("info", "Backup created successfully")
        
        # Write updated content back to file
        try:
            with open(symbol_lib_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log("success", f"Symbol library updated successfully: {symbol_lib_path}")
            self.log("info", f"Total references updated: {updates_made}")
            return True
        except Exception as e:
            self.log("error", f"Failed to write updated symbol library: {str(e)}")
            return False
    
    def localize_all_datasheets(
        self,
        symbol_libs: List[str],
        schematic_files: List[str],
        progress_callback: Optional[Callable] = None
    ) -> Tuple[int, int]:
        """
        @brief Main entry point to localize all datasheets in the project
        
        Scans all symbol libraries for datasheet references, copies/downloads 
        datasheets, and updates all references in both symbol libraries and 
        schematic files. In KiCad, datasheets are stored in symbol definitions
        but are also referenced in schematic files.
        
        @param symbol_libs: List of symbol library paths to scan
        @param schematic_files: List of schematic file paths (.kicad_sch) to update
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
        downloaded_count, copied_count = self.copy_datasheets(all_datasheets, progress_callback)
        total_datasheets = downloaded_count + copied_count
        
        # Get datasheet_map from copy operation
        datasheet_map = getattr(self, 'datasheet_map', {})
        
        if not datasheet_map:
            self.log("warning", "No datasheet mappings created, skipping reference updates")
            return (total_datasheets, 0)
        
        # Update all references in symbol library files
        self.log("info", f"Updating datasheet references in {len(symbol_libs)} symbol libraries")
        updated_count = 0
        for symbol_lib in symbol_libs:
            if os.path.exists(symbol_lib):
                if self.update_symbol_references(symbol_lib, datasheet_map):
                    updated_count += 1
        
        # Update all references in schematic files
        self.log("info", f"Updating datasheet references in {len(schematic_files)} schematic files")
        schematic_updated_count = 0
        for schematic_file in schematic_files:
            if os.path.exists(schematic_file):
                if self.update_schematic_references(schematic_file, datasheet_map):
                    schematic_updated_count += 1
        
        total_updated = updated_count + schematic_updated_count
        
        self.log("success", f"Datasheet localization complete: {total_datasheets} datasheets processed ({downloaded_count} downloaded from internet, {copied_count} copied from local files), {total_updated} files updated ({updated_count} symbol libs, {schematic_updated_count} schematics)")
        
        return (total_datasheets, total_updated)
