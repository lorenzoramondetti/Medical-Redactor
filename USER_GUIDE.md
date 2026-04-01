# 🏥 Medical Redactor - Usage and USB Installation Guide

Welcome to **Medical Redactor**, the portable and secure solution for anonymizing clinical documents and laboratory data. This guide will walk you through preparing the USB drive and using the software down to exporting the redacted files.

---

## 💾 Part 1: Setting up the USB Drive (Portable Installation)

The program is designed to travel entirely within a single folder on your USB drive (e.g., `E:\Medical_Redactor`), without requiring any installation on the hospital computer.

### Setup Steps:
1. **Download the Software:** Download the source code (or the pre-compiled release) and extract it into an empty folder on your USB drive (e.g., `F:\Medical_Redactor`).
2. **Integrated Python Environment:** If you didn't download a pre-packaged version, you will need to place an "Embeddable" Python distribution inside the folder (e.g., in `F:\Medical_Redactor\python\`). Make sure to install the necessary libraries (use `install_dependencies.bat`).
3. **Artificial Intelligence Models:** The program will automatically download the specialized `gliner_multi_pii-v1` NER model upon its first execution on an internet-connected computer and cache it inside the `models/` folder. Subsequent executions on isolated hospital computers will run entirely offline.
4. **Launch:** To start the program on any Windows PC, simply double-click the `start_portable.bat` file. A black window (the engine) will open up, followed immediately by your web browser displaying the application interface. No traces will be left on the host computer.

---

## 🛡️ Part 2: Security and the "One-Way Valve"

When you are at the hospital, **you must never save the original, unredacted PDFs (with clear patient names) directly to your USB drive**, otherwise you compromise privacy in the event the USB drive is lost or stolen.

To prevent this, the software uses a Valve system:
1. In the left sidebar, in Settings, you will find the Security (One-Way Valve) section. Click the folder button (Select Local Hospital Folder) and choose a temporary, secure path on the hospital computer's hard drive (e.g., `C:\Temp\Redactor`).
2. The program will temporarily move the original files from the PC's Desktop into this *secure* `C:\` folder, instantly renaming them with indecipherable alphanumeric codes (UUIDs) so that the pending files are no longer traceable to patients by name.
3. The software will process the files from `C:\` and write the "clean" PDFs directly into the `output_pdf` folder **on your USB drive**.

*This way, sensitive data never touches the memory of the USB drive!*

---

## 👨‍⚕️ Part 3: How to Use the Application (The Workflow)

### Step 1: The Acquisition Wizard
When you launch the application, you will begin in the "Patient Acquisition Wizard".
- Enter the number of patients you want to process today.
- **Pre-emptive Memory Management (NEW):** You can now expand the "Manage Memory" section at the top of the wizard to configure your presets (like Provinces or Medical Roles) *before* the AI analysis starts.
- For each patient, drag and drop the **Clinical Record** PDFs (free-text descriptions) into the left box, and the **Laboratory Data** PDFs (tables, machine printouts) into the right box.
- Click **Next**. Repeat the operation. The system will instantly assign a unique, anonymous identification code to each patient.

### Step 2: AI-Powered Analysis
Once all patients are imported, click **"Start AI Analysis"**.
The built-in AI will scan the documents and autonomously identify sensitive data, including Tax Codes, Addresses, Emails, Proper Names, and Dates. 
- *Note on Laboratory Data:* To preserve information useful for research, the AI keeps exam dates visible in Laboratory Data documents, redacting only birth dates (e.g., "Born on 10/10/1980").

### Step 3: Interactive Review
After the analysis is complete, the PDFs will be displayed with red bounding boxes over any detected sensitive data. In this phase, you have total control to refine the results:
- **Manage Memory (Advanced):** Click the "Manage Memory" expander in the top bar to access the specialized dashboard:
    - **Presets**: Use "Quick-Toggle" buttons to instantly add/remove common hospital terminology (e.g., medical roles, departments, units) from the **Blacklist** (Ignore) or PII patterns (e.g., all 110 Italian Provinces) from the **Whitelist** (Redact).
    - **Search & Metrics**: Locate specific terms in your memory using the search bar and see total item counts.
    - **Granular Control**: Manage terms individually using the 🗑️ icon next to each word.
- **Manual Graphical Corrections**: If you spot an element the AI can't read as text (like a hospital logo or a handwritten signature), simply click and drag your mouse to draw a red rectangle over the area. Thanks to the "Apply to All" checkbox (active by default), this redaction will propagate to all pages.
- **Navigation:** Use the Left/Right Arrow Keys on your keyboard to comfortably flip through the file.

If your Incognito Session is turned OFF, any changes you make in the editor or the Memory Manager are saved to your global profile, automatically applying your preferences to future documents.

### Step 4: Secure Export
When a PDF looks perfect, click **Save and Export Redacted PDF**.
The obscured file will be safely deposited onto your USB drive (in the `output_pdf` folder), permanently renamed (e.g., `Cartella_Clinica_A84B9F.pdf`), without altering the visual quality, but the underlying text will be electronically incinerated to thwart any copy/paste recovery techniques.

---

## 🛠️ Manual and Incognito Modes

The options in the sidebar allow you to toggle:
- **Manual Mode (No AI):** Completely turns off the GLiNER inference model. The program will only eliminate recognizable formats (Emails, Phones, exact Dates via "Regex Rules") plus any words you manually teach it. Ideal for slow and underpowered hospital computers.
- **Incognito Session:** You can check "Do not save RAM to file". Upon exiting the program, the words in your personal dictionary and your corrections will be permanently lost. The program will leave no residual traces of the corrected names on the USB drive's Json log. Use this in highly restrictive environments.

<br><br><br>

---
---

# 🏥 Medical Redactor - Guida all'Uso e Installazione USB

Benvenuto nel **Medical Redactor**, la soluzione portatile e sicura per l'anonimizzazione dei documenti clinici e dei dati di laboratorio. Questa guida ti accompagnerà dalla preparazione della chiavetta USB fino all'esportazione dei file oscurati.

---

## 💾 Parte 1: Configurazione della Chiavetta USB (Installazione Portatile)

Il programma è progettato per risiedere interamente all'interno di una singola cartella sulla tua chiavetta USB (es. `E:\Medical_Redactor`), senza richiedere alcuna installazione sul computer dell'ospedale.

### Passaggi per la configurazione:
1. **Scarica il Software:** Scarica il codice sorgente (o la release pre-compilata) e scompattalo in una cartella vuota sulla tua chiavetta USB (es. `F:\Medical_Redactor`).
2. **Ambiente Python Integrato:** Se non hai scaricato una versione pre-confezionata, dovrai inserire una distribuzione di Python "Embeddable" all'interno della cartella (es. in `F:\Medical_Redactor\python\`). Assicurati di installare le librerie necessarie (usa `install_dependencies.bat`).
3. **Modelli di Intelligenza Artificiale:** Il programma scaricherà automaticamente il modello specializzato `gliner_multi_pii-v1` NER al suo primo avvio su un computer connesso a Internet e lo salverà nella cartella `models/`. Le successive esecuzioni sui computer isolati dell'ospedale avverranno interamente offline.
4. **Avvio:** Per avviare il programma su qualsiasi PC Windows, fai semplicemente doppio clic sul file `start_portable.bat`. Si aprirà una finestra nera (il motore), seguita immediatamente dal tuo browser web che mostrerà l'interfaccia dell'applicazione. Nessuna traccia rimarrà sul computer ospite.

---

## 🛡️ Parte 2: Sicurezza e la "One-Way Valve" (Valvola di Non-Ritorno)

Quando sei in ospedale, **non devi mai salvare i PDF originali non oscurati (con i nomi dei pazienti in chiaro) direttamente sulla tua chiavetta USB**, altrimenti comprometti la privacy in caso di smarrimento o furto della chiavetta.

Per evitare ciò, il software utilizza un sistema a Valvola:
1. Nella barra laterale sinistra, in Impostazioni, troverai la sezione Sicurezza (One-Way Valve). Clicca sul pulsante della cartella (Seleziona Cartella Locale Ospedale) e scegli un percorso temporaneo e sicuro sul disco rigido del computer dell'ospedale (es. `C:\Temp\Redactor`).
2. Il programma sposterà temporaneamente i file originali dal Desktop del PC in questa cartella *sicura* `C:\`, rinominandoli istantaneamente con codici alfanumerici indecifrabili (UUID) in modo che i file in attesa non siano più riconducibili ai pazienti per nome.
3. Il software elaborerà i file da `C:\` e scriverà i PDF "puliti" direttamente nella cartella `output_pdf` **sulla tua chiavetta USB**.

*In questo modo, i dati sensibili non toccano mai la memoria della chiavetta USB!*

---

## 👨‍⚕️ Parte 3: Come usare l'Applicazione (Il Flusso di Lavoro)

### Step 1: Il Wizard di Acquisizione
Al lancio dell'applicazione, inizierai nel "Patient Acquisition Wizard".
- Inserisci il numero di pazienti che vuoi processare oggi.
- **Gestione Memoria Pre-analisi (NOVITÀ):** Ora puoi espandere la sezione "Manage Memory" in alto nel wizard per configurare i preset (come Province o Ruoli Medici) *prima* che inizi l'analisi IA.
- Per ogni paziente, trascina i PDF della **Cartella Clinica** (descrizioni a testo libero) nel riquadro di sinistra, e i PDF dei **Dati di Laboratorio** (tabelle, stampe di macchinari) nel riquadro di destra.
- Clicca su **Avanti**. Ripeti l'operazione. Il sistema assegnerà istantaneamente un codice identificativo unico e anonimo a ogni paziente.

### Step 2: Analisi basata su IA
Una volta importati tutti i pazienti, clicca su **"Start AI Analysis"**.
L'IA integrata scansionerà i documenti e identificherà autonomamente i dati sensibili, inclusi Codici Fiscali, Indirizzi, Email, Nomi Propri e Date. 
- *Nota sui Dati di Laboratorio:* Per preservare le informazioni utili alla ricerca, l'IA mantiene visibili le date degli esami nei documenti di Laboratorio, oscurando solo le date di nascita (es. "Nato il 10/10/1980").

### Step 3: Revisione Interattiva
Al termine dell'analisi, i PDF verranno visualizzati con rettangoli rossi sopra ogni dato sensibile rilevato. In questa fase, hai il controllo totale per rifinire i risultati:
- **Gestione Memoria (Avanzata):** Clicca sull'espansore "Manage Memory" nella barra superiore per accedere al pannello di controllo dedicato:
    - **Preset**: Usa i pulsanti "Quick-Toggle" per aggiungere/rimuovere istantaneamente intere categorie (es. sigle di tutte le 110 province, ruoli medici, reparti, unità di misura) dalla **Blacklist** (Ignora) o dalla **Whitelist** (Redigi).
    - **Ricerca e Metriche**: Trova velocemente termini specifici usando la barra di ricerca e visualizza il conteggio totale degli elementi.
    - **Controllo Granulare**: Gestisci i termini singolarmente usando l'icona 🗑️ accanto a ogni parola.
- **Correzioni Grafiche Manuali:** Se noti un elemento che l'IA non può leggere come testo (come un logo ospedaliero o una firma autografa), clicca e trascina il mouse per disegnare un rettangolo rosso sull'area. Grazie alla casella "Applica a tutti" (attiva di default), questa correzione si propagherà a tutte le pagine.
- **Navigazione:** Usa le frecce Destra/Sinistra sulla tastiera per sfogliare comodamente il file.

Se la Sessione in Incognito è disattivata (OFF), ogni modifica effettuata nell'editor o nel Memory Manager viene salvata nel tuo profilo globale, applicando automaticamente le tue preferenze ai documenti futuri.

### Step 4: Esportazione Sicura
Quando un PDF appare perfetto, clicca su **Salva ed Esporta PDF Redatto**.
Il file oscurato verrà depositato in sicurezza sulla tua chiavetta USB (nella cartella `output_pdf`), rinominato definitivamente (es. `Cartella_Clinica_A84B9F.pdf`), senza alterare la qualità visiva, ma il testo sottostante sarà incenerito elettronicamente per vanificare qualsiasi tecnica di recupero tramite copia/incolla.

---

## 🛠️ Modalità Manuale e Sessioni in Incognito

Le opzioni nella barra laterale ti permettono di attivare:
- **Manual Mode (No AI):** Disattiva completamente il modello di inferenza GLiNER. Il programma eliminerà solo i formati riconoscibili (Email, Telefoni, Date esatte tramite "Regole Regex") oltre a qualsiasi parola tu gli insegni manualmente. Ideale per computer ospedalieri lenti o poco potenti.
- **Sessione in Incognito:** Puoi spuntare "Non salvare la RAM su file". All'uscita dal programma, le parole nel tuo dizionario personale e le tue correzioni andranno perse definitivamente. Il programma non lascerà tracce residue dei nomi corretti nel log Json della chiavetta USB. Usalo in ambienti altamente restrittivi.
