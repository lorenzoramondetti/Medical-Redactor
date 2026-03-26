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
1. Open the Advanced Settings (the gear icon) in the side menu.
2. Under **"Secure Hospital Staging Path"**, click the folder button and choose a temporary, secure path on the hospital computer's hard drive (e.g., `C:\Temp\Redactor`).
3. The program will temporarily move the original files from the PC's Desktop into this *secure* `C:\` folder, instantly renaming them with indecipherable alphanumeric codes (UUIDs) so that the pending files are no longer traceable to patients by name.
4. The software will process the files from `C:\` and write the "clean" PDFs directly into the `output_pdf` folder **on your USB drive**.

*This way, sensitive data never touches the metal of your USB drive!*

---

## 👨‍⚕️ Part 3: How to Use the Application (The Workflow)

### Step 1: The Acquisition Wizard
Upon startup, you will be greeted by the "Patient Acquisition Wizard".
- Enter the number of patients you wish to process today.
- For each patient, drag and drop the **Clinical Record** PDFs (free-text descriptions) into the first box, and the **Laboratory Data** PDFs (tables, machine printouts) into the second box.
- Click **Next**. Repeat the operation. The program will assign an instantly-generated anonymous identification code to each patient.

### Step 2: Automatic Analysis (Artificial Intelligence)
Once all patients are imported, click **"Start AI Analysis"**.
The program will read the text and autonomously identify Tax Codes, Addresses, Emails, Proper Names, and Dates. 
- *Note:* In documents labeled as "Laboratory Data", the AI will preserve exam dates (which are useful for research), redacting only the date of birth (e.g., "Born on 10/10/1980").

### Step 3: Interactive Review (UI)
After the automatic analysis finishes, the PDF will be displayed with black rectangles positioned wherever the AI found sensitive data. Here you have total control:
- **Remove a Redaction:** Did the AI censor a word by mistake? Click the `X` next to the name to "acquit" it. This term will instantly reappear in clear text on *all pages* of the document.
- **Add a Redaction (Textual):** Did the AI miss the term "Dr. Rossi"? Type it into the dedicated text field. The program will find it and erase it from *all pages* in a single action.
- **Graphical Micro-Corrections (Manual Rectangles):** Do you see a hospital logo or an illegible signature not recognized as text? No problem! Click the square icon in the bottom left of the PDF viewer and **draw a freehand red rectangle** over the area to hide. The rectangle will be applied and propagated to all pages (thanks to the "Apply to All" checkbox, active by default).
- Use the **Right/Left Arrow Keys** on your keyboard to comfortably browse through the file.

### Step 4: Exporting
When a PDF looks perfect, click **Save and Export Redacted PDF**.
The obscured file will be safely deposited onto your USB drive (in the `output_pdf` folder), permanently renamed (e.g., `Cartella_Clinica_A84B9F.pdf`), without altering the visual quality, but the underlying text will be electronically incinerated to thwart any copy/paste recovery techniques.

---

## 🛠️ Manual and Incognito Modes

The options in the sidebar allow you to toggle:
- **Manual Mode (No AI):** Completely turns off the GLiNER inference model. The program will only eliminate recognizable formats (Emails, Phones, exact Dates via "Regex Rules") plus any words you manually teach it. Ideal for slow and underpowered hospital computers.
- **Incognito Session:** By clicking the gear icon, you can check "Do not save RAM to file". Upon exiting the program, the words in your personal dictionary and your corrections will be permanently lost. The program will leave no residual traces of the corrected names on the USB drive's Json log. Use this in highly restrictive environments.

<br><br><br>

---
---

# 🏥 Medical Redactor - Guida all'Uso e Installazione USB

Benvenuto nel **Medical Redactor**, la soluzione portatile e sicura per l'anonimizzazione dei documenti clinici e dei dati di laboratorio. Questa guida ti accompagnerà dalla preparazione della chiavetta USB fino all'esportazione dei file oscurati.

---

## 💾 Parte 1: Creazione della Chiavetta USB (Installazione Portable)

Il programma è progettato per viaggiare tutto all'interno di una singola cartella sulla tua chiavetta USB (es. `E:\Medical_Redactor`), senza bisogno di installare nulla sul computer dell'ospedale.

### Passaggi per la preparazione:
1. **Scarica il Software:** Scarica il codice sorgente (o la release pre-compilata) e scompattalo in una cartella vuota sulla tua chiavetta USB (es. `F:\Medical_Redactor`).
2. **Ambiente Python Integrato:** Se non hai scaricato una versione pre-confezionata, dovrai inserire una distribuzione di Python "Embeddable" all'interno della cartella (es. in `F:\Medical_Redactor\python\`). Assicurati di aver installato le librerie necessarie (usa `install_dependencies.bat`).
3. **Modelli di Intelligenza Artificiale:** Al primissimo avvio (se connesso ad internet), il programma scaricherà automaticamente il modello specializzato `gliner_multi_pii-v1`, salvandolo in modo permanente nella cartella `models/` della chiavetta per tutti gli usi offline successivi in ospedale.
4. **Avvio:** Per far partire il programma su qualsiasi PC Windows, fai semplicemente doppio click sul file `start_portable.bat`. Si aprirà una finestra nera (il motore) e subito dopo il tuo browser web con l'interfaccia dell'applicazione. Nessuna traccia verrà lasciata sul computer ospite.

---

## 🛡️ Parte 2: Sicurezza e "One-Way Valve" (Valvola di Non-Ritorno)

Quando sei in ospedale, **non devi mai salvare i PDF originali (con i nomi in chiaro) direttamente sulla chiavetta USB**, altrimenti vanifichi la privacy in caso di smarrimento o furto della chiavetta.

Per questo, il software utilizza un sistema a Valvola:
1. Apri le Impostazioni Avanzate (l'ingranaggio) nel menu laterale.
2. Alla voce **"Staging sicura su PC" (Secure Hospital Staging Path)**, clicca il pulsante della cartella e scegli un percorso temporaneo e sicuro sul disco fisso del computer dell'ospedale (es. `C:\Temp\Redactor`).
3. Il programma sposterà temporaneamente i file originali dal Desktop del PC a questa cartella *sicura* `C:\`, rinominandoli immediatamente con codici alfanumerici indecifrabili (UUID) in modo che i file in attesa di essere epurati non abbiano nomi riconducibili ai pazienti.
4. Il software scansionerà la cartella in `C:\` e scriverà i PDF "puliti" direttamente nella cartella `output_pdf` **sulla tua chiavetta USB**.

*In questo modo, i dati sensibili non toccano mai il metallo della tua chiavetta!*

---

## 👨‍⚕️ Parte 3: Come utilizzare l'Applicazione (Il Workflow)

### Step 1: Il Wizard di Acquisizione
All'avvio, verrai accolto dal "Patient Acquisition Wizard".
- Inserisci il numero di pazienti che vuoi processare oggi.
- Per ogni paziente, trascina i PDF della **Cartella Clinica** (descrizioni a testo libero) nel primo riquadro, e i **Dati di Laboratorio** (tabelle, stampe di macchinari) nel secondo riquadro.
- Clicca **Avanti**. Ripeti l'operazione. Il programma attribuirà ad ogni paziente un codice identificativo anonimo generato istantaneamente.

### Step 2: Analisi Automatica (Intelligenza Artificiale)
Una volta importati tutti i pazienti, clicca su **"Start AI Analysis"**.
Il programma leggerà il testo, identificherà autonomamente Codici Fiscali, Indirizzi, Email, Nomi Propri e Date. 
- *Nota Bene:* Nei documenti etichettati come "Dati di Laboratorio", preserverà le date degli esami (utili per la ricerca), oscurando solo la data di nascita (es. "Nato il 10/10/1980").

### Step 3: Revisione Incrociata (UI Interattiva)
Finita l'analisi automatica, ti verrà mostrato il PDF con dei rettangoli neri posizionati dove l'IA ha trovato dati sensibili. Qui tu hai il controllo totale:
- **Togliere un Oscuramento:** L'IA ha censurato una parola per errore? Clicca sulla `X` accanto al nome per "assolverlo". Questo termine ricomparirà in chiaro su *tutte le pagine* del documento istantaneamente.
- **Aggiungere un Oscuramento (Testuale):** L'IA ha mancato il termine "Dott. Rossi"? Scrivilo nel campo di testo dedicato. Il programma lo troverà e lo cancellerà su *tutte le pagine* in un colpo solo.
- **Micro-correzioni Grafiche (Rettangoli Manuali):** Noti un logo dell'ospedale o una firma illegibile non riconosciuta come testo? Nessun problema! Clicca l'icona del quadrato in basso a sinistra nel visore PDF e **disegna a mano libera** un rettangolo rosso sopra la zona da nascondere. Il rettangolo verrà applicato e propagato a tutte le pagine (grazie alla spunta attiva di default).
- Usa le **Frecce Direzionali Destra/Sinistra** della tastiera per sfogliare comodamente il fascicolo.

### Step 4: Esportazione
Quando un PDF è visivamente perfetto, clicca su **Salva ed Esporta PDF Redatto**.
Il file oscurato verrà depositato al sicuro sulla tua chiavetta USB (nella cartella `output_pdf`), rinominato definitivamente (es. `Cartella_Clinica_A84B9F.pdf`), senza alterarne la qualità visiva, ma i testi sottostanti saranno inceneriti elettronicamente per scongiurare tecniche di recupero con copia/incolla.

---

## 🛠️ Modalità Manuale e Incognito

Le opzioni nella barra laterale ti permettono di attivare la:
- **Manual Mode (No AI):** Spegne completamente il modello di Named Entity Recognition GLiNER. Il programma eliminerà solo formati riconoscibili (Email, Telefoni, Date esatte tramite "Regole Regex") più le parole che gli insegnerai tu manualmente. Ideale per computer ospedalieri lenti e poco potenti.
- **Incognito Session:** Cliccando l'ingranaggio, puoi spuntare "Non salvare la RAM su file". All'uscita del programma, le parole del tuo dizionario personale e le correzioni andranno permanentemente perse. Il programma non lascerà tracce residuali dei nomi corretti sul log Json della chiavetta. Usalo in ambienti ostili.
