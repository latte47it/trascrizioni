# ==========================================
# 1. FUNZIONE PER LEGGERE IL FILE CONFIG.INI
# ==========================================
function Get-IniContent ($filePath) {
    $ini = @{}
    $section = "NO_SECTION"
    Get-Content $filePath | ForEach-Object {
        $line = $_.Trim()
        if ($line.StartsWith("[") -and $line.EndsWith("]")) {
            $section = $line.Substring(1, $line.Length - 2)
            $ini[$section] = @{}
        } elseif ($line -and -not $line.StartsWith(";")) {
            $parts = $line -split '=', 2
            if ($parts.Count -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()
                $ini[$section][$key] = $value
            }
        }
    }
    return $ini
}

# ==========================================
# 2. CARICAMENTO CONFIGURAZIONE DA CONFIG.INI
# ==========================================
$configFile = "config.ini"

if (-not (Test-Path $configFile)) {
    Write-Host "Errore: File $configFile non trovato!" -ForegroundColor Red
    exit
}

$config = Get-IniContent $configFile

$dbHost = $config["DATABASE"]["host"]
$dbUser = $config["DATABASE"]["user"]
$dbPass = $config["DATABASE"]["password"]
$dbName = $config["DATABASE"]["database"]
$dbPort = $config["DATABASE"]["port"]
$cartellaBase = $config["APPLICAZIONE"]["cartella_iniziale"].TrimEnd('\')

Write-Host "Cartella di scansione: $cartellaBase" -ForegroundColor Cyan

# ==========================================
# 3. RECUPERO FILE AUDIO E SOTTOCARTELLE
# ==========================================
if (-not (Test-Path $cartellaBase)) {
    Write-Host "Errore: La cartella $cartellaBase non esiste!" -ForegroundColor Red
    exit
}

$estensioni = @(".mp3", ".wav", ".m4a")

# Mappiamo ogni file creando un oggetto con Nome, Cartella e Percorso Relativo
$fileLocali = Get-ChildItem -Path $cartellaBase -Recurse -File | 
    Where-Object { $estensioni -contains $_.Extension.ToLower() } | 
    Select-Object @(
        @{Name="NomeFile"; Expression={$_.Name}},
        @{Name="Cartella"; Expression={$_.DirectoryName}},
        @{Name="PercorsoRelativo"; Expression={$_.FullName.Substring($cartellaBase.Length + 1)}}
    )

Write-Host "Trovati $($fileLocali.Count) file audio nella cartella e sottocartelle." -ForegroundColor Gray

# ==========================================
# 4. QUERY SU MYSQL VIA COMMAND-LINE
# ==========================================
# Estraiamo dal DB sia il nome del file sia l'eventuale percorso/cartella salvato
$query = "SELECT DISTINCT nome_file FROM trascrizioni;"

$fileNelDB = & 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe' --host=$dbHost --port=$dbPort --user=$dbUser "--password=$dbPass" --database=$dbName -B -N -e $query 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Errore durante la connessione al database MySQL." -ForegroundColor Red
    exit
}

# ==========================================
# 5. CONFRONTO E STAMPA CON CARTELLA
# ==========================================
$mancanti = $fileLocali | Where-Object { 
    $fileNelDB -notcontains $_.NomeFile -and $fileNelDB -notcontains $_.PercorsoRelativo
}

Write-Host "`n=================================================================" -ForegroundColor White
if ($mancanti) {
    Write-Host "FILE ANCORA DA TRASCRIVERE ($($mancanti.Count)):" -ForegroundColor Yellow
    Write-Host "=================================================================" -ForegroundColor White
    
    foreach ($item in $mancanti) {
        # Mostra sia la sottocartella che il nome del file
        Write-Host "[MANCA] " -NoNewline -ForegroundColor Red
        Write-Host "Cartella: " -NoNewline -ForegroundColor Gray
        Write-Host "$($item.Cartella)\" -NoNewline -ForegroundColor Cyan
        Write-Host "$($item.NomeFile)" -ForegroundColor White
    }
} else {
    Write-Host "Tutti i file audio presenti risultano già nel database!" -ForegroundColor Green
}
Write-Host "=================================================================" -ForegroundColor White