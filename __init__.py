"""
Bakery - KiCad Plugin for Localizing Symbols and Footprints

This plugin automates the process of copying global library symbols and footprints
into project-local libraries, eliminating external dependencies.
"""

from .bakery_plugin import BakeryPlugin

# Instantiate the plugin - KiCad will automatically register it
BakeryPlugin()
