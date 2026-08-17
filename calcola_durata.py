import os
import sys
from mutagen.mp3 import MP3

# Se viene passato un parametro usa quello, altrimenti usa la cartella corrente
if len(sys.argv) > 1:
    cartella_target = sys.argv[1]
else:
    cartella_target = os.getcwd()

if not os.path.exists(cartella_target):
    print(f"Errore: La cartella '{cartella_target}' non esiste!")
    sys.exit(1)

def formatta_tempo(secondi_totali):
    ore = int(secondi_totali // 3600)
    minuti = int((secondi_totali % 3600) // 60)
    secondi = int(secondi_totali % 60)
    return f"{ore} ore, {minuti} minuti, {secondi} secondi"

# Dizionario per memorizzare i dati di ogni cartella: { cartella: [conteggio, totale_secondi] }
statistiche_cartelle = {}

totale_generale_secondi = 0
totale_generale_file = 0

print(f"Scansione in corso per: {cartella_target} ...\n")

for root, dirs, files in os.walk(cartella_target):
    for file in files:
        if file.lower().endswith('.mp3'):
            percorso_completo = os.path.join(root, file)
            try:
                audio = MP3(percorso_completo)
                durata = audio.info.length
                
                # Inizializza la voce della cartella se non esiste
                if root not in statistiche_cartelle:
                    statistiche_cartelle[root] = [0, 0.0]
                
                statistiche_cartelle[root][0] += 1
                statistiche_cartelle[root][1] += durata
                
                totale_generale_file += 1
                totale_generale_secondi += durata
            except Exception as e:
                print(f"Errore nella lettura di {file}: {e}")

# Nome del file di output
file_output = os.path.join(cartella_target, "report_durate.txt")

with open(file_output, "w", encoding="utf-8") as f:
    f.write("========================================================\n")
    f.write("          REPORT DURATA E CONTEGGIO FILE MP3            \n")
    f.write("========================================================\n\n")
    f.write(f"Cartella analizzata: {cartella_target}\n\n")
    f.write("--- DETTAGLIO PER PERCORSO / SOTTOCARTELLE ---\n")
    
    for cartella, dati in statistiche_cartelle.items():
        num_file, sec = dati
        rel_path = os.path.relpath(cartella, cartella_target)
        if rel_path == ".":
            rel_path = "Cartella Radice"
            
        f.write(f"\n📂 Cartella: {rel_path}\n")
        f.write(f"   • Numero di file MP3: {num_file}\n")
        f.write(f"   • Durata totale:      {formatta_tempo(sec)}\n")

    f.write("\n========================================================\n")
    f.write("                 RIEPILOGO COMPLESSIVO                  \n")
    f.write("========================================================\n")
    f.write(f"TOTALE FILE MP3 TROVATI: {totale_generale_file}\n")
    f.write(f"TEMPO TOTALE ARCHIVIO:   {formatta_tempo(totale_generale_secondi)}\n")
    f.write("========================================================\n")

print(f"✅ Report salvato con successo in:\n{file_output}")