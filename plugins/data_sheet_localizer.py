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
all references to use local paths with ${KIPRJMOD}. Bakery scans schematic
symbol properties and the live PCB footprint fields exposed by KiCad.

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
import re
import http.client
import shutil
import urllib.request
import urllib.error
from email.message import Message
from typing import List, Optional, Callable, Set, Tuple, Dict
from urllib.parse import parse_qs, unquote, urlparse

from .constants import (
    ENV_VAR_KIPRJMOD, MAX_FILE_SIZE_BYTES, SEXPR_DATASHEET, SEXPR_PROPERTY,
    SEXPR_SYMBOL
)
from .base_localizer import BaseLocalizer
from .sexpr_parser import SExpressionParseError
from .utils import (
    atomic_write_file, expand_kicad_path, make_collision_safe_filename,
    safe_read_file, validate_path_safety, KicadPathResolutionError
)


class DataSheetLocalizer(BaseLocalizer):
    """!
    @brief Handles localization of component datasheets from URLs and global locations
    
    Scans symbol libraries, schematics, and PCB footprint fields for datasheet
    references, downloads or copies them to the project-local directory, and
    updates all references.
    
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

        @throws ValueError if datasheet_dir resolves outside project_dir
        """
        super().__init__(logger)
        self.project_dir = project_dir
        self.datasheet_dir = datasheet_dir
        self.datasheet_dir_path = os.path.join(project_dir, datasheet_dir)
        if not validate_path_safety(self.datasheet_dir_path, project_dir):
            raise ValueError(f"Datasheets directory name is unsafe: {datasheet_dir}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_web_url(ref: str) -> bool:
        """
        @brief Return True if ref is an http/https URL
        
        @param ref: Datasheet reference string
        @return True if ref starts with http:// or https://
        """
        return ref.startswith('http://') or ref.startswith('https://')

    @staticmethod
    def _normalize_download_url(url: str) -> str:
        """
        @brief Resolve known wrapper URLs to their direct download target.

        @param url: Original datasheet URL.
        @return Direct URL when a supported wrapper target is present.
        """
        parsed_url = urlparse(url)
        if (
            parsed_url.netloc.lower().endswith('ti.com')
            and parsed_url.path.endswith('/suppproductinfo.tsp')
        ):
            target_values = parse_qs(parsed_url.query).get('gotoUrl', [])
            if target_values:
                target = unquote(target_values[0])
                if target.startswith(('http://', 'https://')):
                    return target
        return url

    def _classify_datasheet_ref(self, value: str, seen: Set[str]) -> str:
        """
        @brief Classify a raw datasheet property value for inclusion

        Used by both scan_symbol_datasheets and scan_schematic_datasheets to
        apply identical filtering and deduplication rules in one place.

        @param value: Raw datasheet property string from KiCad file
        @param seen: Set of already-seen references (mutated on 'add')

        @return One of:
            'add'       - include and add to seen
            'empty'     - blank / '~' placeholder, skip silently
            'localised' - already a ${KIPRJMOD} path, skip silently
            'non_pdf'   - local path without .pdf extension, skip and count
            'duplicate' - already in seen, skip silently
        """
        if not value or value in ('', '~'):
            return 'empty'
        if value.startswith(f'${{{ENV_VAR_KIPRJMOD}}}'):
            return 'localised'
        if not self._is_web_url(value) and not value.lower().endswith('.pdf'):
            return 'non_pdf'
        if value in seen:
            return 'duplicate'
        seen.add(value)
        return 'add'

    def _make_http_request(
        self,
        url: str,
        method: str = 'GET'
    ) -> urllib.request.Request:
        """
        @brief Build an urllib Request with a browser-like User-Agent header

        Centralises request construction so the User-Agent header is set
        consistently for every outbound HTTP call.

        @param url: Target URL
        @param method: HTTP method ('GET' or 'HEAD')

        @return Configured urllib.request.Request object
        """
        req = urllib.request.Request(url, method=method)
        req.add_header('User-Agent', 'Mozilla/5.0')
        return req

    def _is_valid_pdf(self, file_path: str) -> bool:
        """
        @brief Check if a file is a valid PDF by inspecting its header bytes

        Reads the first 4 bytes of the file and checks for the PDF magic
        number (%PDF). This is a lightweight sanity check after downloading
        or copying a datasheet.

        @param file_path: Path to the file to check

        @return True if the file starts with the PDF magic bytes, False otherwise
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
            return header == b'%PDF'
        except OSError:
            return False

    @staticmethod
    def _is_valid_pdf_content(content: bytes) -> bool:
        """
        @brief Check whether binary content starts with the PDF signature

        @param content: Downloaded binary content
        @return True when content begins with the PDF magic bytes
        """
        return content.startswith(b'%PDF')

    def _should_update_file(self, source_path: str, dest_path: str) -> bool:
        """
        @brief Determine whether a destination file should be overwritten by the source

        Compares file modification times. Returns True (update needed) when:
        - The destination file does not exist, or
        - The source file is newer than the destination file.

        @param source_path: Path to the source file
        @param dest_path: Path to the destination file

        @return True if the destination should be updated, False if it is already current
        """
        if not os.path.exists(dest_path):
            return True
        try:
            return os.path.getmtime(source_path) > os.path.getmtime(dest_path)
        except OSError:
            return True

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
        try:
            content = safe_read_file(symbol_lib_path)
        except (OSError, ValueError) as e:
            self.log("error", f"Failed to read symbol library: {symbol_lib_path}: {e}")
            return datasheets
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
            seen_datasheets: Set[str] = set()

            # Find all symbols in the library
            for item in parsed:
                if isinstance(item, list) and len(item) > 0 and item[0] == SEXPR_SYMBOL:
                    symbols_found += 1
                    symbol_name = item[1].strip('"') if len(item) > 1 else "unknown"

                    # Look for datasheet property in this symbol
                    for sub_item in item:
                        if isinstance(sub_item, list) and len(sub_item) >= 3:
                            # Strip quotes from property name/value (parser preserves them)
                            prop_name = sub_item[1].strip('"') if isinstance(sub_item[1], str) else sub_item[1]
                            prop_value = sub_item[2].strip('"') if isinstance(sub_item[2], str) else sub_item[2]
                            if (
                                sub_item[0] == SEXPR_PROPERTY
                                and prop_name == SEXPR_DATASHEET
                            ):
                                verdict = self._classify_datasheet_ref(prop_value, seen_datasheets)
                                if verdict == 'add':
                                    datasheets.append((symbol_name, prop_value))
                                    datasheets_found += 1
                                elif verdict == 'non_pdf':
                                    non_pdf_skipped += 1
            
            self.log("info", f"Scanned {symbols_found} symbols")
            self.log("info", f"Found {datasheets_found} unique datasheet references")
            if non_pdf_skipped > 0:
                self.log("info", f"Skipped {non_pdf_skipped} non-PDF local datasheets")
                
        except (SExpressionParseError, TypeError, ValueError) as e:
            self.log("error", f"Error parsing symbol library: {str(e)}")
        
        return datasheets

    def _resolve_datasheet_target(
        self,
        component_name: str,
        datasheet_ref: str
    ) -> Optional[Tuple[bool, str, str, str]]:
        """
        @brief Resolve a datasheet reference to its local destination

        @param component_name: Component name used for fallback filenames
        @param datasheet_ref: URL or local datasheet reference
        @return Tuple of (is_url, source, destination, new_reference), or None
        """
        is_url = self._is_web_url(datasheet_ref)
        source_ref = (
            self._normalize_download_url(datasheet_ref)
            if is_url
            else datasheet_ref
        )
        if is_url:
            parsed_url = urlparse(source_ref)
            url_basename = os.path.basename(unquote(parsed_url.path))
            if url_basename and url_basename.lower().endswith('.pdf'):
                filename = url_basename
            else:
                filename = self._resolve_url_filename(
                    source_ref,
                    component_name
                )
                if filename is None:
                    self.log("info", f"Skipping non-PDF URL: {datasheet_ref}")
                    return None
        else:
            if not datasheet_ref.lower().endswith('.pdf'):
                self.log(
                    "info",
                    f"Skipping non-PDF local datasheet: {datasheet_ref}"
                )
                return None
            filename = os.path.basename(datasheet_ref)

        filename = make_collision_safe_filename(filename, datasheet_ref)
        dest_path = os.path.join(self.datasheet_dir_path, filename)
        if not validate_path_safety(dest_path, self.datasheet_dir_path):
            self.log(
                "error",
                f"Skipping unsafe datasheet destination path: {filename}"
            )
            return None

        new_ref = (
            f"${{{ENV_VAR_KIPRJMOD}}}/{self.datasheet_dir}/{filename}"
        )
        return is_url, source_ref, dest_path, new_ref

    def _copy_local_datasheet(
        self,
        datasheet_ref: str,
        dest_path: str
    ) -> bool:
        """
        @brief Copy a local datasheet when the destination is missing or stale

        @param datasheet_ref: Original local datasheet reference
        @param dest_path: Project-local destination path
        @return True when a valid source exists and the destination is current
        """
        try:
            expanded_path = expand_kicad_path(
                datasheet_ref,
                self.project_dir
            )
        except KicadPathResolutionError as error:
            self.log("error", f"Could not resolve datasheet path: {error}")
            return False

        self.log("info", f"Source path: {expanded_path}")
        if not os.path.exists(expanded_path):
            self.log("error", f"Source file not found: {expanded_path}")
            return False
        if not self._is_valid_pdf(expanded_path):
            self.log("error", f"Source file is not a valid PDF: {expanded_path}")
            return False

        filename = os.path.basename(dest_path)
        try:
            if (
                os.path.exists(dest_path)
                and not self._should_update_file(expanded_path, dest_path)
            ):
                self.log(
                    "info",
                    f"Destination file is up-to-date: {filename}"
                )
                return True

            shutil.copy2(expanded_path, dest_path)
            self.log("success", f"Copied: {filename}")
            return True
        except (OSError, shutil.Error) as error:
            self.log("error", f"Error copying file: {error}")
            return False
    
    def copy_datasheets(
        self,
        datasheets: List[Tuple[str, str]]
    ) -> Tuple[int, int, dict]:
        """
        @brief Copy or download datasheets to local project directory
        
        Creates datasheet directory if needed, then:
        - Downloads PDF files from internet URLs (http://, https://)
        - Copies local file paths to the project directory
        
        Automatically deduplicates URLs to avoid copying the same datasheet 
        multiple times (e.g., when multiple component instances reference 
        the         same datasheet URL).
        
        @param datasheets: List of (component_name, datasheet_ref) tuples
        
        @return Tuple of (downloaded_count, copied_count, datasheet_map) where datasheet_map
                maps old references to new local ${KIPRJMOD} paths
        """
        self.log("info", f"Copying datasheets to: {self.datasheet_dir_path}")

        # Create datasheet directory if it doesn't exist
        if not os.path.exists(self.datasheet_dir_path):
            os.makedirs(self.datasheet_dir_path)
            self.log("info", f"Created datasheet directory: {self.datasheet_dir}")

        # Deduplicate while preserving first-seen order
        unique_datasheets: Dict[str, str] = {}  # {datasheet_ref: component_name}
        for comp_name, datasheet_ref in datasheets:
            if datasheet_ref not in unique_datasheets:
                unique_datasheets[datasheet_ref] = comp_name

        self.log("info", f"Processing {len(unique_datasheets)} unique datasheets")

        downloaded_count = 0
        copied_count = 0
        datasheet_map: Dict[str, str] = {}  # Maps old refs to new local paths
        
        # Process each unique datasheet reference
        for datasheet_ref, comp_name in unique_datasheets.items():
            self.log("info", f"Processing datasheet: {datasheet_ref}")
            target = self._resolve_datasheet_target(comp_name, datasheet_ref)
            if target is None:
                continue
            is_url, source_ref, dest_path, new_ref = target
            filename = os.path.basename(dest_path)
            
            if is_url:
                self.log("info", f"Identified as URL download: {filename}")
                if self.download_datasheet(source_ref, dest_path):
                    downloaded_count += 1
                    datasheet_map[datasheet_ref] = new_ref
                    self.log("success", f"Downloaded: {filename}")
            else:
                self.log("info", f"Identified as local file copy: {filename}")
                if self._copy_local_datasheet(datasheet_ref, dest_path):
                    copied_count += 1
                    datasheet_map[datasheet_ref] = new_ref
        
        self.log("info", f"Downloaded {downloaded_count} datasheets from internet, copied {copied_count} from local files")
        return (downloaded_count, copied_count, datasheet_map)
    
    def _resolve_url_filename(self, url: str, comp_name: str) -> Optional[str]:
        """
        @brief Probe a URL via HTTP HEAD to determine filename and confirm it is a PDF

        Used for URLs that do not end with .pdf (e.g. manufacturer redirect links).
        Checks the Content-Type header and tries to extract a filename from the
        Content-Disposition header.

        Strategy:
        - If headers clearly indicate PDF → return filename
        - If headers clearly indicate NOT a PDF (e.g. text/html) → return None
        - If the HEAD request fails or headers are absent/ambiguous → return a
          fallback filename so the download is still attempted; _is_valid_pdf
          will reject the file if it turns out not to be a PDF.

        @param url: URL to probe
        @param comp_name: Component name used as fallback filename stem

        @return Filename string (with .pdf extension) to attempt download, or
                None only when headers explicitly confirm a non-PDF resource
        """
        safe_name = comp_name.replace(':', '_').replace('/', '_').replace('\\', '_')
        fallback_filename = f"{safe_name}.pdf"

        try:
            req = self._make_http_request(url, method='HEAD')
            with urllib.request.urlopen(req, timeout=10) as response:
                content_type = response.headers.get('Content-Type', '')
                ct_lower = content_type.lower()
                final_url = response.geturl()
                if isinstance(final_url, str):
                    final_basename = os.path.basename(
                        unquote(urlparse(final_url).path)
                    )
                    if final_basename.lower().endswith('.pdf'):
                        return final_basename

                # Explicitly non-PDF content type - skip
                if ct_lower and 'pdf' not in ct_lower and any(
                    ct_lower.startswith(t) for t in ('text/html', 'text/plain', 'application/json',
                                                      'application/xml', 'image/')
                ):
                    self.log("info", f"URL Content-Type is '{content_type}', not PDF - skipping: {url}")
                    return None

                # Try Content-Disposition for an explicit filename
                disposition = response.headers.get('Content-Disposition', '')
                if disposition:
                    message = Message()
                    message['Content-Disposition'] = disposition
                    cd_name = message.get_filename() or ''
                    if cd_name:
                        # Server-supplied name: strip any directory components
                        # (both separators, since headers aren't OS-specific) to
                        # prevent it from escaping the datasheet directory.
                        cd_name = os.path.basename(cd_name.replace('\\', '/'))
                        if cd_name and cd_name not in ('.', '..'):
                            if not cd_name.lower().endswith('.pdf'):
                                cd_name += '.pdf'
                            return cd_name

                # Content-Type is PDF or ambiguous - proceed with fallback name
                return fallback_filename

        except (
            OSError,
            ValueError,
            urllib.error.URLError,
            http.client.HTTPException
        ) as e:
            # Cannot reach server or HEAD not supported - attempt download anyway
            self.log("warning", f"Could not probe URL headers for {url}: {str(e)} - will attempt download")
            return fallback_filename

    def download_datasheet(self, url: str, dest_path: str) -> bool:
        """
        @brief Download a datasheet PDF from a URL

        Downloads PDF files from internet URLs (http://, https://) to the
        local project directory. This handles web-hosted datasheets that
        need to be downloaded for offline project portability.

        Accepts URLs regardless of file extension; the caller is responsible
        for confirming the resource is a PDF before calling this method.

        If destination file already exists, compares dates and keeps the latest version.
        
        @param url: Internet URL to download from (e.g., "http://www.vishay.com/docs/88503/1n4001.pdf")
        @param dest_path: Destination file path in local project
        
        @return True if download successful, False otherwise
        
        @throws Exception if download fails
        """
        self.log("info", f"Downloading datasheet from: {url}")

        try:
            # Check if destination file already exists
            if os.path.exists(dest_path):
                self.log("info", f"Destination file already exists: {dest_path}")
                # Get local file modification time
                local_mtime = os.path.getmtime(dest_path)

                # Try to get remote file modification time
                try:
                    req = self._make_http_request(url, method='HEAD')
                    with urllib.request.urlopen(req, timeout=10) as response:
                        last_modified = response.headers.get('Last-Modified')
                        if last_modified:
                            from email.utils import parsedate_to_datetime
                            remote_mtime = parsedate_to_datetime(last_modified).timestamp()

                            if (
                                remote_mtime <= local_mtime
                                and self._is_valid_pdf(dest_path)
                            ):
                                self.log("info", f"Local file is up-to-date, skipping download")
                                return True  # File exists and is current
                            else:
                                self.log("info", f"Remote file is newer, downloading update")
                        else:
                            self.log("info", f"Cannot determine remote file date, re-downloading")
                except (
                    OSError,
                    ValueError,
                    urllib.error.URLError,
                    http.client.HTTPException
                ) as e:
                    self.log("warning", f"Cannot check remote file date: {str(e)}, re-downloading")

            # Download the file using a browser-like User-Agent to avoid 403 blocks
            self.log("info", f"Downloading to: {dest_path}")
            req = self._make_http_request(url, method='GET')
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read(MAX_FILE_SIZE_BYTES + 1)

            if len(content) > MAX_FILE_SIZE_BYTES:
                self.log(
                    "error",
                    f"Downloaded file exceeds {MAX_FILE_SIZE_BYTES} bytes: {url}"
                )
                return False
            if not self._is_valid_pdf_content(content):
                self.log(
                    "error",
                    f"Downloaded content is not a valid PDF: {url}"
                )
                return False

            atomic_write_file(dest_path, content)

            file_size = os.path.getsize(dest_path)
            self.log("success", f"Downloaded successfully ({file_size} bytes)")
            self.log("info", "PDF validation successful")

            return True
            
        except urllib.error.HTTPError as e:
            self.log("error", f"HTTP error {e.code} downloading {url}: {str(e)}")
            return False
        except urllib.error.URLError as e:
            self.log("error", f"URL error downloading {url}: {str(e)}")
            return False
        except (OSError, ValueError, http.client.HTTPException) as e:
            self.log("error", f"Error downloading {url}: {str(e)}")
            return False
    
    def _update_file_references(
        self,
        file_path: str,
        datasheet_map: dict,
        file_type: str
    ) -> bool:
        """
        @brief Generic method to update datasheet references in any KiCad file
        
        Reads file, replaces old datasheet references with new local paths,
        and writes updated content.
        
        @param file_path: Path to file to update (.kicad_sym or .kicad_sch)
        @param datasheet_map: Dictionary mapping old refs to new local paths
        @param file_type: Description of file type for logging ("schematic" or "symbol library")
        
        @return True if update successful, False otherwise
        """
        self.log("info", f"Updating datasheet references in {file_type}: {file_path}")
        
        if not datasheet_map:
            self.log("info", "No datasheet mappings to apply")
            return True
        
        # Read file content
        try:
            if self.is_file_locked(file_path):
                raise PermissionError(f"{file_type.capitalize()} is locked")
            expected_mtime_ns = os.stat(file_path).st_mtime_ns
            content = safe_read_file(file_path)
        except (OSError, ValueError) as e:
            self.log("error", f"Failed to read {file_type}: {file_path}: {e}")
            return False
        if not content:
            self.log("error", f"Failed to read {file_type}: {file_path}")
            return False
        
        self.log("info", f"Starting {file_type} reference update process")
        
        original_content = content
        updates_made = 0
        
        # Replace old datasheet references with new local paths
        for old_ref, new_ref in datasheet_map.items():
            if old_ref in content:
                occurrences = content.count(old_ref)
                content = content.replace(old_ref, new_ref)
                updates_made += occurrences
                self.log("info", f"Updated {occurrences} reference(s): {old_ref} -> {new_ref}")
        
        # Only write if changes were made
        if content == original_content:
            self.log("info", f"No datasheet references needed updating in this {file_type}")
            return True
        
        # Write updated content back to file
        try:
            self._ensure_file_unchanged(file_path, expected_mtime_ns)
            atomic_write_file(file_path, content)
            self.log("success", f"{file_type.capitalize()} updated successfully: {file_path}")
            self.log("info", f"Total references updated in this {file_type}: {updates_made}")
            return True
        except (OSError, UnicodeError, RuntimeError) as e:
            self.log("error", f"Failed to write updated {file_type}: {str(e)}")
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
        return self._update_file_references(schematic_path, datasheet_map, "schematic")

    def update_pcb_references(
        self,
        pcb_path: str,
        datasheet_map: dict
    ) -> bool:
        """
        @brief Update datasheet references in a PCB file.

        @param pcb_path: Path to the .kicad_pcb file.
        @param datasheet_map: Original-to-local datasheet reference map.
        @return True if the PCB was updated successfully.
        """
        return self._update_file_references(
            pcb_path,
            datasheet_map,
            "PCB"
        )
    
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
        return self._update_file_references(symbol_lib_path, datasheet_map, "symbol library")
    
    def _scan_design_file_datasheets(
        self,
        file_path: str,
        file_type: str
    ) -> List[Tuple[str, str]]:
        """
        @brief Scan a schematic or PCB file for datasheet properties.

        @param file_path: KiCad design file path.
        @param file_type: Human-readable file type used in logging.
        @return Unique datasheet name/reference pairs.
        """
        self.log("info", f"Scanning {file_type} for datasheets: {file_path}")
        datasheets = []

        try:
            content = safe_read_file(file_path)
        except (OSError, ValueError) as error:
            self.log(
                "error",
                f"Failed to read {file_type}: {file_path}: {error}"
            )
            return datasheets
        if not content:
            self.log("error", f"Failed to read {file_type}: {file_path}")
            return datasheets

        seen_datasheets: Set[str] = set()
        pattern = re.compile(r'\(property\s+"Datasheet"\s+"([^"]+)"')
        matches = pattern.findall(content)
        non_pdf_skipped = 0

        for value in matches:
            verdict = self._classify_datasheet_ref(
                value,
                seen_datasheets
            )
            if verdict == 'add':
                datasheets.append((file_type, value))
            elif verdict == 'non_pdf':
                non_pdf_skipped += 1

        self.log(
            "info",
            f"Found {len(datasheets)} unique datasheet references in "
            f"{file_type}"
        )
        if non_pdf_skipped > 0:
            self.log(
                "info",
                f"Skipped {non_pdf_skipped} non-PDF local datasheets in "
                f"{file_type}"
            )
        return datasheets

    def scan_schematic_datasheets(
        self,
        schematic_path: str
    ) -> List[Tuple[str, str]]:
        """
        @brief Scan a schematic file for datasheet references
        
        Parses a .kicad_sch file and extracts all (property "Datasheet" "...") 
        values. This is needed on re-runs where the local symbol library has 
        already been updated to ${KIPRJMOD} paths, but the schematics may still 
        contain original URLs or global paths.
        
        @param schematic_path: Path to .kicad_sch file
        
        @return List of tuples ("schematic", datasheet_reference) with duplicates removed
        """
        return self._scan_design_file_datasheets(
            schematic_path,
            "schematic"
        )

    def scan_pcb_datasheets(
        self,
        pcb_path: str
    ) -> List[Tuple[str, str]]:
        """
        @brief Scan a PCB file for datasheet references.

        @param pcb_path: Path to a .kicad_pcb file.
        @return Unique datasheet name/reference pairs.
        """
        return self._scan_design_file_datasheets(pcb_path, "PCB")

    def scan_board_datasheets(self, board) -> List[Tuple[str, str]]:
        """
        @brief Scan the live KiCad board for footprint datasheet fields.

        @param board: Active KiCad BOARD object.
        @return Unique footprint reference/datasheet pairs.

        @throws RuntimeError if KiCad board fields cannot be read.
        """
        datasheets = []
        seen_datasheets: Set[str] = set()

        try:
            for footprint in board.GetFootprints():
                component_name = str(footprint.GetReference()) or "PCB"
                for field in footprint.GetFields():
                    if str(field.GetName()) != SEXPR_DATASHEET:
                        continue
                    value = str(field.GetText())
                    if (
                        self._classify_datasheet_ref(
                            value,
                            seen_datasheets
                        )
                        == 'add'
                    ):
                        datasheets.append((component_name, value))
        except (AttributeError, RuntimeError, TypeError) as error:
            raise RuntimeError(
                f"Failed to scan datasheets from the active PCB: {error}"
            ) from error

        self.log(
            "info",
            f"Found {len(datasheets)} unique datasheet references in PCB"
        )
        return datasheets

    def update_board_references(self, board, datasheet_map: dict) -> bool:
        """
        @brief Update datasheet fields on the active KiCad board.

        @param board: Active KiCad BOARD object.
        @param datasheet_map: Original-to-local datasheet reference map.
        @return True when all matching footprint fields were updated.

        @throws RuntimeError if KiCad board fields cannot be updated.
        """
        updates_made = 0
        try:
            for footprint in board.GetFootprints():
                for field in footprint.GetFields():
                    if str(field.GetName()) != SEXPR_DATASHEET:
                        continue
                    old_reference = str(field.GetText())
                    new_reference = datasheet_map.get(old_reference)
                    if new_reference is None:
                        continue
                    field.SetText(new_reference)
                    updates_made += 1
        except (AttributeError, RuntimeError, TypeError) as error:
            raise RuntimeError(
                f"Failed to update datasheets on the active PCB: {error}"
            ) from error

        self.log(
            "info",
            f"Updated {updates_made} datasheet reference(s) on the active PCB"
        )
        return True

    def localize_all_datasheets(
        self,
        symbol_libs: List[str],
        schematic_files: List[str],
        pcb_files: Optional[List[str]] = None,
        board=None
    ) -> Tuple[int, int]:
        """
        @brief Main entry point to localize all datasheets in the project
        
        Scans symbol libraries, schematic files, PCB files, and the optional live
        board for datasheet references. Scanning design files ensures datasheets
        are still found on re-runs where a local symbol library has already been
        updated to ${KIPRJMOD} paths.
        
        @param symbol_libs: List of symbol library paths to scan
        @param schematic_files: List of schematic file paths (.kicad_sch) to update
        @param pcb_files: Optional list of PCB files to scan and update
        @param board: Optional active KiCad BOARD object
        
        @return Tuple of (datasheets_copied, references_updated)
        """
        self.log("info", "Starting datasheet localization process")
        pcb_files = pcb_files or []
        
        all_datasheets = []
        seen_in_combined: Set[str] = set()

        def _add_unique(entries: List[Tuple[str, str]]) -> None:
            """
            @brief Add unseen datasheet references while preserving order

            @param entries: Datasheet name/reference pairs to merge
            """
            for name, ref in entries:
                if ref not in seen_in_combined:
                    all_datasheets.append((name, ref))
                    seen_in_combined.add(ref)

        # Scan symbol libraries for datasheets
        for symbol_lib in symbol_libs:
            if os.path.exists(symbol_lib):
                datasheets = self.scan_symbol_datasheets(symbol_lib)
                _add_unique(datasheets)

        # Also scan schematic files - on re-runs the symbol lib may already use
        # ${KIPRJMOD} paths, but schematics still contain the original URLs.
        for schematic_file in schematic_files:
            if os.path.exists(schematic_file):
                sch_datasheets = self.scan_schematic_datasheets(schematic_file)
                _add_unique(sch_datasheets)

        for pcb_file in pcb_files:
            if os.path.exists(pcb_file):
                pcb_datasheets = self.scan_pcb_datasheets(pcb_file)
                _add_unique(pcb_datasheets)

        if board is not None:
            _add_unique(self.scan_board_datasheets(board))
        
        self.log(
            "info",
            f"Found {len(all_datasheets)} unique datasheet references across "
            "symbol libraries, schematics, and PCBs"
        )
        
        # Copy/download datasheets
        downloaded_count, copied_count, datasheet_map = self.copy_datasheets(all_datasheets)
        total_datasheets = downloaded_count + copied_count
        
        if not datasheet_map:
            self.log("warning", "No datasheet mappings created, skipping reference updates")
            return (total_datasheets, 0)
        
        # Update all references in symbol library files
        self.log("info", f"Updating datasheet references in {len(symbol_libs)} symbol libraries")
        updated_count = 0
        failed_updates = []
        for symbol_lib in symbol_libs:
            if os.path.exists(symbol_lib):
                if self.update_symbol_references(symbol_lib, datasheet_map):
                    updated_count += 1
                else:
                    failed_updates.append(symbol_lib)
        
        # Update all references in schematic files
        self.log("info", f"Updating datasheet references in {len(schematic_files)} schematic files")
        schematic_updated_count = 0
        for schematic_file in schematic_files:
            if os.path.exists(schematic_file):
                if self.update_schematic_references(schematic_file, datasheet_map):
                    schematic_updated_count += 1
                else:
                    failed_updates.append(schematic_file)

        pcb_updated_count = 0
        for pcb_file in pcb_files:
            if os.path.exists(pcb_file):
                if self.update_pcb_references(pcb_file, datasheet_map):
                    pcb_updated_count += 1
                else:
                    failed_updates.append(pcb_file)

        if board is not None:
            if self.update_board_references(board, datasheet_map):
                pcb_updated_count += 1
            else:
                failed_updates.append("active PCB")

        if failed_updates:
            raise RuntimeError(
                "Failed to update datasheet references in: "
                + ", ".join(failed_updates)
            )
        
        total_updated = (
            updated_count
            + schematic_updated_count
            + pcb_updated_count
        )
        
        self.log("success", f"Datasheet localization complete: {total_datasheets} datasheets processed ({downloaded_count} downloaded from internet, {copied_count} copied from local files), {total_updated} files updated ({updated_count} symbol libs, {schematic_updated_count} schematics, {pcb_updated_count} PCBs)")
        
        return (total_datasheets, total_updated)
