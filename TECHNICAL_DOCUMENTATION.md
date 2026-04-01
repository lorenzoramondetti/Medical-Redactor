# Technical and Architectural Documentation - Medical Redactor

This document illustrates the technical architecture, UI/UX choices, and engineering solutions adopted to develop **Medical Redactor**, a software specifically designed for the secure anonymization of sensitive medical data in critical hospital environments.

---

## 1. System Architecture and Security (Privacy-First)

The main challenge of the project was to ensure the total security of patient data (PHI/PII), preventing any information leakage, while operating on uncontrolled or potentially unstable hardware (USB sticks) in hospital environments.

### 1.1 The "One-Way Valve" Concept
To prevent unredacted data from remaining on removable media, we designed a strictly separated three-stage architecture:
1.  **Local Staging (`C:\`)**: The acquisition of original PDFs occurs in a secure folder on the hospital's local hard drive (e.g., `Staging`). Files are *never* copied directly to the USB stick in this phase.
2.  **Standardized Renaming and Structuring (UUID)**: As soon as they are acquired, a patient's files are immediately renamed with the same randomly generated UUID (e.g., `3153861F_Lab.pdf`, `3153861F_Clinica.pdf`) and placed in an organized parent subfolder (e.g., `Paziente_3153861F`). This approach offers a double advantage:
    *   It instantly breaks the associative chain (the file "Rossi_Mario_Exami.pdf" ceases to exist).
    *   It creates a fixed and predictable structure, ideal for allowing automated sending or insertion into the institute's subsequent surveillance pipeline.
3.  **Removable Output (`E:\`)**: Only the final document, processed and in organized form, is exported to the USB stick (inside the `output_pdf/Paziente_UUID/` folder).

### 1.2 Zero-Trace Execution & Portability
The required paradigm was "Plug & Play" on limited corporate Windows machines.
*   **Embedded Python**: The program does not require installation and has no dependencies on administrator permissions.
*   **No Cache Residue**: The application suppresses the generation and writing of bytecode via `sys.dont_write_bytecode = True` and `os.environ["PYTHONDONTWRITEBYTECODE"]`.
*   **Incognito Session**: If activated in the `settings.json` file, updates to the memory dictionary (`global_memory.json`) in RAM are never persisted to disk upon closure.

---

## 2. Hybrid Redaction Paradigm: "Human in the Loop"

Fully automated tools often return false negatives or positives in the medical field, especially with scanned PDFs or non-standard layouts. The architecture resolves this problem by structuring an operator validation flow.

### 2.1 Multiple Inference Engine
The text extraction engine combines three levels of hierarchical analysis to maximize recall:
1.  **Hard-Coded Rules (Optimized Regex for Italy)**: Specific for Fiscal Codes, hospital clinical record numbers (with and without prefixes), European/Italian date formats, and common medical abbreviations (A.O., Dott.).
2.  **Structured Global Memory**: Maintains categorized whitelists and blacklists. The system now features a professional management interface with **Quick-Toggle Presets** (Italian provinces, medical roles, clinical labels, anatomical terms) to jumpstart the redaction process with high precision.
3.  **Local SLM (Small Language Model - GLiNER)**: The local `urchade/gliner_multi_pii-v1` model intervenes to extract complex nominal entities, working offline (without sending data to cloud APIs, which would violate GDPR/HIPAA).

### 2.2 Semantic Management of Dates (Reports Vs Clinical)
A crucial challenge was discerning the "type" of document. In hematological or serological reports (Laboratory), hiding the date or time of the sample collection invalidates the scientific data. The Regex engine was split:
*   If the operator sets **Structured Data**, the Regex scans only dates near the words "Date of Birth".
*   If the operator sets **Clinical Documents**, the Regex hide anything that resembles a date in a "greedy" way to prevent identification of hospital stays.

---

## 3. UI / UX: Streamlit and Work Optimization

The User Experience was designed to reduce the *mouse-travel* of the operator who must validate dozens of pages per day.

### 3.1 Interactive PDF Rendering
The challenge was to display PDFs and allow corrections without losing the native textual formatting (the output file must have the redacted text selectable or replaced by "[REDACTED]", it must not be a grainy rasterization).
*   **Resolution**: The `fitz` library (PyMuPDF) renders each page in RAM as a PNG with high DPI for the UI.
*   **Drawing Tool**: By modifying the `streamlit-drawable-canvas` Vue.js element, we created a superimposed transparent layer on the PNG. The operator can draw physical rectangles over hospital logos or barcodes, something the textual engine alone could never do (challenge: AI does not "see" OCR barcodes). The pixels underneath the operator's drawings are then deleted in the PDF via coordinates.

### 3.2 Structured Memory Management
Medical documents often rely on repetitive headers/footers and standard clinical boilerplate.
*   **Architectural Solution**: The UI includes a sophisticated **Memory Manager** with:
    *   **Search & Metrics**: Real-time filtering and item counts for thousands of terms.
    *   **Preset Toggles**: Batch-addition of common medical noise (units, roles, departments) to the Blacklist, or PII patterns (provinces) to the Whitelist.
    *   **Individual Removal**: Granular control over learned terms with one-click deletion.
*   **Automatic Propagation**: When the operator validates a term, the logic updates the memory and retroactively applies the change to all subsequent pages, reducing manual work by up to 90%.

### 3.3 Multi-Patient Management and Sequential Wizard
The UX is divided into two modes:
1.  **Acquisition Wizard (Dashboard)**: Using dynamic Streamlit components (bulk Drag and Drop), the user can pour in the entire work shift. **Pre-emptive Memory Management** is available here via an expander, allowing the setup of presets and custom dictionaries before analysis begins.
2.  **Page-by-Page Focus**: A wide column for the preview (PNG) and a narrow column for controls (Checkboxes) with a compressed sidebar, minimizing vertical scroll and distraction.

---

## 4. Test and Quality Assurance (QA)

To ensure software reliability in production, we have implemented an automated testing suite that covers four fundamental pillars:

### 4.1 Unit Testing
Using the `unittest` framework, we verify core functions in isolation:
*   **UUID Anonymization**: Verifies that file renaming is compliant (8 hex characters, uppercase) and does not collide.
*   **Regex Engine**: We test the extraction of CF, doctor names, and hospital structures on messy text strings.
*   **Date Logic**: We verify that the distinction between "Clinical" and "Structured" data works as expected.

### 4.2 Integrity Testing (The Incinerator)
This test (`tests/test_integrity.py`) is the most critical for security:
*   Generates a PDF with "decoy" sensitive data.
*   Runs the redaction procedure.
*   **Bitstream Verification**: Attempts to re-extract data from the final PDF via text search and OCR. The test passes only if the occurrences found are **zero**, ensuring that data has been physically removed and not just covered.

### 4.3 Security Testing (One-Way Valve Architecture)
The `tests/test_security.py` test verifies that:
*   **Incognito Isolation**: In ephemeral mode, no learned data is ever written to the `global_memory.json` file.
*   **Staging/USB Separation**: Verifies that original files (not obscured) remain confined to the `C:\` drive and never touch the USB stick's output folder.

### 4.4 Performance and Stress Testing
The `tests/test_performance.py` test evaluates stability under load:
*   **Bulk Processing**: Simulates iterative processing of 50+ file iterations verify that there are no degrading slowdowns.
*   **Memory Leak**: Verifies that PDF objects (`PyMuPDF`) are closed correctly and RAM is released after each operation.

### 4.5 User Acceptance Testing (UAT) Protocol
In addition to automated tests, the project includes a **[UAT Protocol](file:///c:/Users/loren/Desktop/Medical%20Redactor/UAT_PROTOCOL.md)**. This document guides the human operator in the final verification of critical features, ensuring that the software meets the practical needs of the clinician and the requirements of the Data Protection Officer (DPO).

---

## 5. Limits Addressed and Current Mitigations

-   **Non-searchable text vs OCR text**: If an input PDF is a purely rasterized photocopy (without a text layer underneath), Regex/LLM PII extraction fails. Current mitigation: The architecture falls back to "Manual Drawing" via the interactive layer.
-   **Hardware Constraints (USB)**: Loading the PyTorch framework into memory from a USB 2.0/3.0 connection generates high warmup (program startup) times. Mitigation: Total deactivation of PII scanning until entering the initial redaction view of the first patient, keeping the initial acquisition asynchronous and fast.

<br>
<hr>
<br>

# Documentazione Tecnica e Architetturale - Medical Redactor

Questo documento illustra l'architettura tecnica, le scelte di UI/UX e le soluzioni ingegneristiche adottate per sviluppare **Medical Redactor**, un software progettato specificamente per l'anonimizzazione sicura di dati medici sensibili in ambienti ospedalieri critici.

---

## 1. Architettura di Sistema e Sicurezza (Privacy-First)

La sfida principale del progetto è stata garantire la totale sicurezza dei dati dei pazienti (PHI/PII), impedendo qualsiasi fuga di informazioni, pur operando su hardware non controllato o potenzialmente instabile (chiavette USB) in ambienti ospedalieri.

### 1.1 Il concetto di "One-Way Valve" (Valvola a Singola Via)
Per prevenire la permanenza di dati in chiaro su supporti rimovibili, abbiamo progettato un'architettura a tre stadi rigorosamente separati:
1.  **Staging Locale (`C:\`)**: L'acquisizione dei PDF originali avviene in una cartella sicura sul disco fisso locale dell'ospedale (es. `Staging`). I file non vengono *mai* copiati direttamente sulla chiavetta in questa fase.
2.  **Ridenominazione e Strutturazione Standard (UUID)**: Appena acquisiti, i file di un paziente vengono immediatamente rinominati con uno stesso UUID generato casualmente (es. `3153861F_Lab.pdf`, `3153861F_Clinica.pdf`) e inseriti in una sotto-cartella genitore organizzata (es. `Paziente_3153861F`). Questo approccio offre un duplice vantaggio: 
    *   Rompe istantaneamente la catena associativa (il file "Rossi_Mario_Esami.pdf" cessa di esistere). 
    *   Crea una struttura fissa e predicibile, ideale per permettere l'invio o l'inserimento automatizzato dei file nella successiva pipeline di sorveglianza dell'istituto.
3.  **Output Removibile (`E:\`)**: Solo il documento finale, processato e in forma organizzata, viene esportato sulla chiavetta USB (dentro la cartella `output_pdf/Paziente_UUID/`).

### 1.2 Zero-Trace Execution & Portability (Esecuzione senza tracce)
Il paradigma richiesto era il "Plug & Play" su macchine Windows aziendali limitate.
*   **Embedded Python**: Il programma non richiede installazione e non possiede dipendenze su permessi di amministratore.
*   **Nessun Residuo Cache**: L'applicazione sopprime la generazione e la scrittura di bytecode tramite `sys.dont_write_bytecode = True` e `os.environ["PYTHONDONTWRITEBYTECODE"]`.
*   **Modalità Effimera (Incognito Session)**: Se attivata dal file `settings.json`, l'aggiornamento del dizionario delle memorie (`global_memory.json`) in RAM non viene mai persistito sul disco alla chiusura.

---

## 2. Paradigma di Redazione Ibrido: "Human in the Loop"

Strumenti completamente automatizzati restituiscono spesso falsi negativi o positivi in ambito medico, specialmente con PDF scansionati o impaginati in modo non standard. L'architettura risolve questo problema strutturando un flusso di convalida operatore.

### 2.1 Motore di Inferenza Multiplo
Il motore di estrazione del testo combina tre livelli di analisi gerarchica per massimizzare il richiamo (Recall):
1.  **Regole Hard-Coded (Regex Ottimizzate per l'Italia)**: Specifiche per Codici Fiscali, numeri di cartella clinica ospedalieri (con e senza prefissi), formati di date europei/italiani e abbreviazioni mediche comuni (A.O., Dott.).
2.  **Structured Global Memory**: Mantiene whitelists e blacklists categorizzate. Il sistema dispone ora di un'interfaccia di gestione professionale con **Preset Quick-Toggle** (sigle province, ruoli medici, etichette cliniche, termini anatomici) per avviare il processo di redazione con estrema precisione.
3.  **Local SLM (Small Language Model - GLiNER)**: Il modello locale `urchade/gliner_multi_pii-v1` interviene per estrarre entità nominali complesse, lavorando offline (senza inviare dati a API cloud, il che violerebbe il GDPR/HIPAA).

### 2.2 Gestione Semantica delle Date (Referti Vs Clinico)
Una sfida cruciale è stata discernere il "tipo" di documento. Nei referti ematologici o sierologici (Laboratorio), occultare la data o l'ora del prelievo invalida il dato scientifico. Il motore Regex è stato diviso:
*   Se l'operatore imposta *Dati Strutturati*, il Regex scansiona solo le date vicine alla parola "Data di Nascita".
*   Se l'operatore imposta *Documenti Clinici*, il Regex occulta in modo "greedy" qualsiasi cosa somigli a una data per prevenire l'identificazione di degenze.

---

## 3. UI / UX: Streamlit e Ottimizzazione del Lavoro

La User Experience è stata progettata per ridurre il *mouse-travel* dell'operatore che deve validare decine di pagine al giorno.

### 3.1 PDF Rendering Interattivo
La sfida era visualizzare PDF e permettere correzioni senza perdere la formattazione testuale nativa (il file di output deve avere il testo redatto selezionabile o sostituito da "[REDACTED]", non deve essere una rasterizzazione sgranata).
*   **Risoluzione**: La libreria `fitz` (PyMuPDF) renderizza in RAM ogni pagina come PNG con alta DPI per la UI.
*   **Drawing Tool**: Modificando l'elemento Vue.js `streamlit-drawable-canvas`, abbiamo creato un layer trasparente sovrapposto al PNG. L'operatore può disegnare rettangoli fisici su loghi degli ospedali o codici a barre, cosa che il motore testuale da solo non potrebbe mai fare (sfida: l'AI non "vede" i codici a barre OCR). I pixel sottostanti ai disegni dell'operatore vengono poi cancellati nel PDF tramite coordinate.

### 3.2 Gestione Strutturata della Memoria
I documenti medici presentano spesso intestazioni ripetitive e terminologia clinica standard.
*   **Soluzione Architetturale**: L'interfaccia integra un **Memory Manager** avanzato con:
    *   **Ricerca e Metriche**: Filtraggio in tempo reale e conteggio degli elementi per gestire migliaia di termini.
    *   **Toggle dei Preset**: Aggiunta massiva di "rumore" clinico comune (unità, ruoli, reparti) alla Blacklist, o pattern PII (province) alla Whitelist.
    *   **Rimozione Individuale**: Controllo granulare sui termini appresi con cancellazione in un click.
*   **Propagazione Automatica**: Quando l'operatore convalida un termine, la logica aggiorna la memoria e applica retroattivamente la modifica a tutte le pagine successive, riducendo il lavoro manuale fino al 90%.

### 3.3 Gestione Multi-Paziente e Wizard Sequenziale
La UX è divisa in due modalità:
1.  **Wizard di Acquisizione (Dashboard)**: Utilizzando componenti Streamlit dinamici (Drag and Drop in massa), l'utente può riversare l'intero turno di lavoro. La **Gestione della Memoria Pre-analisi** è disponibile qui tramite un expander, permettendo la configurazione di preset e dizionari prima dell'inizio dell'analisi.
2.  **Focus Pagina per Pagina**: Una colonna larga per l'anteprima (PNG) e una colonna stretta per i controlli (Checkboxes) con sidebar compressa, minimizzando lo scroll verticale e la distrazione.

---

## 4. Test e Garanzia di Qualità (QA)

Per garantire l'affidabilità del software in produzione, abbiamo implementato una suite di test automatizzati che copre quattro pilastri fondamentali:

### 4.1 Test di Unità (Unit Testing)
Utilizzando il framework `unittest`, verifichiamo isolatamente le funzioni core:
*   **Anonimizzazione UUID**: Verifica che la ridenominazione dei file sia conforme (8 caratteri hex, maiuscoli) e non collisioni.
*   **Motore Regex**: Testiamo l'estrazione di CF, nomi di medici e strutture ospedaliere su stringhe di testo sporche.
*   **Logica delle Date**: Verichiamo che la distinzione tra "Clinical" e "Structured" data funzioni come previsto.

### 4.2 Test di Integrità (L'Incenitore)
Questo test (`tests/test_integrity.py`) è il più critico per la sicurezza:
*   Generate un PDF con dati sensibili "esca".
*   Esegue la procedura di redazione.
*   **Verifica Bitstream**: Tenta di ri-estrarre i dati dal PDF finale tramite ricerca testuale e OCR. Il test passa solo se le occorrenze trovate sono pari a **zero**, garantendo che i dati siano stati fisicamente rimossi e non solo coperti.

### 4.3 Test di Sicurezza (Architettura One-Way Valve)
Il test `tests/test_security.py` verifica che:
*   **Isolamento Incognito**: In modalità effimera, nessun dato appreso venga mai scritto sul file `global_memory.json`.
*   **Separazione Staging/USB**: Verifica che i file originali (non oscurati) rimangano confinati nel disco `C:\` e non tocchino mai la cartella di output della chiavetta USB.

### 4.4 Test di Performance e Stress
Il test `tests/test_performance.py` valuta la stabilità sotto carico:
*   **Bulk Processing**: Simula l'elaborazione sequenziale di 50+ file per verificare che non ci siano rallentamenti degradanti.
*   **Memory Leak**: Verifica che gli oggetti PDF (`PyMuPDF`) vengano chiusi correttamente e la RAM venga rilasciata dopo ogni operazione.

### 4.5 Protocollo di Collaudo (UAT)
Oltre ai test automatizzati, il progetto include un **[Protocollo di Collaudo (UAT)](file:///c:/Users/loren/Desktop/Medical%20Redactor/UAT_PROTOCOL.md)**. Questo documento guida l'operatore umano nella verifica finale delle funzionalità critiche, garantendo che il software risponda alle esigenze pratiche del clinico e ai requisiti del Responsabile della Protezione dei Dati (DPO).

---

## 5. Limiti Affrontati e Mitigazioni Attuali

-   **Testo non ricercabile vs Testo OCR**: Se un PDF in ingresso è una fotocopia puramente rasterizzata (senza un text layer sotto), l'estrazione PII Regex/LLM fallisce. Mitigazione attuale: L'architettura ripiega sul "Manual Drawing" tramite layer interattivo.
-   **Hardware Constraints (USB)**: Il caricamento in memoria del PyTorch framework da una connessione USB 2.0/3.0 genera tempi di warmup (avvio del programma) elevati. Mitigazione: Disattivazione totale della scansione PII fino all'ingresso nella visualizzazione di redazione inziale del primo paziente, tenendo l'acquisizione iniziale asincrona e rapida.
