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

"""
@brief User interface components for Bakery plugin

Provides wxPython-based UI components:
- ConfigDialog: Configuration dialog for plugin settings
- BakeryLogger: Progress window with logging and status display
"""

from typing import Dict, Any

try:
    import wx
    WX_AVAILABLE = True
except ImportError:
    # Only available when running inside KiCad
    WX_AVAILABLE = False
    # Create dummy base classes
    class wx:
        Dialog = object
        Frame = object
        OK = 1
        CANCEL = 0
        ID_OK = 1

from .constants import (
    CONFIG_DIALOG_SIZE, CONFIG_LOCAL_LIB_NAME, CONFIG_SYMBOL_LIB_NAME,
    CONFIG_SYMBOL_DIR_NAME, CONFIG_MODELS_DIR_NAME, CONFIG_CREATE_BACKUPS,
    DEFAULT_LOCAL_LIB_NAME, DEFAULT_SYMBOL_LIB_NAME, DEFAULT_SYMBOL_DIR_NAME,
    DEFAULT_MODELS_DIR_NAME, LOGGER_WINDOW_SIZE, LOG_FONT_SIZE,
    COLOR_WARNING_BG, COLOR_ERROR_BG
)
from .utils import validate_library_name


class ConfigDialog(wx.Dialog):
    """
    @brief Configuration dialog for Bakery plugin settings
    
    Allows users to customize library names and backup options.
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
        
        # Footprint library name setting
        lib_label = wx.StaticText(self, label="Local Footprint Library Name:")
        main_sizer.Add(lib_label, 0, wx.ALL, 5)
        
        self.lib_name_ctrl = wx.TextCtrl(
            self, 
            value=config.get(CONFIG_LOCAL_LIB_NAME, DEFAULT_LOCAL_LIB_NAME)
        )
        main_sizer.Add(self.lib_name_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        # Symbol library name setting
        sym_lib_label = wx.StaticText(self, label="Symbol Library Name:")
        main_sizer.Add(sym_lib_label, 0, wx.ALL, 5)
        
        self.sym_lib_name_ctrl = wx.TextCtrl(
            self, 
            value=config.get(CONFIG_SYMBOL_LIB_NAME, DEFAULT_SYMBOL_LIB_NAME)
        )
        main_sizer.Add(self.sym_lib_name_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        # Symbol directory name setting
        sym_dir_label = wx.StaticText(self, label="Symbol Directory Name:")
        main_sizer.Add(sym_dir_label, 0, wx.ALL, 5)
        
        self.sym_dir_ctrl = wx.TextCtrl(
            self, 
            value=config.get(CONFIG_SYMBOL_DIR_NAME, DEFAULT_SYMBOL_DIR_NAME)
        )
        main_sizer.Add(self.sym_dir_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        # Models directory name setting
        models_label = wx.StaticText(self, label="3D Models Directory Name:")
        main_sizer.Add(models_label, 0, wx.ALL, 5)
        
        self.models_dir_ctrl = wx.TextCtrl(
            self, 
            value=config.get(CONFIG_MODELS_DIR_NAME, DEFAULT_MODELS_DIR_NAME)
        )
        main_sizer.Add(self.models_dir_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        # Backup option
        self.backup_checkbox = wx.CheckBox(self, label="Create backups before modifying files")
        self.backup_checkbox.SetValue(config.get(CONFIG_CREATE_BACKUPS, True))
        main_sizer.Add(self.backup_checkbox, 0, wx.ALL, 5)
        
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
    
    def on_ok(self, event):
        """
        @brief Handle OK button click
        
        @param event: Button click event
        """
        # Validate inputs
        lib_name = self.lib_name_ctrl.GetValue().strip()
        sym_lib_name = self.sym_lib_name_ctrl.GetValue().strip()
        sym_dir = self.sym_dir_ctrl.GetValue().strip()
        models_dir = self.models_dir_ctrl.GetValue().strip()
        
        if not validate_library_name(lib_name):
            wx.MessageBox(
                "Footprint library name is empty or contains invalid characters",
                "Validation Error",
                wx.OK | wx.ICON_ERROR
            )
            return
        
        if not validate_library_name(sym_lib_name):
            wx.MessageBox(
                "Symbol library name is empty or contains invalid characters",
                "Validation Error",
                wx.OK | wx.ICON_ERROR
            )
            return
        
        if not validate_library_name(sym_dir):
            wx.MessageBox(
                "Symbol directory name is empty or contains invalid characters",
                "Validation Error",
                wx.OK | wx.ICON_ERROR
            )
            return
        
        if not models_dir.strip():
            wx.MessageBox(
                "3D models directory name cannot be empty",
                "Validation Error",
                wx.OK | wx.ICON_ERROR
            )
            return
            wx.MessageBox(
                "3D Models directory name cannot be empty",
                "Validation Error",
                wx.OK | wx.ICON_ERROR
            )
            return
        
        # Update config
        self.config[CONFIG_LOCAL_LIB_NAME] = lib_name
        self.config[CONFIG_SYMBOL_LIB_NAME] = sym_lib_name
        self.config[CONFIG_SYMBOL_DIR_NAME] = sym_dir
        self.config[CONFIG_MODELS_DIR_NAME] = models_dir
        self.config[CONFIG_CREATE_BACKUPS] = self.backup_checkbox.GetValue()
        
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
    """
    @brief A logging window with progress bar for displaying progress during localization
    
    Provides a real-time log display with separate warning/error sections and progress tracking.
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
        
        # Progress bar
        self.progress_label = wx.StaticText(self, label="Initializing...")
        main_sizer.Add(self.progress_label, 0, wx.ALL, 5)
        
        self.progress_bar = wx.Gauge(self, range=100, style=wx.GA_HORIZONTAL)
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
    
    def set_progress(self, value: int, maximum: int = 100, message: str = ""):
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
