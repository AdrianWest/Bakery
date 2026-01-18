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
copy /Y "%~dp0__init__.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0bakery_plugin.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0base_localizer.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0footprint_localizer.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0symbol_localizer.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0library_manager.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0sexpr_parser.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0ui_components.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0backup_manager.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0constants.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0utils.py" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0metadata.json" "%KICAD_PLUGINS_DIR%\"
copy /Y "%~dp0Bakery_Icon.png" "%KICAD_PLUGINS_DIR%\"
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