@echo off
REM Bakery KiCad Plugin Installer for Windows
REM Installs the plugin to the KiCad plugins directory
REM
REM Usage:
REM   install.bat                 (interactive; pauses at the end)
REM   install.bat /NonInteractive (INST-04: no pause, script-friendly)
REM
REM Exit codes (INST-05):
REM   0  Every required file and resource was installed successfully.
REM   1  A required source file was missing, or a copy/removal step failed.
setlocal enabledelayedexpansion

set "NONINTERACTIVE=0"
if /I "%~1"=="/NonInteractive" set "NONINTERACTIVE=1"
if /I "%~1"=="/Q" set "NONINTERACTIVE=1"

REM *** Global KiCad version number ***
set KICAD_VERSION=10.0

echo ========================================
echo Bakery KiCad Plugin Installer
echo ========================================
echo.

REM Define the KiCad plugins directory
set KICAD_PLUGINS_DIR=%USERPROFILE%\Documents\KiCad\%KICAD_VERSION%\scripting\plugins\Bakery

REM Check if the plugins directory exists, if not create it
if not exist "%USERPROFILE%\Documents\KiCad\%KICAD_VERSION%\scripting\plugins\" (
    echo Creating KiCad plugins directory...
    mkdir "%USERPROFILE%\Documents\KiCad\%KICAD_VERSION%\scripting\plugins\"
)

REM INST-01: install only from files present in this repository checkout.
set "MISSING=0"
for %%F in (
    __init__.py bakery_plugin.py base_localizer.py backup_manager.py
    footprint_localizer.py symbol_localizer.py data_sheet_localizer.py
    library_manager.py sexpr_parser.py ui_components.py constants.py
    utils.py metadata.json
) do (
    if not exist "%~dp0plugins\%%F" (
        echo ERROR: Required source file missing: "%~dp0plugins\%%F"
        set "MISSING=1"
    )
)
if not exist "%~dp0plugins\resources\" (
    echo ERROR: Required resources folder missing: "%~dp0plugins\resources"
    set "MISSING=1"
)
if not exist "%~dp0LICENSE" (
    echo ERROR: Required LICENSE file missing: "%~dp0LICENSE"
    set "MISSING=1"
)
if "%MISSING%"=="1" (
    echo.
    echo Installation aborted: one or more required source files are missing.
    exit /b 1
)

REM INST-02: remove old installation if it exists.
if exist "%KICAD_PLUGINS_DIR%" (
    echo Removing previous installation...
    rmdir /S /Q "%KICAD_PLUGINS_DIR%"
    if exist "%KICAD_PLUGINS_DIR%" (
        echo ERROR: Could not remove previous installation: "%KICAD_PLUGINS_DIR%"
        exit /b 1
    )
)

REM Create the Bakery plugin directory
echo Installing Bakery plugin...
mkdir "%KICAD_PLUGINS_DIR%"
if not exist "%KICAD_PLUGINS_DIR%\" (
    echo ERROR: Could not create plugin directory: "%KICAD_PLUGINS_DIR%"
    exit /b 1
)

REM INST-03: copy every runtime Python module, metadata.json, LICENSE, and resources.
set "COPY_FAILED=0"
for %%F in (
    __init__.py bakery_plugin.py base_localizer.py backup_manager.py
    footprint_localizer.py symbol_localizer.py data_sheet_localizer.py
    library_manager.py sexpr_parser.py ui_components.py constants.py
    utils.py metadata.json
) do (
    copy /Y "%~dp0plugins\%%F" "%KICAD_PLUGINS_DIR%\" >nul
    if errorlevel 1 (
        echo ERROR: Failed to copy "%%F"
        set "COPY_FAILED=1"
    )
)

REM Copy resources folder
mkdir "%KICAD_PLUGINS_DIR%\resources" >nul 2>nul
xcopy /Y /I /E "%~dp0plugins\resources\*" "%KICAD_PLUGINS_DIR%\resources\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy resources folder
    set "COPY_FAILED=1"
)

copy /Y "%~dp0LICENSE" "%KICAD_PLUGINS_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy LICENSE
    set "COPY_FAILED=1"
)

REM INST-05: return a non-zero exit code if any required copy failed.
if "%COPY_FAILED%"=="1" (
    echo.
    echo ========================================
    echo Installation failed!
    echo ========================================
    echo.
    echo Please check that you have write permissions to:
    echo %USERPROFILE%\Documents\KiCad\%KICAD_VERSION%\scripting\plugins\
    echo.
    exit /b 1
)

echo.
echo ========================================
echo Installation successful!
echo ========================================
echo.
echo Plugin installed to:
echo %KICAD_PLUGINS_DIR%
echo.
echo Please restart KiCad to load the plugin.
echo The plugin will appear under Tools ^> External Plugins ^> Bakery
echo.
if "%NONINTERACTIVE%"=="0" pause
exit /b 0