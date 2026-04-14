# M+P Král — Sync skladu z Pohody do Supabase
# PowerShell — žádná instalace, běží nativně na Windows 10/11
# Podporuje tiskový export "Skladové zásoby" i běžný tabulkový export

param([string]$ExcelPath)

$SUPABASE_URL = "https://yqklnqmcjloxwdtifkjb.supabase.co"
$SUPABASE_KEY = "sb_publishable_gZI-26x3NF4Dc5h-BuOpjg_3Y0n2Um-"

if (-not $ExcelPath) {
    # Hledej ve složce "Export Skladu MP Král" na ploše, pak přímo na ploše
    $folders = @(
        "$env:USERPROFILE\Desktop\Export Skladu MP Král",
        "$env:USERPROFILE\Desktop"
    )
    $names = @("Zásoby.xlsx", "Skladové_zásoby.xlsx", "Skladove_zasoby.xlsx")
    foreach ($folder in $folders) {
        foreach ($name in $names) {
            $p = Join-Path $folder $name
            if (Test-Path $p) { $ExcelPath = $p; break }
        }
        if ($ExcelPath) { break }
        # Hledej jakýkoli xlsx ve složce
        if (Test-Path $folder) {
            $found = Get-ChildItem -Path $folder -Filter "*.xlsx" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($found) { $ExcelPath = $found.FullName; break }
        }
    }
}

if (-not $ExcelPath -or -not (Test-Path $ExcelPath)) {
    Write-Host "CHYBA: Excel soubor nenalezen na plose!" -ForegroundColor Red
    Write-Host "Exportuj zasoby z Pohody a uloz na plochu." -ForegroundColor Yellow
    exit 1
}

Write-Host "Ctu Excel: $ExcelPath" -ForegroundColor Cyan

$excel = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $wb = $excel.Workbooks.Open($ExcelPath)
    $ws = $wb.Sheets.Item(1)

    $lastRow = $ws.UsedRange.Rows.Count
    $lastCol = $ws.UsedRange.Columns.Count

    # --- Detekce formátu ---
    # Hledáme řádek s hlavičkou (obsahuje "Kód")
    $headerRow = 0
    $isPrintExport = $false

    for ($r = 1; $r -le [math]::Min(10, $lastRow); $r++) {
        for ($c = 1; $c -le $lastCol; $c++) {
            $val = [string]$ws.Cells.Item($r, $c).Value2
            if ($val -eq 'Kód' -or $val -eq 'Kod') {
                $headerRow = $r
                break
            }
        }
        if ($headerRow -gt 0) { break }
    }

    $items = @()

    if ($headerRow -ge 3) {
        # --- TISKOVÝ EXPORT (Skladové zásoby) ---
        # Hlavička na řádku 4, data od řádku 6, pevné sloupce
        Write-Host "Format: Tiskovy export (Skladove zasoby)" -ForegroundColor Gray
        $isPrintExport = $true

        # Najdi sloupce v hlavičce
        $colKod = 0; $colNazev = 0; $colStav = 0; $colBarcode = 0
        for ($c = 1; $c -le $lastCol; $c++) {
            $val = [string]$ws.Cells.Item($headerRow, $c).Value2
            if ($val -match '^Kód$|^Kod$') { $colKod = $c }
            if ($val -match '^Název$|^Nazev$') { $colNazev = $c }
            if ($val -match 'Stav zásoby|Stav zasoby|Množství') { $colStav = $c }
            if ($val -match 'Čárkód|Carkod|EAN|Čár\.kód') { $colBarcode = $c }
        }

        # V tiskovém exportu může být stav zásoby posunutý - hledej v datech
        $dataStart = $headerRow + 2
        for ($r = $dataStart; $r -le $lastRow; $r++) {
            $kod = [string]$ws.Cells.Item($r, $colKod).Value2
            if (-not $kod -or $kod.Trim() -eq '' -or $kod -match 'Celkem|Součet|Strana') { continue }

            $nazev = [string]$ws.Cells.Item($r, $colNazev).Value2

            # Hledej stav zásoby - může být v jiném sloupci než hlavička říká
            $qty = 0
            if ($colStav -gt 0) {
                # Zkus sloupec z hlavičky i +1, +2 (tiskový export je posunutý)
                foreach ($offset in @(0, 1, 2, 3)) {
                    $testCol = $colStav + $offset
                    $v = $ws.Cells.Item($r, $testCol).Value2
                    if ($v -ne $null -and $v -match '^\d') {
                        $qty = [int][math]::Floor([double]$v)
                        break
                    }
                }
            }

            $barcode = $null
            if ($colBarcode -gt 0) {
                $barcode = [string]$ws.Cells.Item($r, $colBarcode).Value2
                if ($barcode -eq '') { $barcode = $null }
            }

            $items += @{
                kod = $kod.Trim()
                nazev = if ($nazev) { $nazev.Trim() } else { '' }
                carovy_kod = $barcode
                mnozstvi = $qty
            }
        }
    } else {
        # --- TABULKOVÝ EXPORT (datová komunikace) ---
        Write-Host "Format: Tabulkovy export" -ForegroundColor Gray
        if ($headerRow -eq 0) { $headerRow = 1 }

        $headers = @{}
        for ($c = 1; $c -le $lastCol; $c++) {
            $val = [string]$ws.Cells.Item($headerRow, $c).Value2
            if ($val) { $headers[$val.Trim()] = $c }
        }

        $colKod = if ($headers.ContainsKey('Kód')) { $headers['Kód'] } elseif ($headers.ContainsKey('Kod')) { $headers['Kod'] } else { 0 }
        $colNazev = if ($headers.ContainsKey('Název')) { $headers['Název'] } elseif ($headers.ContainsKey('Nazev')) { $headers['Nazev'] } else { 0 }
        $colBarcode = if ($headers.ContainsKey('Čárkód')) { $headers['Čárkód'] } elseif ($headers.ContainsKey('Carkod')) { $headers['Carkod'] } elseif ($headers.ContainsKey('EAN')) { $headers['EAN'] } elseif ($headers.ContainsKey('Čár.kód')) { $headers['Čár.kód'] } else { 0 }
        $colQty = if ($headers.ContainsKey('Stav zásoby')) { $headers['Stav zásoby'] } elseif ($headers.ContainsKey('Stav zasoby')) { $headers['Stav zasoby'] } elseif ($headers.ContainsKey('Množství')) { $headers['Množství'] } else { 0 }

        for ($r = $headerRow + 1; $r -le $lastRow; $r++) {
            $kod = [string]$ws.Cells.Item($r, $colKod).Value2
            if (-not $kod -or $kod.Trim() -eq '') { continue }

            $nazev = [string]$ws.Cells.Item($r, $colNazev).Value2
            $barcode = if ($colBarcode -gt 0) { [string]$ws.Cells.Item($r, $colBarcode).Value2 } else { $null }
            $qty = if ($colQty -gt 0) {
                $v = $ws.Cells.Item($r, $colQty).Value2
                if ($v) { [int][math]::Floor([double]$v) } else { 0 }
            } else { 0 }

            $items += @{
                kod = $kod.Trim()
                nazev = if ($nazev) { $nazev.Trim() } else { '' }
                carovy_kod = if ($barcode -and $barcode.Trim() -ne '') { $barcode.Trim() } else { $null }
                mnozstvi = $qty
            }
        }
    }

    $wb.Close($false)
    $excel.Quit()

    Write-Host "Nacteno $($items.Count) polozek" -ForegroundColor Green

} catch {
    Write-Host "CHYBA pri cteni Excelu: $_" -ForegroundColor Red
    if ($excel) { $excel.Quit() }
    exit 1
} finally {
    if ($excel) { [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null }
}

if ($items.Count -eq 0) {
    Write-Host "Zadne polozky k nahrani!" -ForegroundColor Yellow
    exit 1
}

# Zobraz prvních 10 položek
Write-Host ""
Write-Host "Prvnich 10 polozek:" -ForegroundColor Cyan
$show = [math]::Min(10, $items.Count)
for ($i = 0; $i -lt $show; $i++) {
    $it = $items[$i]
    Write-Host ("  {0,-20} | {1,-35} | {2}" -f $it.kod, $it.nazev, $it.mnozstvi)
}
if ($items.Count -gt 10) { Write-Host "  ... a dalsich $($items.Count - 10) polozek" }
Write-Host ""

# --- Upload do Supabase ---
$apiHeaders = @{
    "apikey" = $SUPABASE_KEY
    "Authorization" = "Bearer $SUPABASE_KEY"
    "Content-Type" = "application/json; charset=utf-8"
    "Prefer" = "return=minimal"
}

try {
    Write-Host "Mazu stara data..." -ForegroundColor Yellow
    Invoke-RestMethod -Uri "$SUPABASE_URL/rest/v1/sklad?id=gt.0" -Method Delete -Headers $apiHeaders | Out-Null

    Write-Host "Nahravam $($items.Count) polozek..." -ForegroundColor Yellow
    $json = $items | ConvertTo-Json -Depth 3
    if ($items.Count -eq 1) { $json = "[$json]" }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    Invoke-RestMethod -Uri "$SUPABASE_URL/rest/v1/sklad" -Method Post -Headers $apiHeaders -Body $bytes | Out-Null

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  HOTOVO! $($items.Count) polozek na webu." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green

} catch {
    Write-Host "CHYBA pri nahravani: $_" -ForegroundColor Red
    exit 1
}
