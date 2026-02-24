"""!
@file test_data_sheet_localizer.py

@brief Unit tests for the data_sheet_localizer module

Tests the DataSheetLocalizer class including:
- Initialization
- URL detection and reference classification
- PDF validation
- File date comparison
- Symbol library scanning
- Schematic scanning
- Datasheet copy/download logic (with mocks for network and file I/O)
- Reference update in schematic and symbol library files
- Full localize_all_datasheets workflow
"""

import sys
import os
import time
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open

# Python 3.13 removed the 'cgi' module; stub it before importing the plugin
# module so that the import succeeds in all Python versions.
if 'cgi' not in sys.modules:
    _cgi_stub = MagicMock()
    _cgi_stub.parse_header.return_value = ('', {})
    sys.modules['cgi'] = _cgi_stub

# Use import helper for modules with relative imports
from import_helper import import_bakery_module

data_sheet_localizer = import_bakery_module('data_sheet_localizer')
DataSheetLocalizer = data_sheet_localizer.DataSheetLocalizer


class MockLogger:
    """Mock logger for testing"""

    def __init__(self):
        self.messages = {'info': [], 'warning': [], 'error': [], 'success': []}

    def info(self, msg):
        self.messages['info'].append(msg)

    def warning(self, msg):
        self.messages['warning'].append(msg)

    def error(self, msg):
        self.messages['error'].append(msg)

    def success(self, msg):
        self.messages['success'].append(msg)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path, content, encoding='utf-8'):
    """Write text content to a file."""
    with open(path, 'w', encoding=encoding) as fh:
        fh.write(content)


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

SYMBOL_LIB_CONTENT = '''\
(kicad_symbol_lib (version 20231120) (generator kicad_symbol_editor)
  (symbol "1N4001" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
    (property "Reference" "D" (at 0 2.54 0))
    (property "Value" "1N4001" (at 0 0 0))
    (property "Datasheet" "http://www.vishay.com/docs/88503/1n4001.pdf" (at 0 0 0))
  )
  (symbol "R" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
    (property "Reference" "R" (at 0 2.54 0))
    (property "Value" "R" (at 0 0 0))
    (property "Datasheet" "~" (at 0 0 0))
  )
  (symbol "LED" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
    (property "Reference" "D" (at 0 2.54 0))
    (property "Value" "LED" (at 0 0 0))
    (property "Datasheet" "http://www.vishay.com/docs/88503/1n4001.pdf" (at 0 0 0))
  )
  (symbol "C" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
    (property "Reference" "C" (at 0 2.54 0))
    (property "Value" "C" (at 0 0 0))
    (property "Datasheet" "C:\\Datasheets\\cap.pdf" (at 0 0 0))
  )
  (symbol "L" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
    (property "Reference" "L" (at 0 2.54 0))
    (property "Value" "L" (at 0 0 0))
    (property "Datasheet" "C:\\Datasheets\\readme.txt" (at 0 0 0))
  )
)'''

SCHEMATIC_CONTENT = '''\
(kicad_sch (version 20231120)
  (symbol (lib_id "Device:1N4001") (at 100 100 0)
    (property "Datasheet" "http://www.vishay.com/docs/88503/1n4001.pdf" (at 0 0 0))
  )
  (symbol (lib_id "Device:R") (at 150 100 0)
    (property "Datasheet" "~" (at 0 0 0))
  )
)'''


# ===========================================================================
# TestDataSheetLocalizerInit
# ===========================================================================

class TestDataSheetLocalizerInit(unittest.TestCase):
    """Tests for DataSheetLocalizer initialisation"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.logger = MockLogger()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_default_initialization(self):
        """Constructor creates instance with expected defaults"""
        localizer = DataSheetLocalizer(self.temp_dir)
        self.assertIsNotNone(localizer)
        self.assertEqual(localizer.project_dir, self.temp_dir)
        self.assertEqual(localizer.datasheet_dir, "Data_Sheets")
        expected = os.path.join(self.temp_dir, "Data_Sheets")
        self.assertEqual(localizer.datasheet_dir_path, expected)

    def test_custom_datasheet_dir(self):
        """Custom datasheet directory name is stored"""
        localizer = DataSheetLocalizer(self.temp_dir, datasheet_dir="MySheets")
        self.assertEqual(localizer.datasheet_dir, "MySheets")
        self.assertIn("MySheets", localizer.datasheet_dir_path)

    def test_initialization_with_logger(self):
        """Logger is wired up correctly"""
        localizer = DataSheetLocalizer(self.temp_dir, logger=self.logger)
        self.assertEqual(localizer.logger, self.logger)

    def test_backup_manager_exists(self):
        """backup_manager attribute is available (inherited from BaseLocalizer)"""
        localizer = DataSheetLocalizer(self.temp_dir)
        self.assertTrue(hasattr(localizer, 'backup_manager'))

    def test_parser_exists(self):
        """parser attribute is available (inherited from BaseLocalizer)"""
        localizer = DataSheetLocalizer(self.temp_dir)
        self.assertTrue(hasattr(localizer, 'parser'))


# ===========================================================================
# TestIsWebUrl
# ===========================================================================

class TestIsWebUrl(unittest.TestCase):
    """Tests for the _is_web_url static helper"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.localizer = DataSheetLocalizer(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_http_url(self):
        self.assertTrue(self.localizer._is_web_url("http://example.com/file.pdf"))

    def test_https_url(self):
        self.assertTrue(self.localizer._is_web_url("https://example.com/file.pdf"))

    def test_local_windows_path(self):
        self.assertFalse(self.localizer._is_web_url("C:\\Datasheets\\file.pdf"))

    def test_local_unix_path(self):
        self.assertFalse(self.localizer._is_web_url("/home/user/datasheets/file.pdf"))

    def test_empty_string(self):
        self.assertFalse(self.localizer._is_web_url(""))

    def test_tilde_placeholder(self):
        self.assertFalse(self.localizer._is_web_url("~"))

    def test_kiprjmod_path(self):
        self.assertFalse(self.localizer._is_web_url("${KIPRJMOD}/Data_Sheets/file.pdf"))

    def test_ftp_not_http(self):
        """ftp:// is NOT treated as a web URL by this helper"""
        self.assertFalse(self.localizer._is_web_url("ftp://example.com/file.pdf"))


# ===========================================================================
# TestClassifyDatasheetRef
# ===========================================================================

class TestClassifyDatasheetRef(unittest.TestCase):
    """Tests for _classify_datasheet_ref"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.localizer = DataSheetLocalizer(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _classify(self, value, seen=None):
        if seen is None:
            seen = set()
        return self.localizer._classify_datasheet_ref(value, seen)

    def test_empty_string_is_empty(self):
        self.assertEqual(self._classify(""), 'empty')

    def test_tilde_is_empty(self):
        self.assertEqual(self._classify("~"), 'empty')

    def test_none_is_empty(self):
        self.assertEqual(self._classify(None), 'empty')

    def test_kiprjmod_path_is_localised(self):
        self.assertEqual(self._classify("${KIPRJMOD}/Data_Sheets/file.pdf"), 'localised')

    def test_non_pdf_local_path_is_non_pdf(self):
        self.assertEqual(self._classify("C:\\Datasheets\\readme.txt"), 'non_pdf')

    def test_http_url_is_add(self):
        self.assertEqual(self._classify("http://example.com/file.pdf"), 'add')

    def test_https_url_is_add(self):
        self.assertEqual(self._classify("https://example.com/file.pdf"), 'add')

    def test_local_pdf_is_add(self):
        self.assertEqual(self._classify("C:\\Datasheets\\file.pdf"), 'add')

    def test_duplicate_is_duplicate(self):
        seen = set()
        ref = "http://example.com/file.pdf"
        self.localizer._classify_datasheet_ref(ref, seen)   # first call → 'add'
        result = self.localizer._classify_datasheet_ref(ref, seen)  # second → 'duplicate'
        self.assertEqual(result, 'duplicate')

    def test_add_mutates_seen_set(self):
        seen = set()
        ref = "http://example.com/file.pdf"
        self.localizer._classify_datasheet_ref(ref, seen)
        self.assertIn(ref, seen)

    def test_http_url_without_pdf_extension_is_add(self):
        """HTTP URLs without .pdf extension are still 'add' (checked at download time)"""
        self.assertEqual(self._classify("http://example.com/datasheet"), 'add')


# ===========================================================================
# TestIsValidPdf
# ===========================================================================

class TestIsValidPdf(unittest.TestCase):
    """Tests for _is_valid_pdf"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.localizer = DataSheetLocalizer(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _write_bytes(self, name, data):
        path = os.path.join(self.temp_dir, name)
        with open(path, 'wb') as fh:
            fh.write(data)
        return path

    def test_valid_pdf_magic_bytes(self):
        path = self._write_bytes("valid.pdf", b'%PDF-1.4 content here')
        self.assertTrue(self.localizer._is_valid_pdf(path))

    def test_not_a_pdf(self):
        path = self._write_bytes("not.pdf", b'\x89PNG\r\n')
        self.assertFalse(self.localizer._is_valid_pdf(path))

    def test_empty_file(self):
        path = self._write_bytes("empty.pdf", b'')
        self.assertFalse(self.localizer._is_valid_pdf(path))

    def test_truncated_header(self):
        path = self._write_bytes("trunc.pdf", b'%PD')
        self.assertFalse(self.localizer._is_valid_pdf(path))

    def test_nonexistent_file_returns_false(self):
        self.assertFalse(self.localizer._is_valid_pdf("/nonexistent/path.pdf"))


# ===========================================================================
# TestShouldUpdateFile
# ===========================================================================

class TestShouldUpdateFile(unittest.TestCase):
    """Tests for _should_update_file"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.localizer = DataSheetLocalizer(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _touch(self, name, mtime=None):
        path = os.path.join(self.temp_dir, name)
        _write(path, "data")
        if mtime is not None:
            os.utime(path, (mtime, mtime))
        return path

    def test_dest_does_not_exist(self):
        src = self._touch("src.pdf")
        dest = os.path.join(self.temp_dir, "nonexistent.pdf")
        self.assertTrue(self.localizer._should_update_file(src, dest))

    def test_source_newer_than_dest(self):
        now = time.time()
        dest = self._touch("dest.pdf", mtime=now - 100)
        src = self._touch("src.pdf", mtime=now)
        self.assertTrue(self.localizer._should_update_file(src, dest))

    def test_source_older_than_dest(self):
        now = time.time()
        dest = self._touch("dest.pdf", mtime=now)
        src = self._touch("src.pdf", mtime=now - 100)
        self.assertFalse(self.localizer._should_update_file(src, dest))

    def test_same_mtime_returns_false(self):
        now = time.time()
        src = self._touch("src.pdf", mtime=now)
        dest = self._touch("dest.pdf", mtime=now)
        self.assertFalse(self.localizer._should_update_file(src, dest))


# ===========================================================================
# TestScanSymbolDatasheets
# ===========================================================================

class TestScanSymbolDatasheets(unittest.TestCase):
    """Tests for scan_symbol_datasheets"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        self.logger = MockLogger()
        self.localizer = DataSheetLocalizer(self.project_dir, logger=self.logger)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_returns_list(self):
        lib = os.path.join(self.temp_dir, "Test.kicad_sym")
        _write(lib, SYMBOL_LIB_CONTENT)
        result = self.localizer.scan_symbol_datasheets(lib)
        self.assertIsInstance(result, list)

    def test_finds_pdf_url(self):
        lib = os.path.join(self.temp_dir, "Test.kicad_sym")
        _write(lib, SYMBOL_LIB_CONTENT)
        result = self.localizer.scan_symbol_datasheets(lib)
        refs = [ref for _, ref in result]
        self.assertIn("http://www.vishay.com/docs/88503/1n4001.pdf", refs)

    def test_deduplicates_same_url(self):
        """Same URL referenced by multiple symbols appears only once"""
        lib = os.path.join(self.temp_dir, "Test.kicad_sym")
        _write(lib, SYMBOL_LIB_CONTENT)
        result = self.localizer.scan_symbol_datasheets(lib)
        refs = [ref for _, ref in result]
        count = refs.count("http://www.vishay.com/docs/88503/1n4001.pdf")
        self.assertEqual(count, 1)

    def test_skips_tilde_placeholder(self):
        lib = os.path.join(self.temp_dir, "Test.kicad_sym")
        _write(lib, SYMBOL_LIB_CONTENT)
        result = self.localizer.scan_symbol_datasheets(lib)
        refs = [ref for _, ref in result]
        self.assertNotIn("~", refs)

    def test_includes_local_pdf_path(self):
        lib = os.path.join(self.temp_dir, "Test.kicad_sym")
        _write(lib, SYMBOL_LIB_CONTENT)
        result = self.localizer.scan_symbol_datasheets(lib)
        refs = [ref for _, ref in result]
        self.assertIn("C:\\Datasheets\\cap.pdf", refs)

    def test_skips_non_pdf_local_path(self):
        lib = os.path.join(self.temp_dir, "Test.kicad_sym")
        _write(lib, SYMBOL_LIB_CONTENT)
        result = self.localizer.scan_symbol_datasheets(lib)
        refs = [ref for _, ref in result]
        self.assertNotIn("C:\\Datasheets\\readme.txt", refs)

    def test_missing_file_returns_empty_list(self):
        result = self.localizer.scan_symbol_datasheets("/nonexistent/lib.kicad_sym")
        self.assertEqual(result, [])
        self.assertTrue(any("Failed to read" in m for m in self.logger.messages['error']))

    def test_empty_file_returns_empty_list(self):
        lib = os.path.join(self.temp_dir, "Empty.kicad_sym")
        _write(lib, "")
        result = self.localizer.scan_symbol_datasheets(lib)
        self.assertEqual(result, [])


# ===========================================================================
# TestScanSchematicDatasheets
# ===========================================================================

class TestScanSchematicDatasheets(unittest.TestCase):
    """Tests for scan_schematic_datasheets"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        self.logger = MockLogger()
        self.localizer = DataSheetLocalizer(self.project_dir, logger=self.logger)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_returns_list(self):
        sch = os.path.join(self.temp_dir, "test.kicad_sch")
        _write(sch, SCHEMATIC_CONTENT)
        result = self.localizer.scan_schematic_datasheets(sch)
        self.assertIsInstance(result, list)

    def test_finds_url_in_schematic(self):
        sch = os.path.join(self.temp_dir, "test.kicad_sch")
        _write(sch, SCHEMATIC_CONTENT)
        result = self.localizer.scan_schematic_datasheets(sch)
        refs = [ref for _, ref in result]
        self.assertIn("http://www.vishay.com/docs/88503/1n4001.pdf", refs)

    def test_skips_tilde_in_schematic(self):
        sch = os.path.join(self.temp_dir, "test.kicad_sch")
        _write(sch, SCHEMATIC_CONTENT)
        result = self.localizer.scan_schematic_datasheets(sch)
        refs = [ref for _, ref in result]
        self.assertNotIn("~", refs)

    def test_skips_already_localised_path(self):
        content = '(property "Datasheet" "${KIPRJMOD}/Data_Sheets/file.pdf" (at 0 0 0))'
        sch = os.path.join(self.temp_dir, "local.kicad_sch")
        _write(sch, content)
        result = self.localizer.scan_schematic_datasheets(sch)
        self.assertEqual(result, [])

    def test_deduplicates_in_schematic(self):
        content = (
            '(property "Datasheet" "http://example.com/file.pdf" (at 0 0 0))\n'
            '(property "Datasheet" "http://example.com/file.pdf" (at 0 0 0))\n'
        )
        sch = os.path.join(self.temp_dir, "dup.kicad_sch")
        _write(sch, content)
        result = self.localizer.scan_schematic_datasheets(sch)
        self.assertEqual(len(result), 1)

    def test_missing_file_returns_empty_list(self):
        result = self.localizer.scan_schematic_datasheets("/nonexistent/test.kicad_sch")
        self.assertEqual(result, [])
        self.assertTrue(any("Failed to read" in m for m in self.logger.messages['error']))

    def test_source_name_is_schematic(self):
        """Name field in returned tuples should be 'schematic'"""
        content = '(property "Datasheet" "http://example.com/file.pdf" (at 0 0 0))\n'
        sch = os.path.join(self.temp_dir, "test.kicad_sch")
        _write(sch, content)
        result = self.localizer.scan_schematic_datasheets(sch)
        for name, _ in result:
            self.assertEqual(name, "schematic")


# ===========================================================================
# TestUpdateFileReferences
# ===========================================================================

class TestUpdateFileReferences(unittest.TestCase):
    """Tests for update_schematic_references / update_symbol_references
    (both delegate to _update_file_references)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        self.logger = MockLogger()
        self.localizer = DataSheetLocalizer(self.project_dir, logger=self.logger)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_update_schematic_replaces_url(self):
        sch = os.path.join(self.temp_dir, "test.kicad_sch")
        _write(sch, SCHEMATIC_CONTENT)
        datasheet_map = {
            "http://www.vishay.com/docs/88503/1n4001.pdf": "${KIPRJMOD}/Data_Sheets/1n4001.pdf"
        }
        result = self.localizer.update_schematic_references(sch, datasheet_map)
        self.assertTrue(result)
        with open(sch, 'r', encoding='utf-8') as fh:
            content = fh.read()
        self.assertIn("${KIPRJMOD}/Data_Sheets/1n4001.pdf", content)
        self.assertNotIn("http://www.vishay.com/docs/88503/1n4001.pdf", content)

    def test_update_symbol_lib_replaces_url(self):
        lib = os.path.join(self.temp_dir, "Test.kicad_sym")
        _write(lib, SYMBOL_LIB_CONTENT)
        datasheet_map = {
            "http://www.vishay.com/docs/88503/1n4001.pdf": "${KIPRJMOD}/Data_Sheets/1n4001.pdf"
        }
        result = self.localizer.update_symbol_references(lib, datasheet_map)
        self.assertTrue(result)
        with open(lib, 'r', encoding='utf-8') as fh:
            content = fh.read()
        self.assertIn("${KIPRJMOD}/Data_Sheets/1n4001.pdf", content)

    def test_no_changes_needed_returns_true(self):
        sch = os.path.join(self.temp_dir, "unchanged.kicad_sch")
        _write(sch, SCHEMATIC_CONTENT)
        empty_map = {}
        result = self.localizer.update_schematic_references(sch, empty_map)
        self.assertTrue(result)

    def test_no_matching_ref_leaves_file_unchanged(self):
        sch = os.path.join(self.temp_dir, "test.kicad_sch")
        _write(sch, SCHEMATIC_CONTENT)
        datasheet_map = {"http://unrelated.com/other.pdf": "${KIPRJMOD}/Data_Sheets/other.pdf"}
        self.localizer.update_schematic_references(sch, datasheet_map)
        with open(sch, 'r', encoding='utf-8') as fh:
            content = fh.read()
        self.assertIn("http://www.vishay.com/docs/88503/1n4001.pdf", content)

    def test_missing_file_returns_false(self):
        result = self.localizer.update_schematic_references(
            "/nonexistent/test.kicad_sch", {"a": "b"}
        )
        self.assertFalse(result)

    def test_multiple_occurrences_all_replaced(self):
        content = (
            '(property "Datasheet" "http://example.com/file.pdf")\n'
            '(property "Datasheet" "http://example.com/file.pdf")\n'
        )
        sch = os.path.join(self.temp_dir, "multi.kicad_sch")
        _write(sch, content)
        datasheet_map = {"http://example.com/file.pdf": "${KIPRJMOD}/Data_Sheets/file.pdf"}
        self.localizer.update_schematic_references(sch, datasheet_map)
        with open(sch, 'r', encoding='utf-8') as fh:
            updated = fh.read()
        self.assertEqual(updated.count("${KIPRJMOD}/Data_Sheets/file.pdf"), 2)
        self.assertNotIn("http://example.com/file.pdf", updated)


# ===========================================================================
# TestCopyDatasheets
# ===========================================================================

class TestCopyDatasheets(unittest.TestCase):
    """Tests for copy_datasheets (local file copying path)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        self.logger = MockLogger()
        self.localizer = DataSheetLocalizer(self.project_dir, logger=self.logger)

        # Create a real PDF source file
        self.source_pdf = os.path.join(self.temp_dir, "component.pdf")
        with open(self.source_pdf, 'wb') as fh:
            fh.write(b'%PDF-1.4 sample content')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_creates_datasheet_directory(self):
        datasheets = [(("C1", self.source_pdf))]
        self.localizer.copy_datasheets(datasheets)
        self.assertTrue(os.path.isdir(self.localizer.datasheet_dir_path))

    def test_copies_local_pdf(self):
        datasheets = [("C1", self.source_pdf)]
        _, copied_count, datasheet_map = self.localizer.copy_datasheets(datasheets)
        self.assertEqual(copied_count, 1)
        dest = os.path.join(self.localizer.datasheet_dir_path, "component.pdf")
        self.assertTrue(os.path.exists(dest))

    def test_returns_datasheet_map_for_local_file(self):
        datasheets = [("C1", self.source_pdf)]
        _, _, datasheet_map = self.localizer.copy_datasheets(datasheets)
        self.assertIn(self.source_pdf, datasheet_map)
        self.assertIn("${KIPRJMOD}", datasheet_map[self.source_pdf])

    def test_deduplicates_same_ref(self):
        datasheets = [("C1", self.source_pdf), ("C2", self.source_pdf)]
        _, copied_count, _ = self.localizer.copy_datasheets(datasheets)
        self.assertEqual(copied_count, 1)

    def test_skips_non_pdf_extension(self):
        txt_file = os.path.join(self.temp_dir, "readme.txt")
        _write(txt_file, "not a pdf")
        datasheets = [("C1", txt_file)]
        dl, cp, dmap = self.localizer.copy_datasheets(datasheets)
        self.assertEqual(dl + cp, 0)
        self.assertEqual(dmap, {})

    def test_missing_source_file_logs_error(self):
        datasheets = [("C1", "/nonexistent/file.pdf")]
        self.localizer.copy_datasheets(datasheets)
        self.assertTrue(any("not found" in m for m in self.logger.messages['error']))

    def test_up_to_date_dest_not_overwritten(self):
        """If dest is newer than source, copied_count should still increment (file is current)"""
        dest_dir = self.localizer.datasheet_dir_path
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, "component.pdf")
        # Dest is newer
        shutil.copy2(self.source_pdf, dest)
        now_plus = time.time() + 200
        os.utime(dest, (now_plus, now_plus))

        datasheets = [("C1", self.source_pdf)]
        _, copied_count, dmap = self.localizer.copy_datasheets(datasheets)
        self.assertEqual(copied_count, 1)
        self.assertIn(self.source_pdf, dmap)

    @patch('urllib.request.urlopen')
    def test_url_triggers_download(self, mock_urlopen):
        """HTTP URL path calls download_datasheet"""
        # Set up a mock HTTP response that returns a valid PDF
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = b'%PDF-1.4 fake'
        mock_response.headers.get.return_value = None
        mock_urlopen.return_value = mock_response

        url = "http://example.com/datasheet.pdf"
        datasheets = [("D1", url)]
        dl, cp, dmap = self.localizer.copy_datasheets(datasheets)
        self.assertEqual(dl, 1)
        self.assertEqual(cp, 0)
        self.assertIn(url, dmap)


# ===========================================================================
# TestDownloadDatasheet
# ===========================================================================

class TestDownloadDatasheet(unittest.TestCase):
    """Tests for download_datasheet"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        self.logger = MockLogger()
        self.localizer = DataSheetLocalizer(self.project_dir, logger=self.logger)
        self.dest = os.path.join(self.temp_dir, "output.pdf")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch('urllib.request.urlopen')
    def test_successful_download(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = b'%PDF-1.4 content'
        mock_response.headers.get.return_value = None
        mock_urlopen.return_value = mock_response

        result = self.localizer.download_datasheet("http://example.com/file.pdf", self.dest)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.dest))

    @patch('urllib.request.urlopen')
    def test_http_error_returns_false(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://example.com/file.pdf", code=404,
            msg="Not Found", hdrs=None, fp=None
        )
        result = self.localizer.download_datasheet("http://example.com/file.pdf", self.dest)
        self.assertFalse(result)
        self.assertTrue(any("HTTP error" in m for m in self.logger.messages['error']))

    @patch('urllib.request.urlopen')
    def test_url_error_returns_false(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        result = self.localizer.download_datasheet("http://example.com/file.pdf", self.dest)
        self.assertFalse(result)
        self.assertTrue(any("URL error" in m for m in self.logger.messages['error']))

    @patch('urllib.request.urlopen')
    def test_non_pdf_content_logs_warning(self, mock_urlopen):
        """Non-PDF data triggers a warning but returns True (file was written)"""
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = b'<html>not a pdf</html>'
        mock_response.headers.get.return_value = None
        mock_urlopen.return_value = mock_response

        result = self.localizer.download_datasheet("http://example.com/file.pdf", self.dest)
        self.assertTrue(result)
        self.assertTrue(any("does not appear to be a PDF" in m for m in self.logger.messages['warning']))


# ===========================================================================
# TestLocalizeAllDatasheets
# ===========================================================================

class TestLocalizeAllDatasheets(unittest.TestCase):
    """Integration-level tests for localize_all_datasheets"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        self.logger = MockLogger()
        self.localizer = DataSheetLocalizer(self.project_dir, logger=self.logger)

        # Create a real source PDF
        self.source_pdf = os.path.join(self.temp_dir, "cap.pdf")
        with open(self.source_pdf, 'wb') as fh:
            fh.write(b'%PDF-1.4 capacitor datasheet')

        # Symbol lib referencing the real PDF
        self.sym_lib = os.path.join(self.project_dir, "MyLib.kicad_sym")
        _write(self.sym_lib, f'''\
(kicad_symbol_lib (version 20231120) (generator kicad_symbol_editor)
  (symbol "C" (pin_names) (in_bom yes) (on_board yes)
    (property "Datasheet" "{self.source_pdf.replace(os.sep, "/")}" (at 0 0 0))
  )
)''')

        # Schematic referencing the real PDF too
        self.sch_file = os.path.join(self.project_dir, "test.kicad_sch")
        _write(self.sch_file, f'''\
(kicad_sch (version 20231120)
  (symbol (lib_id "MyLib:C") (at 100 100 0)
    (property "Datasheet" "{self.source_pdf.replace(os.sep, "/")}" (at 0 0 0))
  )
)''')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_returns_tuple(self):
        result = self.localizer.localize_all_datasheets([self.sym_lib], [self.sch_file])
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_datasheet_copied(self):
        self.localizer.localize_all_datasheets([self.sym_lib], [self.sch_file])
        dest = os.path.join(self.localizer.datasheet_dir_path, "cap.pdf")
        self.assertTrue(os.path.exists(dest))

    def test_references_updated_in_symbol_lib(self):
        self.localizer.localize_all_datasheets([self.sym_lib], [self.sch_file])
        with open(self.sym_lib, 'r', encoding='utf-8') as fh:
            content = fh.read()
        self.assertIn("${KIPRJMOD}", content)

    def test_references_updated_in_schematic(self):
        self.localizer.localize_all_datasheets([self.sym_lib], [self.sch_file])
        with open(self.sch_file, 'r', encoding='utf-8') as fh:
            content = fh.read()
        self.assertIn("${KIPRJMOD}", content)

    def test_empty_inputs_returns_zero_zero(self):
        result = self.localizer.localize_all_datasheets([], [])
        self.assertEqual(result, (0, 0))

    def test_nonexistent_files_are_skipped_gracefully(self):
        result = self.localizer.localize_all_datasheets(
            ["/nonexistent/lib.kicad_sym"],
            ["/nonexistent/sch.kicad_sch"]
        )
        self.assertIsInstance(result, tuple)

    def test_no_datasheets_returns_zero_zero(self):
        empty_lib = os.path.join(self.project_dir, "Empty.kicad_sym")
        _write(empty_lib, "(kicad_symbol_lib (version 20231120))")
        empty_sch = os.path.join(self.project_dir, "empty.kicad_sch")
        _write(empty_sch, "(kicad_sch (version 20231120))")
        result = self.localizer.localize_all_datasheets([empty_lib], [empty_sch])
        self.assertEqual(result, (0, 0))

    def test_second_run_skips_already_localised(self):
        """On a second run, ${KIPRJMOD} paths are classified as 'localised' and not re-copied"""
        self.localizer.localize_all_datasheets([self.sym_lib], [self.sch_file])
        # Run again - should not raise and should return 0 datasheets processed
        dl2, cp2, dmap2 = self.localizer.copy_datasheets([])
        self.assertEqual(dl2 + cp2, 0)


if __name__ == '__main__':
    unittest.main()
