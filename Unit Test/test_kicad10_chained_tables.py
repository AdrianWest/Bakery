"""
Unit tests for KiCad 10 chained library table support.

KiCad 10 introduced a new library-table entry of (type "Table") whose uri points
to another fp-lib-table / sym-lib-table that must also be loaded and searched.
These tests verify that:
  - SExpressionParser.find_library_path ignores chained "Table" entries
  - SExpressionParser.find_table_chains returns the referenced table URIs
  - utils.resolve_library_uri follows chains (recursively, with cycle protection)
    while remaining fully compatible with classic flat KiCad 8/9 tables.
"""

import os
import sys
import shutil
import tempfile
import unittest

from import_helper import import_bakery_module

sexpr_parser = import_bakery_module('sexpr_parser')
utils = import_bakery_module('utils')

SExpressionParser = sexpr_parser.SExpressionParser
resolve_library_uri = utils.resolve_library_uri


# A classic (KiCad 8/9 style) flat table.
FLAT_TABLE = '''(sym_lib_table
    (version 7)
    (lib (name "Device") (type "KiCad") (uri "/opt/kicad/symbols/Device.kicad_sym") (options "") (descr ""))
    (lib (name "MCU") (type "KiCad") (uri "/opt/kicad/symbols/MCU.kicad_sym") (options "") (descr ""))
)'''


class TestParserTableHandling(unittest.TestCase):
    """Parser-level handling of chained Table entries."""

    def setUp(self):
        self.parser = SExpressionParser()

    def test_find_library_path_flat(self):
        """A classic KiCad-type entry resolves directly."""
        sexpr = self.parser.parse(FLAT_TABLE)
        uri = self.parser.find_library_path(sexpr, "Device")
        self.assertEqual(uri, "/opt/kicad/symbols/Device.kicad_sym")

    def test_find_library_path_skips_table_entry(self):
        """A (type "Table") entry must not be returned as a library URI."""
        table = '''(sym_lib_table
            (version 7)
            (lib (name "KiCad") (type "Table") (uri "/opt/kicad/sym-lib-table") (options "") (descr ""))
        )'''
        sexpr = self.parser.parse(table)
        # Even though the nickname matches, a Table entry is not a real library.
        self.assertIsNone(self.parser.find_library_path(sexpr, "KiCad"))

    def test_find_table_chains(self):
        """Chained table URIs are discovered."""
        table = '''(sym_lib_table
            (version 7)
            (lib (name "KiCad") (type "Table") (uri "/opt/kicad/sym-lib-table") (options "") (descr ""))
            (lib (name "Local") (type "KiCad") (uri "${KIPRJMOD}/Local.kicad_sym") (options "") (descr ""))
        )'''
        sexpr = self.parser.parse(table)
        chains = self.parser.find_table_chains(sexpr)
        self.assertEqual(chains, ["/opt/kicad/sym-lib-table"])

    def test_find_table_chains_none(self):
        """A flat table reports no chains."""
        sexpr = self.parser.parse(FLAT_TABLE)
        self.assertEqual(self.parser.find_table_chains(sexpr), [])


class TestResolveLibraryUri(unittest.TestCase):
    """End-to-end nickname resolution through resolve_library_uri."""

    def setUp(self):
        self.parser = SExpressionParser()
        self.temp_dir = tempfile.mkdtemp()
        # No-op path expander (URIs in these tests are already absolute).
        self.expand = lambda p: p

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write(self, name, content):
        path = os.path.join(self.temp_dir, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_resolve_flat_table(self):
        """Classic flat table still resolves (KiCad 8/9 compatibility)."""
        table_path = self._write("sym-lib-table", FLAT_TABLE)
        uri = resolve_library_uri(self.parser, table_path, "Device", self.expand)
        self.assertEqual(uri, "/opt/kicad/symbols/Device.kicad_sym")

    def test_resolve_missing_nickname(self):
        """Unknown nickname returns None."""
        table_path = self._write("sym-lib-table", FLAT_TABLE)
        self.assertIsNone(
            resolve_library_uri(self.parser, table_path, "Nope", self.expand))

    def test_resolve_through_chain(self):
        """A nickname defined only in a chained table is resolved."""
        child = self._write("child-table", '''(sym_lib_table
            (version 7)
            (lib (name "Device") (type "KiCad") (uri "/stock/Device.kicad_sym") (options "") (descr ""))
        )''')
        parent = self._write("sym-lib-table", f'''(sym_lib_table
            (version 7)
            (lib (name "Stock") (type "Table") (uri "{child}") (options "") (descr ""))
        )''')
        uri = resolve_library_uri(self.parser, parent, "Device", self.expand)
        self.assertEqual(uri, "/stock/Device.kicad_sym")

    def test_resolve_chain_cycle_protection(self):
        """Mutually-referencing tables must not cause infinite recursion."""
        a_path = os.path.join(self.temp_dir, "a-table")
        b_path = os.path.join(self.temp_dir, "b-table")
        self._write("a-table", f'''(sym_lib_table
            (lib (name "B") (type "Table") (uri "{b_path}") (options "") (descr ""))
        )''')
        self._write("b-table", f'''(sym_lib_table
            (lib (name "A") (type "Table") (uri "{a_path}") (options "") (descr ""))
        )''')
        # Should terminate and return None rather than hang.
        self.assertIsNone(
            resolve_library_uri(self.parser, a_path, "Device", self.expand))

    def test_direct_entry_preferred_over_chain(self):
        """A nickname present directly is resolved without following chains."""
        child = self._write("child-table", '''(sym_lib_table
            (lib (name "Device") (type "KiCad") (uri "/wrong/Device.kicad_sym") (options "") (descr ""))
        )''')
        parent = self._write("sym-lib-table", f'''(sym_lib_table
            (lib (name "Device") (type "KiCad") (uri "/right/Device.kicad_sym") (options "") (descr ""))
            (lib (name "Stock") (type "Table") (uri "{child}") (options "") (descr ""))
        )''')
        uri = resolve_library_uri(self.parser, parent, "Device", self.expand)
        self.assertEqual(uri, "/right/Device.kicad_sym")


if __name__ == '__main__':
    unittest.main()
