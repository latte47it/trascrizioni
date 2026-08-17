import os
import tkinter as tk
from tkinter import ttk, messagebox
from mutagen.mp3 import MP3

def carica_e_calcola():
    # Svuota la tabella prima di ricaricare i dati
    for riga in tabella.get_children():
        tabella.delete(riga)
        
    cartella_attuale = os.getcwd()
    lbl_cartella.config(text=f"Cartella: {cartella_attuale}")
    
    totale_secondi = 0
    contatore_file = 0

    files = [f for f in os.listdir(cartella_attuale) if f.lower().endswith('.mp3')]
    
    if not files:
        messagebox.showwarning("Attenzione", "Nessun file MP3 trovato in questa cartella!")
        return

    for nome_file in files:
        percorso_completo = os.path.join(cartella_attuale, nome_file)
        
        # Calcolo Dimensione
        byte_dimensione = os.path.getsize(percorso_completo)
        dimensione_mb = f"{byte_dimensione / (1024 * 1024):.2f} MB"
        
        # Lettura accurata della durata con Mutagen
        try:
            audio = MP3(percorso_completo)
            durata_file_secondi = int(audio.info.length)
            totale_secondi += durata_file_secondi
            
            # Formattazione corretta della stringa visiva
            h_f = durata_file_secondi // 3600
            m_f = (durata_file_secondi % 3600) // 60
            s_f = durata_file_secondi % 60
            
            if h_f > 0:
                durata_stringa = f"{h_f:02d}:{m_f:02d}:{s_f:02d}"
            else:
                durata_stringa = f"{m_f:02d}:{s_f:02d}"
        except Exception:
            durata_stringa = "--:--"

        # Inserimento sicuro dei valori estratti
        tabella.insert("", tk.END, values=(nome_file, durata_stringa, dimensione_mb))
        contatore_file += 1

    # Calcolo finale del tempo complessivo generale
    ore = totale_secondi // 3600
    minuti = (totale_secondi % 3600) // 60
    secondi = totale_secondi % 60
    
    lbl_totale.config(text=f"⏱️ Tempo Totale Complessivo ({contatore_file} file): {ore} ore, {minuti} minuti, {secondi} secondi")

# --- COSTRUZIONE INTERFACCIA GRAFICA (GUI) ---
app = tk.Tk()
app.title("Esploratore Durata Omelie MP3 (Infallibile) ⛪")
app.geometry("700x480")

style = ttk.Style()
style.theme_use('vista')

frame = ttk.Frame(app, padding="15")
frame.pack(fill=tk.BOTH, expand=True)

lbl_titolo = ttk.Label(frame, text="Elenco File MP3 e Tempi di Durata", font=("Segoe UI", 12, "bold"), foreground="#2c3e50")
lbl_titolo.pack(anchor=tk.W, pady=(0, 2))

lbl_cartella = ttk.Label(frame, text="Cartella: ", font=("Segoe UI", 9, "italic"), foreground="gray")
lbl_cartella.pack(anchor=tk.W, pady=(0, 10))

frame_tabella = ttk.Frame(frame)
frame_tabella.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

colonne = ("nome", "durata", "dimensione")
tabella = ttk.Treeview(frame_tabella, columns=colonne, show="headings", selectmode="browse")

tabella.heading("nome", text="Nome del File Audio")
tabella.heading("durata", text="Durata Reale")
tabella.heading("dimensione", text="Dimensione")

tabella.column("nome", width=420, anchor=tk.W)
tabella.column("durata", width=100, anchor=tk.CENTER)
tabella.column("dimensione", width=100, anchor=tk.CENTER)

scrollbar = ttk.Scrollbar(frame_tabella, orient=tk.VERTICAL, command=tabella.yview)
tabella.configure(yscrollcommand=scrollbar.set)

tabella.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

lbl_totale = ttk.Label(frame, text="⏱️ Tempo Totale Complessivo: 0 ore, 0 minuti, 0 secondi", font=("Segoe UI", 10, "bold"), foreground="#27ae60")
lbl_totale.pack(anchor=tk.W, pady=(5, 10))

btn_ricarica = ttk.Button(frame, text="🔄 Carica / Aggiorna Elenco Corrente", command=carica_e_calcola)
btn_ricarica.pack(fill=tk.X, ipady=5)

app.after(100, carica_e_calcola)
app.mainloop()