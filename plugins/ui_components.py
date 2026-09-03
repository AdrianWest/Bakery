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
@file ui_components.py

@brief User interface components for Bakery plugin

Provides wxPython-based UI components:
- ConfigDialog: Configuration dialog for plugin settings
- BakeryLogger: Progress window with logging and status display

@section description_ui_components Detailed Description
This module implements the wxPython-based user interface for the Bakery plugin.
ConfigDialog allows users to configure library names and options before running
the localization process. BakeryLogger provides real-time progress updates with
separate panes for info, warning, and error messages.

@section notes_ui_components Notes
- Requires wxPython (bundled with KiCad)
- Gracefully handles missing wx module for development environments
- Logger window supports both modeless (during operation) and modal (at completion) modes
"""

import os
import webbrowser
from typing import Any, Dict

try:
    import wx
    WX_AVAILABLE = True
except ImportError:
    # Only available when running inside KiCad
    WX_AVAILABLE = False
    # Create dummy base classes
    class wx:
        """!
        @brief Minimal wx fallback used when importing outside KiCad.
        """

        Dialog = object
        Frame = object
        OK = 1
        CANCEL = 0
        ID_OK = 1
        ID_CANCEL = 0

from .constants import (
    PLUGIN_VERSION, CONFIG_DIALOG_SIZE, CONFIG_LOCAL_LIB_NAME, CONFIG_SYMBOL_LIB_NAME,
    CONFIG_SYMBOL_DIR_NAME, CONFIG_MODELS_DIR_NAME, CONFIG_DATASHEETS_DIR_NAME,
    DEFAULT_LOCAL_LIB_NAME, DEFAULT_SYMBOL_LIB_NAME,
    DEFAULT_SYMBOL_DIR_NAME, DEFAULT_MODELS_DIR_NAME, DEFAULT_DATASHEETS_DIR_NAME,
    LOGGER_WINDOW_SIZE, LOG_FONT_SIZE, COLOR_WARNING_BG, COLOR_ERROR_BG,
    PROGRESS_BAR_RANGE, CONFIG_BANNER_DISPLAY_WIDTH, CONFIG_BANNER_FILE_NAME,
    LOGGER_BANNER_DISPLAY_WIDTH, LOGGER_BANNER_FILE_NAME,
    COMPLETION_QR_DISPLAY_WIDTH, COMPLETION_QR_FILE_NAME,
    COMPLETION_SUPPORT_MESSAGE, COMPLETION_SUPPORT_URL
)
from .utils import validate_library_name

CONFIG_FIELD_SPECS = (
    (
        "Local Footprint Library Name:",
        "Footprint library name",
        CONFIG_LOCAL_LIB_NAME,
        DEFAULT_LOCAL_LIB_NAME,
        "lib_name_ctrl"
    ),
    (
        "Symbol Library Name:",
        "Symbol library name",
        CONFIG_SYMBOL_LIB_NAME,
        DEFAULT_SYMBOL_LIB_NAME,
        "sym_lib_name_ctrl"
    ),
    (
        "Symbol Directory Name:",
        "Symbol directory name",
        CONFIG_SYMBOL_DIR_NAME,
        DEFAULT_SYMBOL_DIR_NAME,
        "sym_dir_ctrl"
    ),
    (
        "3D Models Directory Name:",
        "3D models directory name",
        CONFIG_MODELS_DIR_NAME,
        DEFAULT_MODELS_DIR_NAME,
        "models_dir_ctrl"
    ),
    (
        "Datasheets Directory Name:",
        "Datasheets directory name",
        CONFIG_DATASHEETS_DIR_NAME,
        DEFAULT_DATASHEETS_DIR_NAME,
        "datasheets_dir_ctrl"
    )
)


def _load_resource_bitmap(file_name: str, display_width: int, description: str):
    """
    @brief Load and scale a PNG image from the plugin resources directory

    @param file_name: Image file name in the plugin resources directory
    @param display_width: Width of the scaled image in pixels
    @param description: Human-readable image description for diagnostics
    @return Scaled wx.Bitmap, or None when the banner cannot be loaded
    """
    image_path = os.path.join(
        os.path.dirname(__file__),
        "resources",
        file_name
    )

    if not os.path.isfile(image_path):
        print(f"Bakery {description} not found: {image_path}")
        return None

    image = wx.Image(image_path, wx.BITMAP_TYPE_PNG)
    if not image.IsOk():
        print(f"Bakery {description} could not be loaded: {image_path}")
        return None

    scaled_height = round(
        image.GetHeight() * display_width / image.GetWidth()
    )
    image = image.Scale(
        display_width,
        scaled_height,
        wx.IMAGE_QUALITY_HIGH
    )
    return wx.Bitmap(image)


def _load_banner_bitmap(file_name: str, display_width: int):
    """
    @brief Load and scale a Bakery banner

    @param file_name: Banner image file name in the plugin resources directory
    @param display_width: Width of the scaled banner in pixels
    @return Scaled wx.Bitmap, or None when the banner cannot be loaded
    """
    return _load_resource_bitmap(file_name, display_width, "banner")


def show_completion_dialog(parent, completion_message: str) -> None:
    """
    @brief Show the localization completion dialog with support QR code

    @param parent: Parent wx window, or None
    @param completion_message: Localization summary text
    """
    dialog = wx.Dialog(parent, title="Bakery - Success", size=(660, 500))
    main_sizer = wx.BoxSizer(wx.VERTICAL)

    title_label = wx.StaticText(dialog, label="Localization Complete!")
    title_font = title_label.GetFont()
    title_font.SetPointSize(round(title_font.GetPointSize() * 1.8))
    title_font.SetWeight(wx.FONTWEIGHT_BOLD)
    title_label.SetFont(title_font)
    main_sizer.Add(title_label, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 18)

    summary_label = wx.StaticText(dialog, label=completion_message)
    summary_font = summary_label.GetFont()
    summary_font.SetPointSize(round(summary_font.GetPointSize() * 1.5))
    summary_label.SetFont(summary_font)
    main_sizer.Add(summary_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 25)

    main_sizer.Add(wx.StaticLine(dialog), 0, wx.EXPAND | wx.ALL, 15)

    support_sizer = wx.BoxSizer(wx.HORIZONTAL)
    qr_bitmap = _load_resource_bitmap(
        COMPLETION_QR_FILE_NAME,
        COMPLETION_QR_DISPLAY_WIDTH,
        "support QR code"
    )
    if qr_bitmap is not None:
        qr_panel = wx.Panel(dialog)
        qr_panel.SetBackgroundColour(wx.Colour(255, 255, 255))
        qr_sizer = wx.BoxSizer(wx.VERTICAL)
        qr_image = wx.StaticBitmap(qr_panel, bitmap=qr_bitmap)
        qr_sizer.Add(qr_image, 0, wx.ALIGN_CENTER | wx.ALL, 12)
        qr_panel.SetSizer(qr_sizer)
        support_sizer.Add(qr_panel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 10)

    support_text_sizer = wx.BoxSizer(wx.VERTICAL)
    support_label = wx.StaticText(dialog, label=COMPLETION_SUPPORT_MESSAGE)
    support_font = support_label.GetFont()
    support_font.SetPointSize(round(support_font.GetPointSize() * 1.5))
    support_label.SetFont(support_font)
    support_label.Wrap(400)
    support_text_sizer.Add(
        support_label,
        0,
        wx.EXPAND | wx.BOTTOM,
        12
    )
    coffee_button = wx.Button(dialog, label="Buy me a coffee")
    coffee_button.Bind(
        wx.EVT_BUTTON,
        lambda event: webbrowser.open(COMPLETION_SUPPORT_URL)
    )
    support_text_sizer.Add(coffee_button, 0, wx.ALIGN_LEFT)
    support_sizer.Add(
        support_text_sizer,
        1,
        wx.ALIGN_CENTER_VERTICAL | wx.ALL,
        10
    )
    main_sizer.Add(support_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 25)

    ok_button = wx.Button(dialog, wx.ID_OK, "OK")
    ok_button.Bind(wx.EVT_BUTTON, lambda event: dialog.EndModal(wx.ID_OK))
    main_sizer.Add(ok_button, 0, wx.ALIGN_CENTER | wx.ALL, 18)

    dialog.SetSizer(main_sizer)
    dialog.Centre()
    try:
        dialog.ShowModal()
    finally:
        dialog.Destroy()


class ConfigDialog(wx.Dialog):
    """!
    @brief Configuration dialog for Bakery plugin settings
    
    Allows users to customize library names and output directory names.
    
    @section methods Methods
    - :py:meth:`~ConfigDialog.__init__`
    - :py:meth:`~ConfigDialog._add_text_setting`
    - :py:meth:`~ConfigDialog.on_ok`
    - :py:meth:`~ConfigDialog.on_cancel`
    - :py:meth:`~ConfigDialog.get_config`
    
    @section attributes Attributes
    - config (dict): Configuration settings dictionary
    """
    
    def __init__(self, parent, config: Dict[str, Any]):
        """
        @brief Initialize the configuration dialog
        
        @param parent: Parent window
        @param config: Current configuration dictionary
        """
        super(ConfigDialog, self).__init__(
            parent, 
            title="Bakery Configuration", 
            size=CONFIG_DIALOG_SIZE
        )
        
        self.config = config.copy()
        
        # Create main sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        banner_bitmap = _load_banner_bitmap(
            CONFIG_BANNER_FILE_NAME,
            CONFIG_BANNER_DISPLAY_WIDTH
        )
        if banner_bitmap is not None:
            banner = wx.StaticBitmap(self, bitmap=banner_bitmap)
            main_sizer.Add(banner, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        # Plugin version
        version_label = wx.StaticText(self, label=f"Bakery v{PLUGIN_VERSION}")
        version_font = version_label.GetFont()
        version_font.SetStyle(wx.FONTSTYLE_ITALIC)
        version_label.SetFont(version_font)
        main_sizer.Add(version_label, 0, wx.ALL, 5)
        
        for label, _, key, default, attribute_name in CONFIG_FIELD_SPECS:
            control = self._add_text_setting(
                main_sizer,
                label,
                config.get(key, default)
            )
            setattr(self, attribute_name, control)
        
        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        ok_btn = wx.Button(self, wx.ID_OK, "OK")
        ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        button_sizer.Add(ok_btn, 0, wx.ALL, 5)
        
        cancel_btn = wx.Button(self, wx.ID_CANCEL, "Cancel")
        cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        button_sizer.Add(cancel_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
        self.Centre()

    def _add_text_setting(self, sizer, label: str, value: str):
        """
        @brief Add a labeled text setting to the configuration dialog

        @param sizer: Parent wx sizer
        @param label: Setting label
        @param value: Initial text value
        @return Created wx.TextCtrl
        """
        setting_label = wx.StaticText(self, label=label)
        sizer.Add(setting_label, 0, wx.ALL, 5)
        control = wx.TextCtrl(self, value=value)
        sizer.Add(
            control,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            5
        )
        return control

    def on_ok(self, event):
        """
        @brief Handle OK button click
        
        @param event: Button click event
        """
        updated_values = {}
        for _, validation_name, key, _, attribute_name in CONFIG_FIELD_SPECS:
            value = getattr(self, attribute_name).GetValue().strip()
            if not validate_library_name(value):
                wx.MessageBox(
                    f"{validation_name} is empty or contains invalid characters",
                    "Validation Error",
                    wx.OK | wx.ICON_ERROR
                )
                return
            updated_values[key] = value

        self.config.update(updated_values)
        
        self.EndModal(wx.ID_OK)
    
    def on_cancel(self, event):
        """
        @brief Handle Cancel button click
        
        @param event: Button click event
        """
        self.EndModal(wx.ID_CANCEL)
    
    def get_config(self) -> Dict[str, Any]:
        """
        @brief Get the updated configuration
        
        @return Configuration dictionary
        """
        return self.config


class BakeryLogger(wx.Dialog):
    """!
    @brief A logging window with progress bar for displaying progress during localization
    
    Provides a real-time log display with separate warning/error sections and progress tracking.
    
    @section methods Methods
    - :py:meth:`~BakeryLogger.__init__`
    - :py:meth:`~BakeryLogger.set_progress`
    - :py:meth:`~BakeryLogger.log`
    - :py:meth:`~BakeryLogger.info`
    - :py:meth:`~BakeryLogger.warning`
    - :py:meth:`~BakeryLogger.error`
    - :py:meth:`~BakeryLogger.success`
    - :py:meth:`~BakeryLogger.enable_close`
    - :py:meth:`~BakeryLogger.on_close`
    
    @section attributes Attributes
    - progress_bar (wx.Gauge): Progress bar control
    - progress_label (wx.StaticText): Progress status label
    - log_text (wx.TextCtrl): Main log text area
    - warning_text (wx.TextCtrl): Warning messages text area
    - error_text (wx.TextCtrl): Error messages text area
    - close_button (wx.Button): Close button control
    """
    
    def __init__(self, parent, title="Bakery - Localization Log"):
        """
        @brief Initialize the logger dialog
        
        @param parent: Parent window (can be None)
        @param title: Dialog window title
        """
        super(BakeryLogger, self).__init__(parent, title=title, size=LOGGER_WINDOW_SIZE)

        # Create main sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        banner_bitmap = _load_banner_bitmap(
            LOGGER_BANNER_FILE_NAME,
            LOGGER_BANNER_DISPLAY_WIDTH
        )
        if banner_bitmap is not None:
            banner = wx.StaticBitmap(self, bitmap=banner_bitmap)
            main_sizer.Add(banner, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        # Progress bar
        self.progress_label = wx.StaticText(self, label="Initializing...")
        main_sizer.Add(self.progress_label, 0, wx.ALL, 5)
        
        self.progress_bar = wx.Gauge(self, range=PROGRESS_BAR_RANGE, style=wx.GA_HORIZONTAL)
        main_sizer.Add(self.progress_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        # Create main log section
        log_label = wx.StaticText(self, label="Log:")
        main_sizer.Add(log_label, 0, wx.ALL, 5)
        
        self.log_text = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        
        # Use monospace font for better readability
        font = wx.Font(
            LOG_FONT_SIZE, 
            wx.FONTFAMILY_TELETYPE, 
            wx.FONTSTYLE_NORMAL, 
            wx.FONTWEIGHT_NORMAL
        )
        self.log_text.SetFont(font)
        
        main_sizer.Add(self.log_text, 3, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        # Create horizontal sizer for warnings and errors
        issues_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Warnings section
        warnings_box = wx.BoxSizer(wx.VERTICAL)
        warnings_label = wx.StaticText(self, label="Warnings:")
        warnings_box.Add(warnings_label, 0, wx.ALL, 5)
        
        self.warnings_text = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self.warnings_text.SetFont(font)
        self.warnings_text.SetBackgroundColour(wx.Colour(*COLOR_WARNING_BG))
        self.warnings_text.SetForegroundColour(wx.Colour(0, 0, 0))
        warnings_box.Add(self.warnings_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        issues_sizer.Add(warnings_box, 1, wx.EXPAND)
        
        # Errors section
        errors_box = wx.BoxSizer(wx.VERTICAL)
        errors_label = wx.StaticText(self, label="Errors:")
        errors_box.Add(errors_label, 0, wx.ALL, 5)
        
        self.errors_text = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self.errors_text.SetFont(font)
        self.errors_text.SetBackgroundColour(wx.Colour(*COLOR_ERROR_BG))
        self.errors_text.SetForegroundColour(wx.Colour(0, 0, 0))
        errors_box.Add(self.errors_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        issues_sizer.Add(errors_box, 1, wx.EXPAND)
        
        main_sizer.Add(issues_sizer, 2, wx.EXPAND | wx.ALL, 0)
        
        # Create close button
        self.close_btn = wx.Button(self, wx.ID_CLOSE, "Close")
        self.close_btn.Enable(False)  # Disabled until process completes
        self.close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        
        main_sizer.Add(self.close_btn, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
        self.Centre()
    
    def set_progress(self, value: int, maximum: int = PROGRESS_BAR_RANGE, message: str = ""):
        """
        @brief Update the progress bar
        
        @param value: Current progress value
        @param maximum: Maximum progress value
        @param message: Optional progress message
        """
        if maximum != self.progress_bar.GetRange():
            self.progress_bar.SetRange(maximum)
        
        self.progress_bar.SetValue(value)
        
        if message:
            self.progress_label.SetLabel(message)
        
        # Update UI
        wx.GetApp().Yield()
    
    def log(self, message: str, level: str = "INFO"):
        """
        @brief Add a log message to the window
        
        @param message: Message text to log
        @param level: Log level (INFO, WARNING, ERROR, SUCCESS)
        """
        timestamp = wx.DateTime.Now().Format("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{level}] {message}\n"
        
        self.log_text.AppendText(formatted_msg)
        self.log_text.SetInsertionPointEnd()
        
        # Process events to update UI immediately
        wx.GetApp().Yield()
    
    def info(self, message: str):
        """
        @brief Log an info message
        
        @param message: Message text
        """
        self.log(message, "INFO")
    
    def warning(self, message: str):
        """
        @brief Log a warning message
        
        @param message: Message text
        """
        self.log(message, "WARNING")
        
        # Also add to warnings text box
        timestamp = wx.DateTime.Now().Format("%H:%M:%S")
        self.warnings_text.AppendText(f"[{timestamp}] {message}\n")
        self.warnings_text.SetInsertionPointEnd()
    
    def error(self, message: str):
        """
        @brief Log an error message
        
        @param message: Message text
        """
        self.log(message, "ERROR")
        
        # Also add to errors text box
        timestamp = wx.DateTime.Now().Format("%H:%M:%S")
        self.errors_text.AppendText(f"[{timestamp}] {message}\n")
        self.errors_text.SetInsertionPointEnd()
    
    def success(self, message: str):
        """
        @brief Log a success message
        
        @param message: Message text
        """
        self.log(message, "SUCCESS")
    
    def enable_close(self):
        """
        @brief Enable the close button when processing is complete
        """
        self.close_btn.Enable(True)
        self.progress_label.SetLabel("Complete")

    def on_close(self, event):
        """
        @brief Handle close button click
        
        @param event: Button click event
        """
        self.EndModal(wx.ID_OK)
