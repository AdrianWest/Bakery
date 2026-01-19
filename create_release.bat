@echo off
REM ============================================================================
REM Bakery KiCad Plugin - Release Package Builder
REM ============================================================================
REM This script creates a release package for KiCad Plugin and Content Manager
REM It will:
REM   1. Create the release directory structure
REM   2. Copy all necessary files
REM   3. Create a ZIP archive
REM   4. Calculate SHA256 hash and file sizes for metadata.json
REM ============================================================================

setlocal enabledelayedexpansion

REM Check if version parameter is provided
if "%~1"=="" (
    echo.
    echo ERROR: Version number required!
    echo.
    echo Usage: create_release.bat VERSION
    echo Example: create_release.bat 1.0.0
    echo.
    pause
    exit /b 1
)

REM Configuration
set VERSION=%~1
set RELEASE_DIR=Bakery-%VERSION%
set ZIP_FILE=%RELEASE_DIR%.zip

echo.
echo ============================================================================
echo Bakery Release Package Builder v%VERSION%
echo ============================================================================
echo.

REM Clean up existing release directory and ZIP
if exist "%RELEASE_DIR%" (
    echo Removing existing release directory...
    rmdir /s /q "%RELEASE_DIR%"
)

if exist "%ZIP_FILE%" (
    echo Removing existing ZIP file...
    del /q "%ZIP_FILE%"
)

echo.
echo Creating release directory structure...
mkdir "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%\plugins"
mkdir "%RELEASE_DIR%\resources"

echo.
echo Copying plugin files...
copy "plugins\__init__.py" "%RELEASE_DIR%\plugins\" > nul
copy "plugins\bakery_plugin.py" "%RELEASE_DIR%\plugins\" > nul
copy "plugins\base_localizer.py" "%RELEASE_DIR%\plugins\" > nul
copy "plugins\constants.py" "%RELEASE_DIR%\plugins\" > nul
copy "plugins\footprint_localizer.py" "%RELEASE_DIR%\plugins\" > nul
copy "plugins\symbol_localizer.py" "%RELEASE_DIR%\plugins\" > nul
copy "plugins\library_manager.py" "%RELEASE_DIR%\plugins\" > nul
copy "plugins\sexpr_parser.py" "%RELEASE_DIR%\plugins\" > nul
copy "plugins\ui_components.py" "%RELEASE_DIR%\plugins\" > nul
copy "plugins\backup_manager.py" "%RELEASE_DIR%\plugins\" > nul
copy "plugins\utils.py" "%RELEASE_DIR%\plugins\" > nul
copy "plugins\metadata.json" "%RELEASE_DIR%\plugins\" > nul

echo Copying resource files...
if exist "resources\Bakery_Icon.png" (
    copy "resources\Bakery_Icon.png" "%RELEASE_DIR%\resources\" > nul
) else (
    echo WARNING: resources\Bakery_Icon.png not found!
)

if exist "resources\Bakery_Icon_256x256.png" (
    copy "resources\Bakery_Icon_256x256.png" "%RELEASE_DIR%\resources\" > nul
) else (
    echo WARNING: resources\Bakery_Icon_256x256.png not found!
)

echo Copying root files...
copy "LICENSE" "%RELEASE_DIR%\" > nul
copy "metadata.json" "%RELEASE_DIR%\" > nul
copy "README.md" "%RELEASE_DIR%\" > nul

echo.
echo Creating ZIP archive...
powershell -Command "Compress-Archive -Path '%RELEASE_DIR%' -DestinationPath '%ZIP_FILE%' -Force"

if not exist "%ZIP_FILE%" (
    echo ERROR: Failed to create ZIP file!
    pause
    exit /b 1
)

echo Cleaning up release directory...
rmdir /s /q "%RELEASE_DIR%"

echo.
echo ============================================================================
echo Calculating metadata for metadata.json...
echo ============================================================================
echo.

REM Calculate ZIP file size
for %%A in ("%ZIP_FILE%") do set ZIP_SIZE=%%~zA
echo ZIP file size: %ZIP_SIZE% bytes

REM Calculate installed size using PowerShell
for /f %%i in ('powershell -Command "(Get-ChildItem -Recurse '%RELEASE_DIR%' | Measure-Object -Property Length -Sum).Sum"') do set INSTALL_SIZE=%%i
echo Installed size: %INSTALL_SIZE% bytes

REM Calculate SHA256 hash
echo.
echo Calculating SHA256 hash (this may take a moment)...
for /f "skip=1 tokens=*" %%i in ('certutil -hashfile "%ZIP_FILE%" SHA256') do (
    set HASH_LINE=%%i
    goto :hash_done
)
:hash_done
REM Remove spaces from hash
set SHA256=%HASH_LINE: =%

echo SHA256 hash: %SHA256%

echo.
echo ============================================================================
echo Updating metadata.json...
echo ============================================================================
echo.

REM Update metadata.json using PowerShell with error handling
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $json = Get-Content 'metadata.json' -Raw | ConvertFrom-Json; $json.versions[0].download_sha256 = '%SHA256%'; $json.versions[0].download_size = [int]%ZIP_SIZE%; $json.versions[0].install_size = [int]%INSTALL_SIZE%; $json.versions[0].status = 'stable'; $json | ConvertTo-Json -Depth 10 | Set-Content 'metadata.json' -Encoding UTF8; exit 0 } catch { Write-Host 'Error:' $_.Exception.Message; exit 1 }"

if %ERRORLEVEL% EQU 0 (
    echo metadata.json updated successfully!
    echo   - download_sha256: %SHA256%
    echo   - download_size: %ZIP_SIZE%
    echo   - install_size: %INSTALL_SIZE%
    echo   - status: stable
) else (
    echo WARNING: Failed to update metadata.json automatically
    echo Please update manually with these values:
    echo   "download_size": %ZIP_SIZE%,
    echo   "download_sha256": "%SHA256%",
    echo   "install_size": %INSTALL_SIZE%,
    echo   "status": "stable"
)

echo.
echo ============================================================================
echo Release Package Created Successfully!
echo ============================================================================
echo.
echo Package: %ZIP_FILE%
echo Directory: %RELEASE_DIR%\
echo.
echo Next steps:
echo 1. Create GitHub release and upload %ZIP_FILE%
echo 2. Update download_url in metadata.json with GitHub release URL:
echo    https://github.com/AdrianWest/Bakery/releases/download/v%VERSION%/%ZIP_FILE%
echo 3. Commit and push updated metadata.json
echo 4. Submit to KiCad PCM repository
echo.
echo See PCM_RELEASE_CHECKLIST.md for complete release process.
echo.
echo ============================================================================

pause
