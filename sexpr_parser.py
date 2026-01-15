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
@file sexpr_parser.py

@brief S-expression parser for KiCad file formats

This module provides parsing and serialization of S-expressions used in KiCad files.
Supports:
- Parsing S-expression text into nested Python structures
- Formatting S-expressions back to text with proper indentation
- Caching for performance optimization
- Special formatting for KiCad-specific structures (symbols, libraries, etc.)

@section description_sexpr_parser Detailed Description
The SExpressionParser class provides efficient parsing and serialization of
KiCad's S-expression file format. It includes a caching mechanism to improve
performance when parsing the same content multiple times, and special formatters
for symbol libraries and symbol definitions to maintain KiCad's expected formatting.

@section notes_sexpr_parser Notes
- Uses LRU cache for parsed results to improve performance
- Handles nested parentheses and quoted strings correctly
- Preserves KiCad formatting conventions for symbols and libraries
"""

from typing import List, Union, Any, Optional
from collections import OrderedDict
from .constants import (
    SEXPR_FP_LIB_TABLE, SEXPR_LIB, SEXPR_LIB_SYMBOLS, SEXPR_SYMBOL,
    SEXPR_PROPERTY, SEXPR_FOOTPRINT, SEXPR_MODEL, SEXPR_NAME, SEXPR_URI
)

# Maximum cache size to prevent unbounded memory growth
MAX_CACHE_SIZE = 100


class SExpressionParser:
    """!
    @brief Parser for KiCad S-expression format
    
    Provides methods to parse S-expression text into nested Python structures
    and format them back to text with proper indentation.
    
    @section methods Methods
    - :py:meth:`~SExpressionParser.__init__`
    - :py:meth:`~SExpressionParser.parse`
    - :py:meth:`~SExpressionParser.to_string`
    - :py:meth:`~SExpressionParser.find_footprints`
    - :py:meth:`~SExpressionParser.find_3d_models`
    - :py:meth:`~SExpressionParser.find_library_path`
    - :py:meth:`~SExpressionParser.clear_cache`
    - :py:meth:`~SExpressionParser._format_symbol_lib`
    - :py:meth:`~SExpressionParser._format_symbol`
    
    @section attributes Attributes
    - cache (dict): Cache of parsed S-expressions for performance
    - max_cache_size (int): Maximum number of cached parse results
    """
    
    def __init__(self, max_cache_size: int = MAX_CACHE_SIZE):
        """
        @brief Initialize the parser with an empty cache
        
        @param max_cache_size: Maximum number of cached parse results
        """
        self.cache = OrderedDict()
        self.max_cache_size = max_cache_size
    
    def parse(self, text: str) -> Union[List, str]:
        """
        @brief Parse S-expression text into nested Python structures
        
        @param text: S-expression text string
        @return Nested list/string structure representing the S-expression
        
        @note Caches parsed results for performance using LRU eviction
        """
        text = text.strip()
        
        # Check cache (LRU - move to end if found)
        if text in self.cache:
            self.cache.move_to_end(text)
            return self.cache[text]
        
        # Evict oldest if cache is full (proper LRU)
        if len(self.cache) >= self.max_cache_size:
            self.cache.popitem(last=False)
        
        stack = [[]]
        i = 0
        current_token = ""
        in_string = False
        escape_next = False
        
        while i < len(text):
            char = text[i]
            
            # Handle escape sequences
            if escape_next:
                current_token += char
                escape_next = False
                i += 1
                continue
            
            if char == '\\' and in_string:
                current_token += char
                escape_next = True
                i += 1
                continue
            
            char = text[i]
            
            if char == '"' and (i == 0 or text[i-1] != '\\'):
                in_string = not in_string
                current_token += char
            elif in_string:
                current_token += char
            elif char == '(':
                if current_token:
                    stack[-1].append(current_token.strip())
                    current_token = ""
                stack.append([])
            elif char == ')':
                if current_token:
                    stack[-1].append(current_token.strip())
                    current_token = ""
                completed = stack.pop()
                stack[-1].append(completed)
            elif char in ' \t\n\r':
                if current_token:
                    stack[-1].append(current_token.strip())
                    current_token = ""
            else:
                current_token += char
            
            i += 1
        
        result = stack[0][0] if stack[0] else []
        
        # Cache result
        self.cache[text] = result
        
        return result
    
    def to_string(self, sexpr: Union[List, str], indent: int = 0) -> str:
        """
        @brief Convert S-expression back to formatted string
        
        @param sexpr: S-expression (nested lists)
        @param indent: Current indentation level
        @return Formatted S-expression string
        """
        if isinstance(sexpr, str):
            return sexpr
        elif isinstance(sexpr, list):
            if len(sexpr) == 0:
                return "()"
            
            # Special formatting for top-level tables
            if sexpr[0] == SEXPR_FP_LIB_TABLE:
                parts = [f'({SEXPR_FP_LIB_TABLE}']
                for item in sexpr[1:]:
                    if isinstance(item, list):
                        parts.append('\n  ' + self.to_string(item, indent + 2))
                parts.append('\n)')
                return ''.join(parts)
            
            # Special formatting for lib entries
            elif sexpr[0] == SEXPR_LIB:
                parts = [f'({SEXPR_LIB}']
                for item in sexpr[1:]:
                    parts.append(self.to_string(item, indent))
                parts.append(')')
                return ''.join(parts)
            
            # Special formatting for symbol library files
            elif sexpr[0] == SEXPR_LIB_SYMBOLS:
                return self._format_symbol_lib(sexpr, indent)
            
            # Special formatting for symbol definitions
            elif sexpr[0] == SEXPR_SYMBOL:
                return self._format_symbol(sexpr, indent)
            
            # Other lists - compact format
            else:
                parts = ['(']
                for i, item in enumerate(sexpr):
                    if i > 0:
                        parts.append(' ')
                    parts.append(self.to_string(item, indent))
                parts.append(')')
                return ''.join(parts)
        else:
            return str(sexpr)
    
    def find_footprints(self, sexpr: Union[List, str]) -> set:
        """
        @brief Recursively find all footprint references in S-expression
        
        @param sexpr: Parsed S-expression (nested lists)
        @return Set of (library, footprint) tuples
        """
        footprints = set()
        
        def search(node):
            if isinstance(node, list):
                # Look for (property "Footprint" "Library:Footprint")
                if len(node) >= 3 and node[0] == SEXPR_PROPERTY:
                    if len(node) > 1 and node[1].strip('"') == SEXPR_FOOTPRINT:
                        if len(node) > 2:
                            fp_value = node[2].strip('"')
                            if ':' in fp_value:
                                lib, fp = fp_value.split(':', 1)
                                if lib.strip() and fp.strip():
                                    footprints.add((lib.strip(), fp.strip()))
                
                # Recurse into all sub-lists
                for item in node:
                    search(item)
        
        search(sexpr)
        return footprints
    
    def find_3d_models(self, sexpr: Union[List, str]) -> List[str]:
        """
        @brief Extract 3D model references from S-expression
        
        @param sexpr: Parsed S-expression (nested lists)
        @return List of 3D model paths referenced
        """
        models = []
        
        def search_models(node):
            if isinstance(node, list) and len(node) > 0:
                if node[0] == SEXPR_MODEL:
                    # Found a model entry, extract the path
                    # Format: (model "path/to/model.step" ...)
                    if len(node) > 1:
                        model_path = node[1].strip('"')
                        models.append(model_path)
                
                # Recurse into sub-lists
                for item in node:
                    if isinstance(item, list):
                        search_models(item)
        
        search_models(sexpr)
        return models
    
    def find_library_path(self, sexpr: Union[List, str], lib_name: str) -> Union[str, None]:
        """
        @brief Find library URI in fp-lib-table S-expression
        
        @param sexpr: Parsed fp-lib-table S-expression
        @param lib_name: Library nickname to search for
        @return Library URI string or None if not found
        """
        def search_lib(node):
            if isinstance(node, list) and len(node) > 0:
                if node[0] == SEXPR_LIB:
                    # Found a library entry, check if it's the one we want
                    lib_entry_name = None
                    lib_entry_uri = None
                    
                    for item in node:
                        if isinstance(item, list) and len(item) >= 2:
                            if item[0] == SEXPR_NAME:
                                lib_entry_name = item[1].strip('"')
                            elif item[0] == SEXPR_URI:
                                lib_entry_uri = item[1].strip('"')
                    
                    if lib_entry_name == lib_name and lib_entry_uri:
                        return lib_entry_uri
                
                # Recurse into sub-lists
                for item in node:
                    if isinstance(item, list):
                        result = search_lib(item)
                        if result:
                            return result
            
            return None
        
        return search_lib(sexpr)
    
    def clear_cache(self):
        """
        @brief Clear the parse cache
        
        Useful when memory usage is a concern or when files have been modified.
        """
        self.cache.clear()
    
    def _format_symbol_lib(self, sexpr: list, indent: int = 0) -> str:
        """
        @brief Format kicad_symbol_lib with proper indentation
        
        @param sexpr: Symbol library S-expression
        @param indent: Current indentation level
        @return Formatted string with tabs and newlines
        """
        tabs = '\t' * indent
        result = [f'({sexpr[0]}']
        
        for item in sexpr[1:]:
            if isinstance(item, list):
                # Nested elements go on new lines with indentation
                result.append('\n' + tabs + '\t' + self._format_symbol(item, indent + 1))
            else:
                # Simple values stay on same line
                result.append('\n' + tabs + '\t' + '(' + item + ')')
        
        result.append('\n' + tabs + ')')
        return ''.join(result)
    
    def _format_symbol(self, sexpr: list, indent: int = 0) -> str:
        """
        @brief Format symbol definitions with proper indentation
        
        @param sexpr: Symbol S-expression
        @param indent: Current indentation level
        @return Formatted string with tabs and newlines
        """
        if not isinstance(sexpr, list) or len(sexpr) == 0:
            return str(sexpr)
        
        tabs = '\t' * indent
        keyword = sexpr[0]
        
        # Keywords that should have their content on the same line
        inline_keywords = {'version', 'generator', 'generator_version', 'hide', 'offset', 
                          'exclude_from_sim', 'in_bom', 'on_board', 'at', 'size', 'justify',
                          'width', 'type', 'length', 'number', 'embedded_fonts',
                          'power', 'xy', 'start', 'mid', 'end',
                          'radius', 'center'}
        
        # Simple inline format for certain keywords
        if keyword in inline_keywords or (isinstance(sexpr, list) and len(sexpr) == 2 and not isinstance(sexpr[1], list)):
            parts = ['(' + str(sexpr[0])]
            for item in sexpr[1:]:
                if isinstance(item, list):
                    parts.append(' ' + self._format_symbol(item, 0))
                else:
                    parts.append(' ' + str(item))
            parts.append(')')
            return ''.join(parts)
        
        # Special handling for pts - keep all xy elements on same line
        if keyword == 'pts':
            parts = ['(pts']
            for item in sexpr[1:]:
                if isinstance(item, list):
                    parts.append(' ' + self._format_symbol(item, 0))
                else:
                    parts.append(' ' + str(item))
            parts.append(')')
            return ''.join(parts)
        
        # Special handling for symbol keyword - name stays on same line
        if keyword == 'symbol' and len(sexpr) > 1 and not isinstance(sexpr[1], list):
            result = ['(symbol ' + str(sexpr[1])]
            for item in sexpr[2:]:
                if isinstance(item, list):
                    result.append('\n' + tabs + '\t' + self._format_symbol(item, indent + 1))
                else:
                    result.append('\n' + tabs + '\t' + str(item))
            result.append('\n' + tabs + ')')
            return ''.join(result)
        
        # Special handling for pin_names and pin_numbers with nested content
        if keyword in {'pin_names', 'pin_numbers'}:
            if len(sexpr) == 1:
                return '(' + keyword + ')'
            # Check if all children are simple
            has_complex = any(isinstance(item, list) and len(item) > 2 for item in sexpr[1:])
            if not has_complex:
                # Keep it compact
                result = ['(' + keyword]
                for item in sexpr[1:]:
                    if isinstance(item, list):
                        result.append('\n' + tabs + '\t' + self._format_symbol(item, 0))
                    else:
                        result.append('\n' + tabs + '\t' + str(item))
                result.append('\n' + tabs + ')')
                return ''.join(result)
        
        # Multi-line format for complex structures
        result = ['(' + keyword]
        
        for item in sexpr[1:]:
            if isinstance(item, list):
                # Check if it's a simple list that can stay inline
                if len(item) <= 3 and all(not isinstance(x, list) for x in item):
                    result.append('\n' + tabs + '\t' + self._format_symbol(item, 0))
                else:
                    result.append('\n' + tabs + '\t' + self._format_symbol(item, indent + 1))
            else:
                # String values - check if they should be on same line
                if keyword in {'property', 'pin', 'name'}:
                    result.append(' ' + str(item))
                else:
                    result.append('\n' + tabs + '\t' + str(item))
        
        result.append('\n' + tabs + ')')
        return ''.join(result)
