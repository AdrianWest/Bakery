@echo off
REM Bakery KiCad Plugin Installer for Windows
REM Installs the plugin to the KiCad 9.0 plugins directory

echo ========================================
echo Bakery KiCad Plugin Installer
echo ========================================
echo.

REM Define the KiCad plugins directory
set KICAD_PLUGINS_DIR=%USERPROFILE%\Documents\KiCad\9.0\scripting\plugins\Bakery

REM Check if the plugins directory exists, if not create it
if not exist "%USERPROFILE%\Documents\KiCad\9.0\scripting\plugins\" (
    echo Creating KiCad plugins directory...
    mkdir "%USERPROFILE%\Documents\KiCad\9.0\scripting\plugins\"
)

REM Remove old installation if it exists
if exist "%KICAD_PLUGINS_DIR%" (
    echo Removing previous installation...
    rmdir /S /Q "%KICAD_PLUGINS_DIR%"
)

REM Create the Bakery plugin directory
echo Installing Bakery plugin...
mkdir "%KICAD_PLUGINS_DIR%"

REM Copy only essential plugin files
copy /Y "%~dp0plugins\__init__.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0plugins\bakery_plugin.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0plugins\base_localizer.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0plugins\footprint_localizer.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0plugins\symbol_localizer.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0plugins\data_sheet_localizer.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0plugins\library_manager.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0plugins\sexpr_parser.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0plugins\ui_components.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0plugins\backup_manager.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0plugins\constants.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0plugins\utils.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0plugins\metadata.json" "%KICAD_PLUGINS_DIR%\"

REM Copy resources folder
mkdir "%KICAD_PLUGINS_DIR%\resources"
xcopy /Y /I "%~dp0plugins\resources\*" "%KICAD_PLUGINS_DIR%\resources\"

copy /Y "%~dp0LICENSE" "%KICAD_PLUGINS_DIR%\"

REM Check if installation was successful
if %ERRORLEVEL% EQU 0 (
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
) else (
    echo.
    echo ========================================
    echo Installation failed!
    echo ========================================
    echo.
    echo Please check that you have write permissions to:
    echo %USERPROFILE%\Documents\KiCad\9.0\scripting\plugins\
    echo.
)
pause