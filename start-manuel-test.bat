@echo off
REM Restores clean working copies of the four functional-test fixtures.
REM
REM Usage:
REM   start-manuel-test.bat                 (interactive; pauses at the end)
REM   start-manuel-test.bat /NonInteractive  (SETUP-04: no pause, script-friendly)
REM
REM Exit codes (SETUP-05/SETUP-06):
REM   0  All four fixtures were restored successfully.
REM   1  The Functional Test source folder or the testing workspace could not
REM      be prepared.
REM   2  One or more fixture sources are missing, a destination could not be
REM      replaced, or a copy is incomplete.
setlocal enabledelayedexpansion

set "NONINTERACTIVE=0"
if /I "%~1"=="/NonInteractive" set "NONINTERACTIVE=1"
if /I "%~1"=="/Q" set "NONINTERACTIVE=1"

set "SOURCE_DIR=%~dp0Functional Test"
for %%I in ("%~dp0..") do set "DESTINATION_DIR=%%~fI\testing"

REM SETUP-03: only these four named fixtures are copied as test projects.
REM Markdown files and any other content under "Functional Test" is ignored.
set "FIXTURE1=Ki-Test 01-10 - Backup"
set "FIXTURE2=Ki-Test 01-09 - Backup"
set "FIXTURE3=Ki-Test 02-10 - BackUp"
set "FIXTURE4=Ki-Test 02-09 - BackUp"

if not exist "%SOURCE_DIR%\" (
    echo ERROR: Functional Test folder not found: "%SOURCE_DIR%"
    exit /b 1
)

for %%F in ("%FIXTURE1%" "%FIXTURE2%" "%FIXTURE3%" "%FIXTURE4%") do (
    if not exist "%SOURCE_DIR%\%%~F\" (
        echo ERROR: Required fixture missing: "%SOURCE_DIR%\%%~F"
        exit /b 2
    )
)

if not exist "%DESTINATION_DIR%\" (
    mkdir "%DESTINATION_DIR%"
    if errorlevel 1 (
        echo ERROR: Could not create testing folder: "%DESTINATION_DIR%"
        exit /b 1
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference = 'Stop'; " ^
    "$source = '%SOURCE_DIR%'; $destination = '%DESTINATION_DIR%'; " ^
    "$names = @('%FIXTURE1%', '%FIXTURE2%', '%FIXTURE3%', '%FIXTURE4%'); " ^
    "try { " ^
    "  foreach ($name in $names) { " ^
    "    $sourcePath = Join-Path $source $name; " ^
    "    $targetName = ($name -replace ' - Backup$', '' -replace ' - BackUp$', ''); " ^
    "    $targetPath = Join-Path $destination $targetName; " ^
    "    if (Test-Path -LiteralPath $targetPath) { Remove-Item -LiteralPath $targetPath -Recurse -Force }; " ^
    "    Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Recurse -Force; " ^
    "    $sourceCount = (Get-ChildItem -LiteralPath $sourcePath -Recurse -Force -File).Count; " ^
    "    $targetCount = (Get-ChildItem -LiteralPath $targetPath -Recurse -Force -File).Count; " ^
    "    if ($sourceCount -ne $targetCount) { throw \"Copy incomplete for $name ($targetCount of $sourceCount files)\" }; " ^
    "    Write-Host ('Copied ' + $name + ' to ' + $targetPath + ' (' + $targetCount + ' files)') " ^
    "  } " ^
    "} catch { " ^
    "  Write-Host ('ERROR: ' + $_.Exception.Message); " ^
    "  exit 2 " ^
    "}"

if errorlevel 1 (
    echo.
    echo Manual test project setup failed.
    exit /b 2
)

echo.
echo Manual test projects are ready in "%DESTINATION_DIR%".
if "%NONINTERACTIVE%"=="0" pause
exit /b 0