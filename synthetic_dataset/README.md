# 🏥 Medical Redactor - Generatore di Dataset Clinici Sintetici conformi al GDPR

Benvenuto nella directory dedicata al **Generatore di Dataset Clinici Sintetici** di *Medical Redactor*. 

Questa suite è stata progettata per consentire a ricercatori, medici e sviluppatori di generare dataset di cartelle cliniche in lingua italiana ad altissima fedeltà, arricchiti con etichette esatte di **Protected Health Information (PHI) / Personally Identifiable Information (PII)**. Il dataset generato è ideale per addestrare, fine-tunare e validare modelli di Named Entity Recognition (NER) o filtri di privacy basati su Transformer (es. BERT, RoBERTa, LLM localmente ospitati).

> [!NOTE]
> La directory `synthetic_dataset/` è interamente esclusa dal tracciamento Git tramite il file `.gitignore` di radice. Questo previene qualsiasi fuga accidentale di chiavi API locali o di porzioni di dataset generati contenenti dati sensibili simulati.

---

## 🏗️ Architettura del Generatore

Il generatore (`generate_dataset.py`) supporta due modalità operative distinte per bilanciare velocità di esecuzione offline e ricchezza espressiva tipica dei modelli di frontiera.

```
                  ┌───────────────────────────────────────────────┐
                  │          generate_dataset.py (CLI)            │
                  └───────────────────────┬───────────────────────┘
                                          │
                        Scegli la modalità (--mode)
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
      ┌─────────────────────────┐                     ┌─────────────────────────┐
      │      OFFLINE MODE       │                     │       ONLINE MODE       │
      │  (Compilatore Locale)   │                     │   (API LLM Esterne)     │
      └───────────┬─────────────┘                     └───────────┬─────────────┘
                  │                                               │
      Utilizza liste strutturate                      Inietta variabili casuali
      italiane e template per                         nel prompt per evitare
      costruire prosa clinica.                        bias ed omonimie.
                  │                                               │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    synthetic_dataset_output.json      │
                      └───────────────────────────────────────┘
```

### 1. Modalità Offline (`--mode offline`)
Funziona in locale senza richiedere connessioni di rete o chiavi API.
- **Dati Anagrafici e Clinici Italiani**: Utilizza ricche liste seed precompilate di nomi italiani, cognomi comuni, città italiane reali, vie, ospedali rinomati, reparti specialistici e patologie con acronimi e descrizioni reali.
- **Simulatore Anagrafico**: Genera Codici Fiscali formalmente validi (con estrazione consonanti/vocali da nome/cognome, calcolo del mese simbolico e anno di nascita, e sfasamento di +40 per il sesso femminile), numeri di telefono italiani reali, email plausibili e codici di esenzione sanitaria.
- **Edizione dei Casi Limite**: Integra algoritmi probabilistici per simulare omonimie (es. farmaco vs persona), omonimie di ospedali (es. paziente Luigi ricoverato al "San Luigi"), date relative e sovrapposizioni geografiche.

### 2. Modalità Online (`--mode llm`)
Sfrutta modelli di intelligenza artificiale remoti per generare testi complessi, non strutturati e privi di schemi ripetitivi.
- **Modelli Supportati**: Google Gemini (`gemini-2.5-flash` predefinito, raccomandato dal team `gemini-3.5-flash`), OpenAI (`gpt-4o-mini`), e Anthropic (`claude-3-5-sonnet-20241022`).
- **Iniezione Dinamica delle Variabili**: Il generatore seleziona casualmente nomi, cognomi, città e ospedali dalle liste offline e li **inietta direttamente nel prompt** dell'LLM. Questo costringe il modello a generare storie cliniche basate esclusivamente su queste variabili, eliminando del tutto il bias dei modelli che tendono a riutilizzare gli stessi nomi clinici standard (es. "Mario Rossi").
- **Structured JSON Output**: Sfrutta le funzionalità native dei provider (es. `responseMimeType: "application/json"` per Gemini o `response_format` per OpenAI) per ricevere un output JSON garantito senza dover ricorrere a parsing regex instabili.

---

## 📊 Schema e Struttura del Dataset

Il file JSON finale esportato contiene un array di oggetti strutturati secondo il seguente schema standardizzato:

| Campo | Tipo | Descrizione |
| :--- | :--- | :--- |
| `id_caso` | `string` | Codice univoco incrementale del caso (es. `CASO_001`). |
| `tipologia_documento` | `string` | Tipo di verbale (`Lettera di dimissione`, `Diario clinico`, `Verbale di pronto soccorso`). |
| `branca_medica` | `string` | Reparto clinico di riferimento (es. `Cardiologia`, `Neurologia`). |
| `testo_clinico` | `string` | Il testo medico non strutturato in italiano contenente i dati personali sensibili (PHI/PII). |
| `ground_truth_phi` | `object` | Dizionario contenente le liste esatte dei termini sensibili suddivisi per categoria. |

### Categorie di Ground Truth (`ground_truth_phi`)
- **`PAZIENTE`**: Nomi e cognomi completi del paziente, varianti del nome, e menzioni di familiari o contatti d'emergenza presenti nel testo.
- **`MEDICO`**: Nomi di medici di guardia, chirurghi, medici dimettenti o curanti menzionati nel verbale.
- **`DATA`**: Date assolute esatte espresse nel testo (es. `12/05/2026`, `28 Giugno 2026`). *Le date relative non costituiscono PII esatto e non vengono marcate.*
- **`LUOGO`**: Nomi di ospedali, reparti specialistici, indirizzi di residenza e città.
- **`ID_CODICI`**: Codici Fiscali, numeri di telefono, indirizzi email, codici di esenzione, numeri di cartella clinica e codici posto letto.

---

## 🛠️ Gestione Avanzata dei Casi Limite (Edge Cases)

Per garantire la massima robustezza dei modelli addestrati su questo dataset, il generatore inietta attivamente nel testo **quattro scenari critici di ambiguità (omonimie e overlaps)**:

1. **Omonimia di Farmaco**
   - *Scenario*: Presenza di un paziente o parente di nome "Rosa" assieme alla somministrazione clinica dello "sciroppo di rosa" per lenire la tosse.
   - *Obiettivo NER*: Riconoscere "Rosa" come entità `PAZIENTE`, ma ignorare correttamente "sciroppo di rosa" come entità farmacologica standard.
2. **Omonimia di Ospedale**
   - *Scenario*: Un paziente di nome "Luigi" viene ricoverato o trasferito presso l'istituto ospedaliero "San Luigi Gonzaga".
   - *Obiettivo NER*: Riconoscere "Luigi" come entità `PAZIENTE` e "Ospedale San Luigi Gonzaga" come entità `LUOGO`.
3. **Date Relative**
   - *Scenario*: Note cliniche contenenti espressioni temporali non assolute come "ieri", "sabato scorso" o "tra due martedì".
   - *Obiettivo NER*: Le date relative non devono essere identificate come dati sensibili esportabili, evitando falsi positivi nel modello di redazione.
4. **Sovrapposizione Cognome-Città (Overlaps)**
   - *Scenario*: Un paziente il cui cognome è identico a una città (es. "Milano", "Torino", "Roma"), ma che risiede o è ricoverato altrove.
   - *Obiettivo NER*: Distinguere l'entità anagrafica `PAZIENTE` (es. "sig. Milano") dall'entità geografica `LUOGO` (es. "residente nella città di Torino").

---

## 🚀 Istruzioni per l'Uso (CLI Command Line)

### Prerequisiti
Il generatore utilizza esclusivamente moduli della Standard Library di Python (`json`, `urllib`, `argparse`, `random`), garantendo l'esecuzione out-of-the-box in qualsiasi ambiente ospedaliero o amministrativo sprovvisto di privilegi Internet.

### Sintassi del Comando
```bash
python synthetic_dataset/generate_dataset.py [opzioni]
```

### Parametri della CLI
* `--count` *(default: 3)*: Numero di casi clinici da generare nel dataset.
* `--mode` *(default: offline)*: Scegli tra `offline` (generatore locale rapido) e `llm` (generazione avanzata tramite API remota).
* `--provider` *(default: gemini)*: Provider LLM da utilizzare in modalità online (`gemini`, `openai`, `anthropic`).
* `--model` *(opzionale)*: Specifica il modello (es. `gemini-2.5-flash`, `gpt-4o-mini`, `claude-3-5-sonnet-20241022`).
* `--api-key` *(opzionale)*: Chiave API del provider selezionato. Se omessa, il programma cercherà le variabili d'ambiente (`GEMINI_API_KEY`, `OPENAI_API_KEY` o `ANTHROPIC_API_KEY`).
* `--output` *(default: synthetic_dataset/synthetic_dataset_output.json)*: Path di destinazione del dataset in formato JSON.

### Esempi di Esecuzione

#### Esempio 1: Generazione Rapida Locale (Offline)
Genera 50 casi clinici complessi salvandoli all'interno del percorso protetto:
```bash
python synthetic_dataset/generate_dataset.py --count 50 --mode offline
```

#### Esempio 2: Generazione tramite Google Gemini API (Online)
Genera 10 casi ad alta variazione espressiva usando Gemini 2.5 Flash:
```powershell
$env:GEMINI_API_KEY="AIzaSyYourKeyHere..."
python synthetic_dataset/generate_dataset.py --count 10 --mode llm --provider gemini
```

---

## 🤗 Pubblicazione su Hugging Face Datasets

Una volta generato il dataset, condividerlo con la comunità scientifica su **Hugging Face Datasets** è il modo migliore per renderlo facilmente accessibile a chiunque desideri addestrare o testare filtri di anonimizzazione.

Ecco la procedura guidata passo-passo per pubblicare il tuo dataset.

### Passo 1: Installa la libreria di Hugging Face
Assicurati di disporre della libreria `datasets` e del client di Hugging Face sul tuo computer di sviluppo:
```bash
pip install datasets huggingface_hub
```

### Passo 2: Accedi al tuo account Hugging Face
Genera un token con permessi di **scrittura** (Write Token) dal tuo profilo Hugging Face (Settings -> Access Tokens) e autenticati da terminale:
```bash
huggingface-cli login
```
*Inserisci il token quando richiesto.*

### Passo 3: Prepara lo script di caricamento Python
Crea un file temporaneo di caricamento (es. `upload_dataset.py` nella cartella `synthetic_dataset/`) con il seguente codice:

```python
import os
from datasets import Dataset, DatasetDict

# 1. Carica il file JSON generato
json_file_path = "synthetic_dataset/synthetic_dataset_output.json"

if not os.path.exists(json_file_path):
    raise FileNotFoundError(f"File di output non trovato! Generalo prima eseguendo il comando CLI.")

# 2. Carica i dati in un oggetto Dataset di Hugging Face
print("Caricamento del dataset in corso...")
dataset = Dataset.from_json(json_file_path)

# 3. Suddividi in Train / Validation / Test set (Opzionale ma consigliato per NER)
# Es. 80% train, 10% validation, 10% test
train_test_split = dataset.train_test_split(test_size=0.2, seed=42)
test_valid_split = train_test_split["test"].train_test_split(test_size=0.5, seed=42)

dataset_dict = DatasetDict({
    "train": train_test_split["train"],
    "validation": test_valid_split["train"],
    "test": test_valid_split["test"]
})

# 4. Definisci il nome del repository (Sostituisci col tuo username HF)
username_hf = "il-tuo-username"
repo_name = f"{username_hf}/italian-medical-redaction-synthetic"

# 5. Esegui il push su Hugging Face Hub
print(f"Pubblicazione in corso su: https://huggingface.co/datasets/{repo_name}")
dataset_dict.push_to_hub(repo_name, private=False) # private=True se desideri tenerlo privato
print("Caricamento completato con successo!")
```

### Passo 4: Esegui lo script di caricamento
Esegui lo script Python per caricare i dati:
```bash
python synthetic_dataset/upload_dataset.py
```

### Passo 5: Scrivi una Dataset Card professionale
Vai sulla pagina del tuo dataset su Hugging Face (es. `https://huggingface.co/datasets/il-tuo-username/italian-medical-redaction-synthetic`) e scrivi una `README.md` (Dataset Card) che descriva:
1. **Dataset Summary**: Dataset sintetico di note cliniche italiane anonimizzate per l'addestramento NER.
2. **Supported Tasks**: Token Classification, Named Entity Recognition.
3. **Data Schema**: Spiegazione di `ground_truth_phi` e delle categorie `PAZIENTE`, `MEDICO`, `DATA`, `LUOGO`, `ID_CODICI`.
4. **Limitations**: Essendo dati sintetici generati probabilisticamente o tramite LLM, non contengono cartelle cliniche reali di pazienti fisici.

---

Grazie per aver scelto il nostro sistema per la protezione della privacy sanitaria. Condividere dati puliti e anonimizzati aiuta l'intera ricerca medica a progredire in totale sicurezza!
