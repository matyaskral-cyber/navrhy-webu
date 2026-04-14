@echo off
chcp 65001 >nul
echo ========================================
echo   M+P Kral - Aktualizace skladu na webu
echo ========================================
echo.
echo Hledam Excel soubor...
echo.

REM PowerShell skript si najde soubor sam (ve slozce "Export Skladu MP Kral" nebo na plose)
echo Spoustim sync...
echo.
powershell -ExecutionPolicy Bypass -File "%~dp0sync_sklad.ps1"
echo.
pause
