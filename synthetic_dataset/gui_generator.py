#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏥 Medical Redactor - GUI Dataset Generator
=========================================
Interfaccia Grafica (GUI) professionale basata su Tkinter per il modulo 
di generazione di dataset clinici sintetici. Consente l'inserimento
semplificato di tutti i parametri della CLI tramite menu interattivi
senza richiedere l'uso del terminale.
"""

import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText

# Mappatura dei modelli predefiniti per provider
DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022"
}

class DatasetGeneratorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Medical Redactor - Generatore Dataset Clinico Sintetico")
        self.geometry("700x750")
        self.minsize(650, 700)
        
        # Imposta favicon o stile generale
        self.configure(bg="#f8fafc") # Slate 50
        
        # Font personalizzati
        self.font_title = ("Segoe UI", 14, "bold")
        self.font_subtitle = ("Segoe UI", 9, "italic")
        self.font_header = ("Segoe UI", 11, "bold")
        self.font_body = ("Segoe UI", 10)
        self.font_console = ("Consolas", 9)
        
        self.is_generating = False
        self.generation_thread = None
        self.process = None
        
        self.create_styles()
        self.build_ui()
        self.update_mode_states()
        
    def create_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("vista")
        
        # Personalizzazione dei widget TTK
        self.style.configure(".", font=self.font_body)
        self.style.configure("TFrame", background="#f8fafc")
        self.style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        self.style.configure("Header.TLabel", background="#ffffff", font=self.font_header, foreground="#0f172a")
        
        # Pulsanti stilizzati
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background="#0284c7", foreground="#0f172a")
        self.style.configure("Secondary.TButton", font=("Segoe UI", 10), background="#e2e8f0")

    def build_ui(self):
        # 1. Header Banner
        self.header_frame = tk.Frame(self, bg="#0f172a", height=80)
        self.header_frame.pack(fill=tk.X)
        self.header_frame.pack_propagate(False)
        
        title_lbl = tk.Label(
            self.header_frame, 
            text="🏥 MEDICAL REDACTOR - SYNTHETIC DATASET GENERATOR", 
            font=("Segoe UI", 12, "bold"), 
            bg="#0f172a", 
            fg="#f8fafc"
        )
        title_lbl.pack(pady=(18, 2), anchor=tk.CENTER)
        
        desc_lbl = tk.Label(
            self.header_frame, 
            text="Generazione semplificata di note cliniche sintetiche italiane per addestramento e benchmark NER", 
            font=("Segoe UI", 9), 
            bg="#0f172a", 
            fg="#94a3b8"
        )
        desc_lbl.pack(anchor=tk.CENTER)
        
        # Container Principale con scroll
        self.main_container = tk.Frame(self, bg="#f8fafc", padx=15, pady=15)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # --- CARDA 1: CONFIGURAZIONE GENERALE ---
        self.general_card = ttk.Frame(self.main_container, style="Card.TFrame", padding=15)
        self.general_card.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(self.general_card, text="1. Impostazioni Generali", style="Header.TLabel").grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        # Numero Casi
        ttk.Label(self.general_card, text="Numero di casi da generare:", background="#ffffff").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.count_var = tk.StringVar(value="3")
        self.count_spin = ttk.Spinbox(self.general_card, from_=1, to=10000, textvariable=self.count_var, width=10)
        self.count_spin.grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Modalità
        ttk.Label(self.general_card, text="Modalità operativa:", background="#ffffff").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.mode_var = tk.StringVar(value="Offline")
        self.mode_combo = ttk.Combobox(
            self.general_card, 
            textvariable=self.mode_var, 
            values=["Offline (Locale Alta Fedeltà)", "Online (LLM API Esterne)"],
            state="readonly",
            width=30
        )
        self.mode_combo.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5, padx=10)
        self.mode_combo.bind("<<ComboboxSelected>>", self.update_mode_states)
        
        # Output File
        ttk.Label(self.general_card, text="Percorso file di output:", background="#ffffff").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        # Trova il percorso assoluto della cartella di generazione
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_output = os.path.join(script_dir, "synthetic_dataset_output.json")
        
        self.output_var = tk.StringVar(value=default_output)
        self.output_entry = ttk.Entry(self.general_card, textvariable=self.output_var, width=45)
        self.output_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=10)
        
        self.browse_btn = ttk.Button(self.general_card, text="Sfoglia...", command=self.browse_output_file)
        self.browse_btn.grid(row=3, column=2, sticky=tk.W, pady=5)
        
        # --- CARDA 2: INTELLIGENZA ARTIFICIALE (LLM) ---
        self.llm_card = ttk.Frame(self.main_container, style="Card.TFrame", padding=15)
        self.llm_card.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(self.llm_card, text="2. Configurazione LLM (Abilitata solo in modalità Online)", style="Header.TLabel").grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        # Provider
        self.provider_lbl = ttk.Label(self.llm_card, text="LLM Provider:", background="#ffffff")
        self.provider_lbl.grid(row=1, column=0, sticky=tk.W, pady=5)
        self.provider_var = tk.StringVar(value="Gemini")
        self.provider_combo = ttk.Combobox(
            self.llm_card,
            textvariable=self.provider_var,
            values=["Gemini", "OpenAI", "Anthropic"],
            state="readonly",
            width=15
        )
        self.provider_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        self.provider_combo.bind("<<ComboboxSelected>>", self.on_provider_changed)
        
        # Modello
        self.model_lbl = ttk.Label(self.llm_card, text="Modello specifico:", background="#ffffff")
        self.model_lbl.grid(row=2, column=0, sticky=tk.W, pady=5)
        self.model_var = tk.StringVar(value=DEFAULT_MODELS["gemini"])
        self.model_entry = ttk.Entry(self.llm_card, textvariable=self.model_var, width=30)
        self.model_entry.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5, padx=10)
        
        # API Key
        self.key_lbl = ttk.Label(self.llm_card, text="API Key:", background="#ffffff")
        self.key_lbl.grid(row=3, column=0, sticky=tk.W, pady=5)
        self.key_var = tk.StringVar()
        self.key_entry = ttk.Entry(self.llm_card, textvariable=self.key_var, show="*", width=45)
        self.key_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=10)
        
        self.show_key_var = tk.BooleanVar(value=False)
        self.show_key_check = tk.Checkbutton(
            self.llm_card, 
            text="Mostra", 
            variable=self.show_key_var, 
            command=self.toggle_key_visibility,
            bg="#ffffff",
            activebackground="#ffffff"
        )
        self.show_key_check.grid(row=3, column=2, sticky=tk.W, pady=5)
        
        # Helper text per API key da variabile d'ambiente
        self.key_help_lbl = ttk.Label(
            self.llm_card, 
            text="Nota: Se lasciata vuota, verrà letta la variabile d'ambiente (es. GEMINI_API_KEY).",
            background="#ffffff",
            font=self.font_subtitle,
            foreground="#64748b"
        )
        self.key_help_lbl.grid(row=4, column=1, columnspan=2, sticky=tk.W, pady=(0, 5), padx=10)
        
        # --- SEZIONE 3: PULSANTI DI AZIONE ---
        self.action_frame = tk.Frame(self.main_container, bg="#f8fafc")
        self.action_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.generate_btn = tk.Button(
            self.action_frame,
            text="🚀 GENERA DATASET",
            font=("Segoe UI", 10, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            command=self.start_generation
        )
        self.generate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.open_folder_btn = tk.Button(
            self.action_frame,
            text="📂 Apri Cartella Output",
            font=("Segoe UI", 10),
            bg="#e2e8f0",
            fg="#0f172a",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2",
            activebackground="#cbd5e1",
            command=self.open_output_folder
        )
        self.open_output_folder_btn_state(False) # Disabilitato inizialmente
        self.open_folder_btn.pack(side=tk.LEFT)
        
        # --- SEZIONE 4: CONSOLE LOG OUTPUT ---
        self.log_lbl = ttk.Label(self.main_container, text="Log di Esecuzione (Real-Time Console):", font=("Segoe UI", 10, "bold"), background="#f8fafc")
        self.log_lbl.pack(anchor=tk.W, pady=(5, 2))
        
        self.console = ScrolledText(self.main_container, font=self.font_console, bg="#0f172a", fg="#f8fafc", insertbackground="#ffffff", height=15)
        self.console.pack(fill=tk.BOTH, expand=True)
        self.console.insert(tk.END, "[INFO] GUI caricata con successo. Imposta i parametri e premi 'GENERA DATASET'.\n")
        self.console.configure(state="disabled")

    def update_mode_states(self, event=None):
        mode = self.mode_var.get()
        if "Offline" in mode:
            # Disabilita tutti gli input LLM
            self.provider_combo.configure(state="disabled")
            self.model_entry.configure(state="disabled")
            self.key_entry.configure(state="disabled")
            self.show_key_check.configure(state="disabled")
            
            # Sbiadisci le label
            self.provider_lbl.configure(foreground="#94a3b8")
            self.model_lbl.configure(foreground="#94a3b8")
            self.key_lbl.configure(foreground="#94a3b8")
            self.key_help_lbl.configure(foreground="#cbd5e1")
        else:
            # Abilita tutti gli input LLM
            self.provider_combo.configure(state="readonly")
            self.model_entry.configure(state="normal")
            self.key_entry.configure(state="normal")
            self.show_key_check.configure(state="normal")
            
            # Colore normale
            self.provider_lbl.configure(foreground="#0f172a")
            self.model_lbl.configure(foreground="#0f172a")
            self.key_lbl.configure(foreground="#0f172a")
            self.key_help_lbl.configure(foreground="#64748b")

    def on_provider_changed(self, event=None):
        provider = self.provider_var.get().lower()
        if provider in DEFAULT_MODELS:
            self.model_var.set(DEFAULT_MODELS[provider])

    def toggle_key_visibility(self):
        if self.show_key_var.get():
            self.key_entry.configure(show="")
        else:
            self.key_entry.configure(show="*")

    def browse_output_file(self):
        initial_file = self.output_var.get()
        initial_dir = os.path.dirname(initial_file) if initial_file else ""
        
        file_path = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            title="Salva Dataset Clinico Sintetico",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if file_path:
            self.output_var.set(os.path.abspath(file_path))

    def log(self, text):
        self.console.configure(state="normal")
        self.console.insert(tk.END, text)
        self.console.see(tk.END)
        self.console.configure(state="disabled")

    def open_output_folder_btn_state(self, enabled):
        if enabled:
            self.open_folder_btn.configure(state="normal", bg="#cbd5e1")
        else:
            self.open_folder_btn.configure(state="disabled", bg="#e2e8f0")

    def open_output_folder(self):
        output_file = self.output_var.get()
        if not output_file:
            return
        
        folder = os.path.dirname(os.path.abspath(output_file))
        if os.path.exists(folder):
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        else:
            messagebox.showerror("Errore", f"La cartella di output non esiste: {folder}")

    def start_generation(self):
        if self.is_generating:
            # Pulsante funziona come "Interrompi" se sta già generando
            self.stop_generation()
            return
            
        # Validazione minima
        try:
            count = int(self.count_var.get())
            if count <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Errore di Validazione", "Il numero di casi da generare deve essere un intero positivo superiore a 0.")
            return
            
        output_path = self.output_var.get().strip()
        if not output_path:
            messagebox.showerror("Errore di Validazione", "Specifica un percorso valido per il file di output.")
            return
            
        # Modalità ed eventuali credenziali
        mode = "offline" if "Offline" in self.mode_var.get() else "llm"
        provider = self.provider_var.get().lower()
        model = self.model_var.get().strip()
        api_key = self.key_var.get().strip()
        
        # Conferma se online
        if mode == "llm" and not api_key:
            env_var = f"{provider.upper()}_API_KEY"
            if not os.environ.get(env_var):
                ans = messagebox.askyesno(
                    "Attenzione", 
                    f"Non hai inserito alcuna API Key per {provider.capitalize()} e la variabile d'ambiente '{env_var}' "
                    "non sembra essere configurata.\nVuoi comunque tentare l'avvio?",
                    icon="warning"
                )
                if not ans:
                    return

        # Setup GUI in stato "Generazione in corso..."
        self.is_generating = True
        self.generate_btn.configure(text="🛑 INTERROMPI", bg="#dc2626", activebackground="#b91c1c")
        self.open_output_folder_btn_state(False)
        
        # Pulisci console
        self.console.configure(state="normal")
        self.console.delete("1.0", tk.END)
        self.console.configure(state="disabled")
        
        self.log(f"[INFO] Avvio processo di generazione...\n")
        self.log(f"[INFO] Parametri: Casi={count}, Modalità={mode.upper()}\n")
        if mode == "llm":
            self.log(f"[INFO] Configurazione LLM: Provider={provider.upper()}, Modello={model or 'Default'}\n")
        self.log(f"[INFO] File di Output: {output_path}\n")
        self.log("-" * 60 + "\n")
        
        # Lancio Thread di generazione per evitare blocco GUI
        self.generation_thread = threading.Thread(
            target=self.run_generation_process, 
            args=(count, mode, provider, model, api_key, output_path),
            daemon=True
        )
        self.generation_thread.start()

    def run_generation_process(self, count, mode, provider, model, api_key, output_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Costruzione argomenti comando subprocess
        cmd = [
            sys.executable, 
            "generate_dataset.py", 
            "--count", str(count),
            "--mode", mode,
            "--output", output_path
        ]
        
        if mode == "llm":
            cmd += ["--provider", provider]
            if model:
                cmd += ["--model", model]
            if api_key:
                cmd += ["--api-key", api_key]
                
        # Prepariamo l'ambiente (per ereditare path e variabili)
        env = os.environ.copy()
        
        try:
            # Avvia il processo in background nascondendo la finestra cmd su Windows
            self.process = subprocess.Popen(
                cmd,
                cwd=script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Leggi in real-time l'output linea per linea
            for line in iter(self.process.stdout.readline, ""):
                # Invia l'aggiornamento alla console GUI in modo thread-safe
                self.after(0, lambda l=line: self.log(l))
                
            self.process.stdout.close()
            return_code = self.process.wait()
            
            # Completato
            self.after(0, lambda: self.on_generation_complete(return_code))
            
        except Exception as e:
            self.after(0, lambda err=e: self.log(f"\n[ERRORE CRITICO] Errore di esecuzione del sottoprocesso: {err}\n"))
            self.after(0, lambda: self.on_generation_complete(-1))

    def on_generation_complete(self, return_code):
        self.is_generating = False
        self.generate_btn.configure(text="🚀 GENERA DATASET", bg="#0284c7", activebackground="#0369a1")
        
        self.log("-" * 60 + "\n")
        if return_code == 0:
            self.log(f"[SUCCESS] Generazione completata con successo! Codice di uscita: {return_code}\n")
            self.open_output_folder_btn_state(True)
            messagebox.showinfo("Successo", "Dataset Clinico Sintetico generato con successo!")
        elif return_code == -9 or return_code == 15 or return_code == 3221225786: # Annullato manualmente
            self.log(f"[INFO] Processo interrotto dall'utente.\n")
            self.open_output_folder_btn_state(False)
            messagebox.showwarning("Interrotto", "Il processo di generazione è stato interrotto.")
        else:
            self.log(f"[ERRORE] Il processo è terminato con errori (Codice uscita: {return_code}).\n")
            self.open_output_folder_btn_state(False)
            messagebox.showerror("Errore", f"Errore durante la generazione del dataset. Controlla il log di console.")

    def stop_generation(self):
        if not self.is_generating or not self.process:
            return
            
        ans = messagebox.askyesno("Conferma", "Sei sicuro di voler interrompere il processo di generazione in corso?")
        if ans:
            self.log("\n[INFO] Interruzione del processo in corso richiesta...\n")
            try:
                if sys.platform == "win32":
                    # Forza la terminazione pulita su Windows
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    self.process.terminate()
            except Exception as e:
                self.log(f"[ERRORE] Impossibile terminare il processo: {e}\n")

if __name__ == "__main__":
    app = DatasetGeneratorGUI()
    app.mainloop()
