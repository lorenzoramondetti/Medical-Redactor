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
2.  **Global Memory (Dizionario Dinamico)**: Mantiene whitelists e blacklists. Se il sistema ha già visto un nome falso-positivo, questo viene ignorato; se ha visto un paziente raro, lo rintraccia sempre tramite ricerca testuale pura esatta.
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

### 3.2 Propagazione Automatica delle Correzioni (Ottimizzazione)
I documenti medici presentano l'anagrafica del paziente ripetuta in tutte le intestazioni a piè di pagina (header/footer). Per un PDF di 100 pagine, l'operatore impazzirebbe.
*   **Soluzione Architetturale**: L'interfaccia ha un meccanismo "Seleziona/Deseleziona parola Trovata". Se l'operatore seleziona la casella "Correggi e Propaga", la logica aggiorna la `Global Memory`. Negli stadi successivi, quando vengono renderizzate le pagine dalla 2 alla 100, la AI "non farà più errori" e i nomi saranno pre-selezionati per l'occultamento. L'operatore dovrà fare solo click su "Avanti" per 99 pagine consecutive.

### 3.3 Gestione Multi-Paziente e Wizard Sequenziale
La UX è divisa in due modalità:
1.  **Wizard di Acquisizione (Dashboard)**: Utilizzando componenti Streamlit dinamici (Drag and Drop in massa), l'utente può riversare l'intero turno di lavoro e visualizzare bar-chart di sintesi o code di calcolo.
2.  **Focus Pagina per Pagina**: Una colonna larga per l'anteprima (PNG) e una colonna stretta per i controlli (Checkboxes) con sidebar compressa, minimizzando lo scroll verticale e la distrazione.

---

## 4. Limiti Affrontati e Mitigazioni Attuali

-   **Testo non ricercabile vs Testo OCR**: Se un PDF in ingresso è una fotocopia puramente rasterizzata (senza un text layer sotto), l'estrazione PII Regex/LLM fallisce. Mitigazione attuale: L'architettura ripiega sul "Manual Drawing" tramite layer interattivo.
-   **Hardware Costraints (USB)**: Il caricamento in memoria del PyTorch framework da una connessione USB 2.0/3.0 genera tempi di warmup (avvio del programma) elevati. Mitigazione: Disattivazione totale della scansione PII fino all'ingresso nella visualizzazione di redazione inziale del primo paziente, tenendo l'acquisizione iniziale asincrona e rapida.
