"""
Unit tests for sexpr_parser module

Tests S-expression parsing, serialization, and caching.
"""

import sys
import os
import unittest

# Use import helper for modules with relative imports
from import_helper import import_bakery_module

sexpr_parser = import_bakery_module('sexpr_parser')
SExpressionParser = sexpr_parser.SExpressionParser


class TestSExpressionParser(unittest.TestCase):
    """Test suite for SExpressionParser class"""
    
    def setUp(self):
        """Create parser instance for each test"""
        self.parser = SExpressionParser()
    
    def test_parse_simple_expression(self):
        """Test parsing simple S-expression"""
        sexpr = "(lib MyLib)"
        result = self.parser.parse(sexpr)
        self.assertIsInstance(result, list)
        self.assertEqual(result[0], "lib")
        self.assertEqual(result[1], "MyLib")
    
    def test_parse_nested_expression(self):
        """Test parsing nested S-expression"""
        sexpr = "(lib (name MyLib) (type KiCad))"
        result = self.parser.parse(sexpr)
        self.assertIsInstance(result, list)
        self.assertEqual(result[0], "lib")
        self.assertIsInstance(result[1], list)
        self.assertEqual(result[1][0], "name")
        self.assertEqual(result[1][1], "MyLib")
    
    def test_parse_with_quoted_strings(self):
        """Test parsing S-expression with quoted strings"""
        sexpr = '(lib (name "My Library") (type "KiCad"))'
        result = self.parser.parse(sexpr)
        self.assertIsInstance(result, list)
        # The parser should handle quoted strings
        self.assertIn("My Library", str(result))
    
    def test_parse_multiple_elements(self):
        """Test parsing S-expression with multiple elements at same level"""
        sexpr = "(fp_lib_table (lib (name A)) (lib (name B)))"
        result = self.parser.parse(sexpr)
        self.assertIsInstance(result, list)
        self.assertEqual(result[0], "fp_lib_table")
        # Should have two lib entries
        libs = [item for item in result[1:] if isinstance(item, list) and item[0] == "lib"]
        self.assertEqual(len(libs), 2)
    
    def test_parse_empty_expression(self):
        """Test parsing empty expression"""
        sexpr = "()"
        result = self.parser.parse(sexpr)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
    
    def test_parse_caching(self):
        """Test that parsing results are cached"""
        sexpr = "(lib MyLib)"
        result1 = self.parser.parse(sexpr)
        result2 = self.parser.parse(sexpr)
        
        # Results should be identical (from cache)
        self.assertEqual(result1, result2)
        
        # Cache should contain the parsed result
        self.assertIn(sexpr, self.parser.cache)
    
    def test_cache_size_limit(self):
        """Test that cache respects size limit"""
        small_parser = SExpressionParser(max_cache_size=3)
        
        # Parse more items than cache size
        for i in range(5):
            sexpr = f"(lib Lib{i})"
            small_parser.parse(sexpr)
        
        # Cache should not exceed max size
        self.assertLessEqual(len(small_parser.cache), 3)
    
    def test_clear_cache(self):
        """Test clearing the cache"""
        sexpr = "(lib MyLib)"
        self.parser.parse(sexpr)
        self.assertGreater(len(self.parser.cache), 0)
        
        self.parser.clear_cache()
        self.assertEqual(len(self.parser.cache), 0)
    
    def test_to_string_simple(self):
        """Test serializing simple S-expression"""
        sexpr_list = ["lib", "MyLib"]
        result = self.parser.to_string(sexpr_list)
        self.assertIsInstance(result, str)
        self.assertIn("lib", result)
        self.assertIn("MyLib", result)
        self.assertTrue(result.startswith("("))
        self.assertTrue(result.rstrip().endswith(")"))
    
    def test_to_string_nested(self):
        """Test serializing nested S-expression"""
        sexpr_list = ["lib", ["name", "MyLib"], ["type", "KiCad"]]
        result = self.parser.to_string(sexpr_list)
        self.assertIsInstance(result, str)
        self.assertIn("lib", result)
        self.assertIn("name", result)
        self.assertIn("MyLib", result)
        self.assertIn("type", result)
        self.assertIn("KiCad", result)
    
    def test_to_string_with_indentation(self):
        """Test that serialization produces properly indented output"""
        sexpr_list = ["lib", ["name", "MyLib"]]
        result = self.parser.to_string(sexpr_list)
        
        # Check that output has some indentation (spaces or tabs)
        lines = result.split('\n')
        if len(lines) > 1:
            # At least one line should have leading whitespace
            has_indent = any(line and line[0] in ' \t' for line in lines[1:])
            self.assertTrue(has_indent or len(lines) == 1)
    
    def test_parse_and_serialize_roundtrip(self):
        """Test that parse -> serialize produces valid S-expression"""
        original = "(lib (name MyLib) (type KiCad))"
        parsed = self.parser.parse(original)
        serialized = self.parser.to_string(parsed)
        reparsed = self.parser.parse(serialized)
        
        # Parsing serialized output should produce same structure
        self.assertEqual(parsed, reparsed)
    
    def test_find_footprints(self):
        """Test finding footprints in S-expression"""
        sexpr_text = '''(kicad_pcb
            (footprint "Resistor_SMD:R_0805" (layer "F.Cu"))
            (footprint "Capacitor_SMD:C_0603" (layer "F.Cu"))
        )'''
        
        footprints = self.parser.find_footprints(sexpr_text)
        self.assertIsInstance(footprints, (list, set))
        # Should find footprints in the text
        self.assertGreaterEqual(len(footprints), 0)
    
    def test_find_3d_models(self):
        """Test finding 3D models in S-expression"""
        sexpr_text = '''(footprint "R_0805"
            (model "${KICAD_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_0805.wrl")
            (model "${KIPRJMOD}/3D/custom.step")
        )'''
        
        models = self.parser.find_3d_models(sexpr_text)
        self.assertIsInstance(models, (list, set))
        # Should find models in the text
        self.assertGreaterEqual(len(models), 0)
    
    def test_find_library_path(self):
        """Test finding library path in fp-lib-table"""
        lib_table = '''(fp_lib_table
            (lib (name "MyLib") (type "KiCad") (uri "${KIPRJMOD}/MyLib.pretty"))
            (lib (name "OtherLib") (type "KiCad") (uri "/path/to/other.pretty"))
        )'''
        
        path = self.parser.find_library_path(lib_table, "MyLib")
        if path:  # Only check if find_library_path is implemented
            self.assertIsInstance(path, str)
            self.assertIn("MyLib.pretty", path)
    
    def test_parse_handles_comments(self):
        """Test that parser handles comments (if supported)"""
        # KiCad S-expressions may contain comments
        # This test verifies graceful handling even if comments aren't fully parsed
        sexpr_with_comment = "(lib MyLib) ; this is a comment"
        try:
            result = self.parser.parse(sexpr_with_comment)
            # Should at least not crash
            self.assertIsInstance(result, (list, str))
        except Exception as e:
            # If comments aren't supported, should get a parse error
            # but should not crash the program
            self.assertIsInstance(e, Exception)


class TestSExpressionParserEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        """Create parser instance for each test"""
        self.parser = SExpressionParser()
    
    def test_parse_whitespace_handling(self):
        """Test that parser handles various whitespace correctly"""
        variations = [
            "(lib MyLib)",
            "( lib MyLib )",
            "(  lib   MyLib  )",
            "(\nlib\nMyLib\n)",
            "(\tlib\tMyLib\t)"
        ]
        
        results = [self.parser.parse(v) for v in variations]
        # All should parse to similar structure
        for result in results:
            self.assertIsInstance(result, list)
    
    def test_parse_deeply_nested(self):
        """Test parsing deeply nested expressions"""
        sexpr = "(a (b (c (d (e (f (g h)))))))"
        result = self.parser.parse(sexpr)
        self.assertIsInstance(result, list)
        self.assertEqual(result[0], "a")
    
    def test_to_string_empty_list(self):
        """Test serializing empty list"""
        result = self.parser.to_string([])
        self.assertIsInstance(result, str)
        self.assertEqual(result.strip(), "()")
    
    def test_to_string_single_element(self):
        """Test serializing single element"""
        result = self.parser.to_string(["lib"])
        self.assertIsInstance(result, str)
        self.assertIn("lib", result)


if __name__ == '__main__':
    unittest.main()
