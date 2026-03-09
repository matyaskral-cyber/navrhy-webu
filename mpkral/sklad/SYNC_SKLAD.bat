@echo off
chcp 65001 >nul
echo ========================================
echo   M+P Kral - Aktualizace skladu na webu
echo ========================================
echo.
echo Hledam soubor Zasoby.xlsx na plose...

set EXCEL="%USERPROFILE%\Desktop\Zásoby.xlsx"
if not exist %EXCEL% (
    echo.
    echo CHYBA: Soubor Zasoby.xlsx nenalezen na plose!
    echo.
    echo Nejdriv exportuj zasoby z Pohody:
    echo   Sklady - Zasoby - Soubor - Datova komunikace
    echo   - Export agendy - Excel 2007
    echo.
    pause
    exit /b 1
)

echo Nalezen! Spoustim sync...
echo.
python "%~dp0sync_pohoda.py" %EXCEL%

if errorlevel 1 (
    echo.
    echo CHYBA pri synchronizaci!
    pause
)
