"""!
@file __init__.py

@brief Bakery - KiCad Plugin for Localizing Symbols and Footprints

This plugin automates the process of copying global library symbols and footprints
into project-local libraries, eliminating external dependencies.

@section description_init Detailed Description
This module serves as the package initializer for the Bakery plugin. It handles
plugin registration with KiCad and sets up logging for debugging purposes.

@section notes_init Notes
- Logging is configured to write to bakery_init.log in the plugin directory
- Plugin registration is deferred to avoid loading issues during KiCad startup
- Import errors are caught and logged for troubleshooting
"""
import logging
import os
from pathlib import Path

# Setup logging to file in the plugin directory
script_dir = Path(__file__).parent # Get the directory where this script is located
log_file = script_dir.joinpath("bakery_init.log")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file), mode='a'),
        logging.StreamHandler()  # Also log to console
    ]
)

logger = logging.getLogger("Bakery")
logger.info("=" * 80)
logger.info("Bakery plugin __init__.py loading")

try:
    import pcbnew
    logger.info("Loading Bakery plugin...")
    from .bakery_plugin import BakeryPlugin
    BakeryPlugin().register()
    logger.info("Bakery plugin registered successfully")
except ImportError:
    pass  # pcbnew not available (running outside KiCad)
except Exception as e:
    logger.exception(f"Fatal error loading Bakery plugin: {e}")
    raise
