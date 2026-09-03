"""!
@file __init__.py

@brief Bakery automated functional test suite package.

@section description_main Detailed Description
This package implements the Windows functional test suite described in
`Functional Test/test_spec.md`. It restores the four immutable fixtures,
installs the current Bakery source into KiCad 10, drives the KiCad UI to
exercise the plugin end-to-end, verifies the resulting project files, and
writes machine-readable results.

@section notes_main Notes
- All modules target Windows and KiCad 10 only, matching Bakery's supported
  platform.
- The suite never modifies anything below `Functional Test`; it only reads
  from there and writes to the `C:\\GIT_HUB\\testing` workspace.
"""

__version__ = "1.0.0"
