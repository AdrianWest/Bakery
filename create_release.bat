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
mkdir "%RELEASE_DIR%\plugins\resources"

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
    copy "resources\Bakery_Icon.png" "%RELEASE_DIR%\plugins\resources\" > nul
) else (
    echo WARNING: resources\Bakery_Icon.png not found!
)

if exist "resources\Bakery_Icon_256x256.png" (
    copy "resources\Bakery_Icon_256x256.png" "%RELEASE_DIR%\plugins\resources\" > nul
) else (
    echo WARNING: resources\Bakery_Icon_256x256.png not found!
)

echo Copying root files...
copy "metadata.json" "%RELEASE_DIR%\" > nul

echo.
echo Removing download fields from plugins/metadata.json (cannot be in package)...
powershell -NoProfile -Command "$json = Get-Content '%RELEASE_DIR%\plugins\metadata.json' -Raw | ConvertFrom-Json; $json.versions[0].PSObject.Properties.Remove('download_sha256'); $json.versions[0].PSObject.Properties.Remove('download_size'); $json.versions[0].PSObject.Properties.Remove('install_size'); $json.versions[0].PSObject.Properties.Remove('download_url'); $json | ConvertTo-Json -Depth 10 | Set-Content '%RELEASE_DIR%\plugins\metadata.json' -Encoding UTF8"

echo Removing UTF-8 BOM from metadata.json files...
powershell -NoProfile -Command "$content = Get-Content '%RELEASE_DIR%\metadata.json' -Raw; [System.IO.File]::WriteAllText('%RELEASE_DIR%\metadata.json', $content, (New-Object System.Text.UTF8Encoding $false))"
powershell -NoProfile -Command "$content = Get-Content '%RELEASE_DIR%\plugins\metadata.json' -Raw; [System.IO.File]::WriteAllText('%RELEASE_DIR%\plugins\metadata.json', $content, (New-Object System.Text.UTF8Encoding $false))"

echo.
echo Creating ZIP archive...
powershell -Command "Compress-Archive -Path '%RELEASE_DIR%\*' -DestinationPath '%ZIP_FILE%' -Force"

if not exist "%ZIP_FILE%" (
    echo ERROR: Failed to create ZIP file!
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo Calculating metadata for metadata.json...
echo ============================================================================
echo.

REM Calculate ZIP file size
for %%A in ("%ZIP_FILE%") do set ZIP_SIZE=%%~zA
echo ZIP file size: %ZIP_SIZE% bytes

REM Calculate installed size using PowerShell (before deleting the folder!)
for /f %%i in ('powershell -Command "(Get-ChildItem -Recurse '%RELEASE_DIR%' | Measure-Object -Property Length -Sum).Sum"') do set INSTALL_SIZE=%%i
echo Installed size: %INSTALL_SIZE% bytes

echo Cleaning up release directory...
rmdir /s /q "%RELEASE_DIR%"

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
echo Updating metadata.json files...
echo ============================================================================
echo.

REM Create a temporary PowerShell script to update root metadata.json
echo $json = Get-Content 'metadata.json' -Raw ^| ConvertFrom-Json > update_metadata.ps1
echo $json.versions[0].version = '%VERSION%' >> update_metadata.ps1
echo $json.versions[0].download_url = 'https://github.com/AdrianWest/Bakery/releases/download/v%VERSION%/%ZIP_FILE%' >> update_metadata.ps1
echo $json.versions[0].download_sha256 = '%SHA256%' >> update_metadata.ps1
echo $json.versions[0].download_size = [int]%ZIP_SIZE% >> update_metadata.ps1
echo $json.versions[0].install_size = [int]%INSTALL_SIZE% >> update_metadata.ps1
echo $json.versions[0].status = 'stable' >> update_metadata.ps1
echo $json ^| ConvertTo-Json -Depth 10 ^| Set-Content 'metadata.json' -Encoding UTF8 >> update_metadata.ps1
echo. >> update_metadata.ps1
echo # Update plugins/metadata.json with version and status only (no download fields) >> update_metadata.ps1
echo $json = Get-Content 'plugins\metadata.json' -Raw ^| ConvertFrom-Json >> update_metadata.ps1
echo $json.versions[0].version = '%VERSION%' >> update_metadata.ps1
echo $json.versions[0].status = 'stable' >> update_metadata.ps1
echo $json ^| ConvertTo-Json -Depth 10 ^| Set-Content 'plugins\metadata.json' -Encoding UTF8 >> update_metadata.ps1

REM Execute the PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File update_metadata.ps1

if %ERRORLEVEL% EQU 0 (
    echo Root and plugins metadata.json updated successfully!
    del update_metadata.ps1
) else (
    echo WARNING: Failed to update metadata.json
    if exist update_metadata.ps1 del update_metadata.ps1
)

echo.
echo Removing UTF-8 BOM from repository metadata.json files...
powershell -NoProfile -Command "$content = Get-Content 'metadata.json' -Raw; [System.IO.File]::WriteAllText('metadata.json', $content, (New-Object System.Text.UTF8Encoding $false))"
powershell -NoProfile -Command "$content = Get-Content 'plugins\metadata.json' -Raw; [System.IO.File]::WriteAllText('plugins\metadata.json', $content, (New-Object System.Text.UTF8Encoding $false))"
echo Repository metadata.json files cleaned successfully!

echo   - download_sha256: %SHA256%
echo   - download_size: %ZIP_SIZE%
echo   - install_size: %INSTALL_SIZE%
echo   - status: stable

echo.
echo ============================================================================
echo Release Package Created Successfully!
echo ============================================================================
echo.
echo Package: %ZIP_FILE%
echo.
echo Next steps:
echo 1. Create GitHub release and upload %ZIP_FILE%
echo 2. Verify download_url in metadata.json is correct
echo 3. Commit and push updated metadata.json
echo 4. Submit to KiCad PCM repository
echo.
echo See PCM_RELEASE_CHECKLIST.md for complete release process.
echo.
echo ============================================================================

pause
