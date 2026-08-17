param(
    [string]$Percorso = (Get-Location).Path
)

if (-not (Test-Path -Path $Percorso)) {
    Write-Host "La cartella specificata non esiste: $Percorso" -ForegroundColor Red
    exit
}

$shell = New-Object -ComObject Shell.Application
$fileMp3 = Get-ChildItem -Path $Percorso -Filter *.mp3 -Recurse

if (-not $fileMp3 -or $fileMp3.Count -eq 0) {
    Write-Host "Nessun file MP3 trovato in $Percorso" -ForegroundColor Yellow
    exit
}

# Hashtable per salvare dati per ogni cartella
$cartelleDati = @{}
$totaleSecondiGenerale = 0

foreach ($file in $fileMp3) {
    $folderObject = $shell.Namespace($file.DirectoryName)
    $item = $folderObject.ParseName($file.Name)
    $durataRaw = $folderObject.GetDetailsOf($item, 27)
    
    if (-not [string]::IsNullOrEmpty($durataRaw)) {
        $durataClean = $durataRaw -replace '[^\d:]', ''
        $secFile = 0
        
        if ($durataClean -match '^(\d+):(\d+):(\d+)$') {
            $secFile = ([int]$Matches[1] * 3600) + ([int]$Matches[2] * 60) + [int]$Matches[3]
        } elseif ($durataClean -match '^(\d+):(\d+)$') {
            $secFile = ([int]$Matches[1] * 60) + [int]$Matches[2]
        }
        
        $dirPath = $file.DirectoryName
        if (-not $cartelleDati.ContainsKey($dirPath)) {
            $cartelleDati[$dirPath] = @{ Count = 0; Secondi = 0 }
        }
        
        $cartelleDati[$dirPath].Count++
        $cartelleDati[$dirPath].Secondi += $secFile
        $totaleSecondiGenerale += $secFile
    }
}

function Formatta-Tempo($sec) {
    $h = [Math]::Floor($sec / 3600)
    $m = [Math]::Floor(($sec % 3600) / 60)
    $s = $sec % 60
    return "$h ore, $m minuti, $s secondi"
}

# Creazione del testo del report
$fileOutput = Join-Path -Path $Percorso -ChildPath "report_durate.txt"
$report = @()
$report += "========================================================"
$report += "          REPORT DURATA E CONTEGGIO FILE MP3            "
$report += "========================================================"
$report += "Cartella analizzata: $Percorso`n"
$report += "--- DETTAGLIO PER SOTTOCARTELLE ---"

foreach ($key in $cartelleDati.Keys) {
    $num = $cartelleDati[$key].Count
    $tempo = Formatta-Tempo($cartelleDati[$key].Secondi)
    $report += "`n[Cartella] $key"
    $report += "   - Numero di file MP3: $num"
    $report += "   - Durata totale:      $tempo"
}

$report += "`n========================================================"
$report += "                 RIEPILOGO COMPLESSIVO                  "
$report += "========================================================"
$report += "TOTALE FILE MP3 TROVATI: $($fileMp3.Count)"
$report += "TEMPO TOTALE ARCHIVIO:   $(Formatta-Tempo($totaleSecondiGenerale))"
$report += "========================================================"

$report | Out-File -FilePath $fileOutput -Encoding utf8
Write-Host "OK: Report generato con successo in: $fileOutput" -ForegroundColor Green