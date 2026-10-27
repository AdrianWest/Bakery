@echo off
REM Bakery KiCad Plugin Uninstaller for Windows
REM Removes the manual installation created by install.bat.
REM Usage: uninstall.bat [/NonInteractive or /Q]
REM Exit codes: 0 = removed or already absent; 1 = removal failed.
setlocal DisableDelayedExpansion

set "NONINTERACTIVE=0"
if /I "%~1"=="/NonInteractive" set "NONINTERACTIVE=1"
if /I "%~1"=="/Q" set "NONINTERACTIVE=1"

REM Keep this version in sync with install.bat.
set "KICAD_VERSION=10.0"

echo ========================================
echo Bakery KiCad Plugin Uninstaller
echo ========================================
echo.
echo Close KiCad before uninstalling Bakery.
echo.

REM Resolve and validate the exact target before removing it with PowerShell.
powershell.exe -NoProfile -Command ^
    "$ErrorActionPreference = 'Stop';" ^
    "try {" ^
    "    if ([string]::IsNullOrWhiteSpace($env:USERPROFILE) -or -not [IO.Path]::IsPathRooted($env:USERPROFILE)) { throw 'USERPROFILE must be an absolute path.' };" ^
    "    $pluginsRoot = [IO.Path]::GetFullPath((Join-Path $env:USERPROFILE ('Documents\KiCad\' + $env:KICAD_VERSION + '\scripting\plugins')));" ^
    "    $target = [IO.Path]::GetFullPath((Join-Path $pluginsRoot 'Bakery'));" ^
    "    if ((Split-Path -Parent $target) -ne $pluginsRoot -or (Split-Path -Leaf $target) -ne 'Bakery') { throw 'Refusing to remove an unexpected path.' };" ^
    "    if (-not (Test-Path -LiteralPath $target)) { Write-Host ('Bakery is already absent: ' + $target); exit 0 };" ^
    "    $item = Get-Item -LiteralPath $target -Force;" ^
    "    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw ('Expected a regular Bakery directory: ' + $target) };" ^
    "    Write-Host ('Removing: ' + $target);" ^
    "    Remove-Item -LiteralPath $target -Recurse -Force;" ^
    "    if (Test-Path -LiteralPath $target) { throw ('Could not remove: ' + $target) };" ^
    "    Write-Host 'Bakery uninstalled successfully. Restart KiCad to refresh the plugins.';" ^
    "    exit 0;" ^
    "} catch { Write-Host ('ERROR: ' + $_.Exception.Message); exit 1 }"

set "UNINSTALL_RESULT=%ERRORLEVEL%"
echo.
if "%NONINTERACTIVE%"=="0" pause
exit /b %UNINSTALL_RESULT%
