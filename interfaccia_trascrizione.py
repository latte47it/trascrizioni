import configparser
from datetime import datetime
import os
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import mysql.connector
import whisper  # Libreria openai-whisper

# ==========================================
# GESTIONE CONFIGURAZIONE ESTERNA (config.ini)
# ==========================================
CONFIG_FILE = "config.ini"


def carica_configurazione():
    """Carica il file config.ini. Se non esiste, lo crea con i valori di default."""
    config = configparser.ConfigParser()

    if not os.path.exists(CONFIG_FILE):
        config["DATABASE"] = {
            "host": "localhost",
            "user": "root",
            "password": "maurof",
            "database": "archivio_omelie_nuovo",
            "port": "3306",
        }
        config["WHISPER"] = {
            "percorso_modello_turbo": (
                r"C:\tmp\omelie_nuovo\whisper-turbo-local\large-v3-turbo.pt"
            ),
            "lingua": "it",
        }
        config["APPLICAZIONE"] = {"cartella_iniziale": ""}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            config.write(f)
    else:
        config.read(CONFIG_FILE, encoding="utf-8")

    return config


config = carica_configurazione()

DB_CONFIG = {
    "host": config.get("DATABASE", "host", fallback="localhost"),
    "user": config.get("DATABASE", "user", fallback="root"),
    "password": config.get("DATABASE", "password", fallback=""),
    "database": config.get("DATABASE", "database", fallback="archivio_omelie_nuovo"),
    "port": config.getint("DATABASE", "port", fallback=3306),
}

PERCORSO_MODELLO_TURBO = config.get(
    "WHISPER", "percorso_modello_turbo", fallback="turbo"
)
LINGUA_WHISPER = config.get("WHISPER", "lingua", fallback="it")

# ==========================================
# VARIABILI GLOBALI DI STATO
# ==========================================
cartella_selezionata = ""
file_nel_db = set()
# Salviamo tuple/dizionari dei file audio trovati
tutti_i_file_mp3 = []


# ==========================================
# FUNZIONI DATABASE E LOGICA BUSINESS
# ==========================================
def ottieni_file_gia_trascritti():
    """Legge il DB e restituisce un set con i nomi dei file già elaborati."""
    gia_trascritti = set()
    try:
        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor()
        cursor.execute("SELECT nome_file FROM trascrizioni")
        for (nome_file,) in cursor.fetchall():
            if nome_file:
                gia_trascritti.add(nome_file.strip().lower())
        cursor.close()
        db.close()
    except mysql.connector.Error as err:
        messagebox.showerror(
            "Errore Database", f"Impossibile connettersi a MySQL:\n{err}"
        )
    except Exception as e:
        print(f"Errore DB: {e}")
    return gia_trascritti


def seleziona_cartella():
    global cartella_selezionata, file_nel_db, tutti_i_file_mp3
    cartella_init = config.get("APPLICAZIONE", "cartella_iniziale", fallback="")

    cartella = filedialog.askdirectory(
        title="Seleziona la Cartella Radice delle Omelie",
        initialdir=cartella_init if os.path.exists(cartella_init) else None,
    )
    if not cartella:
        return

    cartella_selezionata = cartella
    entry_cartella.config(state=tk.NORMAL)
    entry_cartella.delete(0, tk.END)
    entry_cartella.insert(0, cartella)
    entry_cartella.config(state=tk.DISABLED)

    file_nel_db = ottieni_file_gia_trascritti()

    # 🔍 SCANSIONE RICORSIVA DI TUTTE LE SOTTOCARTELLE (os.walk)
    tutti_i_file_mp3 = []
    lbl_stato_numerico.config(text="Scansione delle cartelle in corso...")
    app.update_idletasks()

    for root, dirs, files in os.walk(cartella):
        for file in files:
            if file.lower().endswith(".mp3"):
                percorso_completo = os.path.join(root, file)
                percorso_relativo = os.path.relpath(percorso_completo, cartella)
                tutti_i_file_mp3.append(
                    {
                        "nome_file": file,
                        "percorso_completo": percorso_completo,
                        "percorso_relativo": percorso_relativo,
                    }
                )

    aggiorna_tabella_visiva()


def aggiorna_tabella_visiva():
    """Ridisegna la tabella mostrando i file e il loro percorso relativo."""
    for riga in tabella.get_children():
        tabella.delete(riga)

    nascondi_gia_fatti = var_filtro.get()
    conteggio_mostrati = 0

    for item in tutti_i_file_mp3:
        nome_file = item["nome_file"]
        percorso_rel = item["percorso_relativo"]

        stato_db = (
            "Già Trascritto"
            if nome_file.strip().lower() in file_nel_db
            else "Nuovo (Da Fare)"
        )

        if nascondi_gia_fatti and stato_db == "Già Trascritto":
            continue

        tabella.insert(
            "",
            tk.END,
            values=(percorso_rel, stato_db),
            tags=(item["percorso_completo"],),
        )
        conteggio_mostrati += 1

    lbl_stato_numerico.config(
        text=(
            f"Trovati {len(tutti_i_file_mp3)} file MP3 totali | Visualizzati:"
            f" {conteggio_mostrati}"
        )
    )


# ==========================================
# NUOVE FUNZIONI PER LA SELEZIONE
# ==========================================
def seleziona_tutti():
    """Seleziona tutte le righe attualmente visibili nella tabella."""
    righe = tabella.get_children()
    if righe:
        tabella.selection_set(righe)


def deseleziona_tutti():
    """Deseleziona tutte le righe dalla tabella."""
    tabella.selection_remove(tabella.selection())


# ==========================================
# ELABORAZIONE IN THREAD
# ==========================================
def avvia_elaborazione_thread():
    t = threading.Thread(target=processa_file_selezionati)
    t.daemon = True
    t.start()


def processa_file_selezionati():
    righe_selezionate = tabella.selection()

    if not righe_selezionate:
        messagebox.showwarning("Attenzione", "Seleziona almeno un file dalla tabella!")
        return

    totale_file = len(righe_selezionate)

    btn_avvia.config(state=tk.DISABLED)
    btn_sfoglia.config(state=tk.DISABLED)
    btn_sel_tutti.config(state=tk.DISABLED)
    btn_desel_tutti.config(state=tk.DISABLED)
    chk_filtro.config(state=tk.DISABLED)

    progress_bar["maximum"] = totale_file
    progress_bar["value"] = 0

    try:
        lbl_stato_numerico.config(text="Inizializzazione Whisper TURBO...")
        lbl_file_corrente.config(text="Caricamento modello dalla cache locale...")
        app.update_idletasks()

        # 🚀 Caricamento standard e sicuro gestito direttamente da Whisper
        model = whisper.load_model("turbo")

        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor()

        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor()

        for indice, riga_id in enumerate(righe_selezionate, start=1):
            valori_riga = tabella.item(riga_id, "values")
            percorso_relativo = valori_riga[0]
            nome_file = os.path.basename(percorso_relativo)

            percorso_completo = tabella.item(riga_id, "tags")[0]

            match_data = re.search(r"\b\d{8}\b", nome_file) or re.search(
                r"\d{8}", nome_file
            )
            data_rilevata = None
            if match_data:
                stringa_data = match_data.group(0)
                try:
                    data_rilevata = datetime.strptime(stringa_data, "%Y%m%d").strftime(
                        "%Y-%m-%d"
                    )
                except ValueError:
                    data_rilevata = None

            lbl_stato_numerico.config(
                text=f"Trascrizione in corso: {indice} di {totale_file}"
            )
            lbl_file_corrente.config(text=f"Elaborazione: {percorso_relativo}")
            progress_bar["value"] = indice - 0.5
            app.update_idletasks()

            try:
                result = model.transcribe(percorso_completo, language=LINGUA_WHISPER)
                testo_trascritto = result["text"].strip()

                query = """
                    INSERT INTO trascrizioni (nome_file, testo_completo, modello_usato, data_omelia) 
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(
                    query, (nome_file, testo_trascritto, "Whisper Turbo", data_rilevata)
                )
                db.commit()

            except Exception as e:
                print(f"Errore su {nome_file}: {e}")

            progress_bar["value"] = indice
            app.update_idletasks()

        cursor.close()
        db.close()

        lbl_stato_numerico.config(text="Trascrizione completata con successo! 🎉")
        lbl_file_corrente.config(text="")
        messagebox.showinfo(
            "Fatto", f"Elaborati tutti i {totale_file} file selezionati!"
        )

    except Exception as global_error:
        messagebox.showerror("Errore Grave", f"Errore di sistema:\n{global_error}")

    finally:
        btn_avvia.config(state=tk.NORMAL)
        btn_sfoglia.config(state=tk.NORMAL)
        btn_sel_tutti.config(state=tk.NORMAL)
        btn_desel_tutti.config(state=tk.NORMAL)
        chk_filtro.config(state=tk.NORMAL)

        global file_nel_db
        file_nel_db = ottieni_file_gia_trascritti()
        aggiorna_tabella_visiva()


# ==========================================
# INTERFACCIA GRAFICA (GUI)
# ==========================================
app = tk.Tk()
app.title("Gestore Ricorsivo Trascrizioni Omelie - Whisper TURBO ⛪")
app.geometry("840x620")

style = ttk.Style()
style.theme_use("vista")

frame = ttk.Frame(app, padding="15")
frame.pack(fill=tk.BOTH, expand=True)

# Selezione Cartella Radice
lbl_info = ttk.Label(
    frame,
    text="Seleziona la cartella RADICE per scansionare le sottocartelle:",
    font=("Segoe UI", 10),
)
lbl_info.pack(anchor=tk.W, pady=(0, 5))

frame_sfoglia = ttk.Frame(frame)
frame_sfoglia.pack(fill=tk.X, pady=(0, 10))

entry_cartella = ttk.Entry(frame_sfoglia)
entry_cartella.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=3)
entry_cartella.config(state=tk.DISABLED)

btn_sfoglia = ttk.Button(
    frame_sfoglia, text="Scegli Cartella Radice...", command=seleziona_cartella
)
btn_sfoglia.pack(side=tk.RIGHT)

# Checkbox Filtro Duplicati
var_filtro = tk.BooleanVar(value=True)
chk_filtro = ttk.Checkbutton(
    frame,
    text=(
        " Nascondi file MP3 già presenti nel Database (Mostra solo novità da"
        " trascrivere)"
    ),
    variable=var_filtro,
    command=aggiorna_tabella_visiva,
)
chk_filtro.pack(anchor=tk.W, pady=(0, 10))

# --- BARRA CON PULSANTI SELEZIONE ---
frame_pulsanti_sel = ttk.Frame(frame)
frame_pulsanti_sel.pack(fill=tk.X, pady=(0, 5))

btn_sel_tutti = ttk.Button(
    frame_pulsanti_sel, text="✅ Seleziona Tutti", command=seleziona_tutti
)
btn_sel_tutti.pack(side=tk.LEFT, padx=(0, 5))

btn_desel_tutti = ttk.Button(
    frame_pulsanti_sel, text="❌ Deseleziona Tutti", command=deseleziona_tutti
)
btn_desel_tutti.pack(side=tk.LEFT)

# Tabella Esplorativa (Treeview)
frame_tabella = ttk.Frame(frame)
frame_tabella.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

colonne = ("percorso", "stato")
tabella = ttk.Treeview(
    frame_tabella, columns=colonne, show="headings", selectmode="extended"
)

tabella.heading("percorso", text="Percorso Sottocartella / Nome File Audio MP3")
tabella.heading("stato", text="Stato nel DB")

tabella.column("percorso", width=620, anchor=tk.W)
tabella.column("stato", width=150, anchor=tk.CENTER)

scrollbar = ttk.Scrollbar(frame_tabella, orient=tk.VERTICAL, command=tabella.yview)
tabella.configure(yscrollcommand=scrollbar.set)

tabella.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Status e Barra Avanzamento
lbl_stato_numerico = ttk.Label(
    frame,
    text="Seleziona la cartella radice per iniziare la scansione.",
    font=("Segoe UI", 10),
    foreground="#2980b9",
)
lbl_stato_numerico.pack(anchor=tk.W, pady=(5, 2))

lbl_file_corrente = ttk.Label(
    frame, text="", font=("Segoe UI", 9, "italic"), foreground="gray"
)
lbl_file_corrente.pack(anchor=tk.W, pady=(0, 5))

progress_bar = ttk.Progressbar(frame, orient=tk.HORIZONTAL, mode="determinate")
progress_bar.pack(fill=tk.X, pady=(0, 15), ipady=3)

# Pulsante Esecuzione
btn_avvia = ttk.Button(
    frame,
    text="🚀 Avvia Trascrizione Batch dei File Selezionati",
    command=avvia_elaborazione_thread,
)
btn_avvia.pack(fill=tk.X, ipady=8)

if __name__ == "__main__":
    app.mainloop()
