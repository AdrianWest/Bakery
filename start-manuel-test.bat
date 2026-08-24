@echo off
setlocal

set "SOURCE_DIR=%~dp0Functional Test"
for %%I in ("%~dp0..") do set "DESTINATION_DIR=%%~fI\testing"

if not exist "%SOURCE_DIR%\" (
    echo ERROR: Functional Test folder not found: "%SOURCE_DIR%"
    exit /b 1
)

if not exist "%DESTINATION_DIR%\" (
    mkdir "%DESTINATION_DIR%"
    if errorlevel 1 (
        echo ERROR: Could not create testing folder: "%DESTINATION_DIR%"
        exit /b 1
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$source = '%SOURCE_DIR%'; $destination = '%DESTINATION_DIR%'; " ^
    "$items = Get-ChildItem -LiteralPath $source -Force; " ^
    "$copies = foreach ($item in $items) { " ^
    "  [pscustomobject]@{ Item = $item; Target = Join-Path $destination ($item.Name -replace ' - Backup$', '' -replace ' - BackUp$', '') } " ^
    "}; " ^
    "foreach ($copy in $copies) { " ^
    "  if (Test-Path -LiteralPath $copy.Target) { Remove-Item -LiteralPath $copy.Target -Recurse -Force }; " ^
    "  Copy-Item -LiteralPath $copy.Item.FullName -Destination $copy.Target -Recurse -Force; " ^
    "  Write-Host ('Copied ' + $copy.Item.Name + ' to ' + $copy.Target) " ^
    "}"

if errorlevel 1 (
    echo.
    echo Manual test project setup failed.
    exit /b 1
)

echo.
echo Manual test projects are ready in "%DESTINATION_DIR%".
pause