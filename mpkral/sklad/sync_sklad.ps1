# M+P Král — Sync skladu z Pohody do Supabase
# PowerShell — NEVYŽADUJE Excel ani žádnou instalaci
# Čte xlsx přímo jako ZIP/XML

param([string]$ExcelPath)

$SUPABASE_URL = "https://yqklnqmcjloxwdtifkjb.supabase.co"
$SUPABASE_KEY = "sb_publishable_gZI-26x3NF4Dc5h-BuOpjg_3Y0n2Um-"

if (-not $ExcelPath) {
    $folders = @(
        "$env:USERPROFILE\Desktop\Export Skladu MP Král",
        "$env:USERPROFILE\Desktop\Export Skladu MP Kral",
        "$env:USERPROFILE\Desktop"
    )
    foreach ($folder in $folders) {
        if (Test-Path $folder) {
            $found = Get-ChildItem -Path $folder -Filter "*.xlsx" -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($found) { $ExcelPath = $found.FullName; break }
        }
    }
}

if (-not $ExcelPath -or -not (Test-Path $ExcelPath)) {
    Write-Host "CHYBA: Excel soubor nenalezen!" -ForegroundColor Red
    Write-Host "Exportuj zasoby z Pohody a uloz na plochu." -ForegroundColor Yellow
    exit 1
}

Write-Host "Ctu Excel: $ExcelPath" -ForegroundColor Cyan

# --- Čtení XLSX bez Excelu (xlsx = ZIP s XML uvnitř) ---
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($ExcelPath)

    # Načti shared strings (texty)
    $ssEntry = $zip.Entries | Where-Object { $_.FullName -eq "xl/sharedStrings.xml" }
    $strings = @()
    if ($ssEntry) {
        $sr = New-Object System.IO.StreamReader($ssEntry.Open())
        $ssXml = [xml]$sr.ReadToEnd()
        $sr.Close()
        foreach ($si in $ssXml.sst.si) {
            if ($si.t -is [string]) {
                $strings += $si.t
            } elseif ($si.t.'#text') {
                $strings += $si.t.'#text'
            } elseif ($si.r) {
                $text = ""
                foreach ($r in $si.r) { $text += $r.t }
                $strings += $text
            } else {
                $strings += [string]$si.t
            }
        }
    }

    # Načti sheet1
    $sheetEntry = $zip.Entries | Where-Object { $_.FullName -match "xl/worksheets/sheet1.xml" }
    $sr2 = New-Object System.IO.StreamReader($sheetEntry.Open())
    $sheetXml = [xml]$sr2.ReadToEnd()
    $sr2.Close()
    $zip.Dispose()

    # Parsuj řádky
    $rows = @()
    foreach ($row in $sheetXml.worksheet.sheetData.row) {
        $cells = @{}
        foreach ($c in $row.c) {
            $ref = $c.r
            # Extrahuj sloupec (písmeno) z reference (např. "A1" → "A")
            $colLetter = ($ref -replace '[0-9]', '')
            # Převeď písmeno na číslo (A=1, B=2, ..., AA=27)
            $colNum = 0
            foreach ($ch in $colLetter.ToCharArray()) {
                $colNum = $colNum * 26 + ([int][char]$ch - 64)
            }

            $val = $null
            if ($c.t -eq "s" -and $c.v -ne $null) {
                # Shared string — index do tabulky textů
                $idx = [int]$c.v
                if ($idx -lt $strings.Count) { $val = $strings[$idx] }
            } elseif ($c.t -eq "inlineStr") {
                # Inline string — text přímo v buňce <is><t>...</t></is>
                if ($c.is -and $c.is.t) {
                    if ($c.is.t -is [string]) { $val = $c.is.t }
                    elseif ($c.is.t.'#text') { $val = $c.is.t.'#text' }
                    else { $val = [string]$c.is.t }
                }
            } elseif ($c.t -eq "str") {
                # Formula string result
                $val = $c.v
            } else {
                # Číslo nebo jiná hodnota
                $val = $c.v
            }
            $cells[$colNum] = $val
        }
        $rows += ,$cells
    }

    Write-Host "Nacteno $($rows.Count) radku z Excelu" -ForegroundColor Gray
    Write-Host "Shared strings: $($strings.Count)" -ForegroundColor Gray

    # Debug: zobraz prvních 5 řádků
    Write-Host "Prvnich 5 radku z XML:" -ForegroundColor DarkGray
    for ($dbg = 0; $dbg -lt [math]::Min(5, $rows.Count); $dbg++) {
        $dr = $rows[$dbg]
        $vals = @()
        foreach ($dk in ($dr.Keys | Sort-Object)) { $vals += "$dk=$($dr[$dk])" }
        Write-Host "  Radek $($dbg+1): $($vals -join ' | ')" -ForegroundColor DarkGray
    }

    # --- Hledej hlavičku (řádek s "Kód") ---
    $headerRowIdx = -1
    $colKod = 0; $colNazev = 0; $colStav = 0
    for ($i = 0; $i -lt [math]::Min(10, $rows.Count); $i++) {
        $r = $rows[$i]
        foreach ($key in $r.Keys) {
            $cellVal = [string]$r[$key]
            $t = $cellVal.Trim()
            # Porovnání bez diakritiky v patternu (PS 5.1 čte ps1 jako ANSI)
            if ($t -match '^K.d$' -or $t -eq 'Kod') {
                $headerRowIdx = $i
                $colKod = $key
            }
            if ($t -match '^N.zev$' -or $t -eq 'Nazev') { $colNazev = $key }
            if ($t -match 'Stav z.soby|Stav zasoby|Mno') { $colStav = $key }
        }
        if ($headerRowIdx -ge 0) { break }
    }

    if ($headerRowIdx -lt 0) {
        Write-Host "CHYBA: Nenalezen sloupec Kod v hlavicce!" -ForegroundColor Red
        exit 1
    }

    Write-Host "Hlavicka na radku $($headerRowIdx + 1), Kod=sl.$colKod, Nazev=sl.$colNazev, Stav=sl.$colStav" -ForegroundColor Gray

    # --- Načti položky ---
    $items = @()
    $seenKods = @{}
    $dataStart = $headerRowIdx + 2  # přeskočí prázdný řádek po hlavičce

    for ($i = $dataStart; $i -lt $rows.Count; $i++) {
        $r = $rows[$i]
        $kod = [string]$r[$colKod]
        if (-not $kod -or $kod.Trim() -eq '' -or $kod -match 'Celkem|Strana|^K.d$|^Kod$|^Typ$') { continue }
        $kod = $kod.Trim()
        if ($seenKods.ContainsKey($kod)) { continue }
        $seenKods[$kod] = $true

        $nazev = if ($r[$colNazev]) { [string]$r[$colNazev] } else { '' }

        # Hledej stav zásoby - může být posunutý v tiskovém exportu
        $qty = 0
        foreach ($offset in @(0, 1, 2, 3)) {
            $testCol = $colStav + $offset
            $v = $r[$testCol]
            if ($v -ne $null -and $v -match '^\d') {
                $qty = [int][math]::Floor([double]$v)
                break
            }
        }

        $items += @{
            kod = $kod
            nazev = $nazev.Trim()
            carovy_kod = $null
            mnozstvi = $qty
        }
    }

    Write-Host "Nacteno $($items.Count) polozek" -ForegroundColor Green

} catch {
    Write-Host "CHYBA pri cteni Excelu: $_" -ForegroundColor Red
    exit 1
}

if ($items.Count -eq 0) {
    Write-Host "Zadne polozky k nahrani!" -ForegroundColor Yellow
    exit 1
}

# Zobraz prvních 10
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

    # Po dávkách max 200
    $batch = 200
    for ($i = 0; $i -lt $items.Count; $i += $batch) {
        $chunk = $items[$i..[math]::Min($i + $batch - 1, $items.Count - 1)]
        $json = $chunk | ConvertTo-Json -Depth 3
        if ($chunk.Count -eq 1) { $json = "[$json]" }
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
        Invoke-RestMethod -Uri "$SUPABASE_URL/rest/v1/sklad" -Method Post -Headers $apiHeaders -Body $bytes | Out-Null
        Write-Host "  Nahrano $([math]::Min($i + $batch, $items.Count))/$($items.Count)"
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  HOTOVO! $($items.Count) polozek na webu." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green

} catch {
    Write-Host "CHYBA pri nahravani: $_" -ForegroundColor Red
    exit 1
}
